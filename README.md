# Rubik's Cube × Graph Theory

Scrambles an NxN Rubik's cube (N = 2..5) and solves it with a bidirectional BFS over the
cube's state graph. Each solving step is animated in a 3D cube (Three.js) and in a
concentric-ring graph view (canvas 2D).

## Run

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Open http://localhost:8000.

## Test

```bash
pytest
```

## Notes

- The solver always returns a shortest solution. There is no fixed limit on states explored, but
  cost grows exponentially with scramble depth (a depth-8 4x4 scramble takes a few seconds and a
  few hundred MB). Set `solver.MAX_NODES` to an int if you want it to give up (HTTP 422) instead.
- Layout: `backend/cube.py` (model), `backend/solver.py` (search + graph slice),
  `backend/main.py` (FastAPI), `frontend/index.html` (UI).
