from fastapi.testclient import TestClient

from backend import solver
from backend.main import app

client = TestClient(app)


def test_round_trip():
    n = 3
    cube = client.get("/api/cube", params={"n": n}).json()
    assert len(cube["moves"]) == 18
    state = cube["state"]

    scr = client.post("/api/scramble", json={"n": n, "stickers": state["stickers"], "k": 5}).json()
    assert len(scr["steps"]) == 5
    scrambled = scr["steps"][-1]["state"]

    res = client.post("/api/solve", json={"n": n, "stickers": scrambled["stickers"]})
    assert res.status_code == 200
    body = res.json()
    assert 0 < len(body["steps"]) <= 5
    final = body["steps"][-1]["state"]["stickers"]
    assert [s["c"] for s in final] == [s["c"] for s in state["stickers"]]
    assert body["stats"]["length"] == len(body["steps"])
    assert body["graph"]["nodes"]


def test_solve_gives_422_when_search_limit_hit(monkeypatch):
    state = client.get("/api/cube", params={"n": 3}).json()["state"]
    scr = client.post("/api/scramble", json={"n": 3, "stickers": state["stickers"], "k": 8}).json()
    monkeypatch.setattr(solver, "MAX_NODES", 10)
    res = client.post("/api/solve", json={"n": 3, "stickers": scr["steps"][-1]["state"]["stickers"]})
    assert res.status_code == 422
    assert "shorter" in res.json()["detail"]


def test_index_served():
    assert client.get("/").status_code == 200
