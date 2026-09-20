"""FastAPI app: serves the frontend and the cube / scramble / solve API."""
import random
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import solver
from .cube import get_spec

FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "index.html"

# Deepest random jumble per cube size when no k is given (keeps the shortest-solution search fast).
DEFAULT_MAX_DEPTH = {2: 10, 3: 10, 4: 7, 5: 7}

app = FastAPI(title="Rubik's Cube Graph Solver")


class ScrambleRequest(BaseModel):
    n: int
    stickers: list[dict]
    k: int | None = None  # omitted: pick a random depth the solver can handle


class SolveRequest(BaseModel):
    n: int
    stickers: list[dict]


def _spec_and_state(n, stickers):
    if not 2 <= n <= 7:
        raise HTTPException(422, "n must be between 2 and 7")
    spec = get_spec(n)
    try:
        return spec, spec.state_from_json(stickers)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/")
def index():
    return FileResponse(FRONTEND)


@app.get("/api/cube")
def cube(n: int = Query(3, ge=2, le=7)):
    spec = get_spec(n)
    return {
        "state": spec.state_to_json(spec.solved),
        "moves": [m.as_dict() for m in spec.moves],
    }


@app.post("/api/scramble")
def scramble(req: ScrambleRequest):
    spec, state = _spec_and_state(req.n, req.stickers)
    k = req.k if req.k is not None else random.randint(3, DEFAULT_MAX_DEPTH.get(req.n, 6))
    steps, last_slice = [], None
    for _ in range(max(0, k)):
        move = random.choice([m for m in spec.moves if m.slice_id != last_slice])
        state = spec.apply(state, move)
        last_slice = move.slice_id
        steps.append({"move": move.as_dict(), "state": spec.state_to_json(state)})
    return {"steps": steps}


@app.post("/api/solve")
def solve(req: SolveRequest):
    spec, state = _spec_and_state(req.n, req.stickers)
    try:
        path, states, stats, graph = solver.solve(req.n, state, max_nodes=solver.MAX_NODES)
    except solver.SearchLimit as e:
        raise HTTPException(422, str(e))
    steps = [
        {"move": spec.moves[mi].as_dict(), "state": spec.state_to_json(states[i + 1])}
        for i, mi in enumerate(path)
    ]
    return {"steps": steps, "stats": stats, "graph": graph}
