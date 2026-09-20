import random
import time

import pytest

from backend.cube import get_spec
from backend.solver import solve


def _identity(spec, state):
    return state == spec.solved


@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_move_powers_and_inverses(n):
    spec = get_spec(n)
    ident = tuple(range(len(spec.stickers)))
    for m in spec.moves:
        s = spec.solved
        cycle = 2 if m.turns == 2 else 4
        for _ in range(cycle):
            s = spec.apply(s, m)
        assert s == spec.solved, m.name
        # Use a distinguishable state so permutation errors can't hide in the solved one.
        marked = tuple(range(len(spec.stickers)))
        back = spec.apply(spec.apply(marked, m), spec.moves[m.inv])
        assert back == ident, m.name


def test_move_counts():
    assert len(get_spec(3).moves) == 18
    assert len(get_spec(4).moves) == 36
    assert len(get_spec(5).moves) == 36


@pytest.mark.parametrize("n,k", [(2, 6), (3, 6), (4, 4)])
def test_scramble_then_solution_is_solved(n, k):
    spec = get_spec(n)
    rng = random.Random(n)
    state = spec.solved
    for _ in range(k):
        state = spec.apply(state, rng.choice(spec.moves))
    path, states, stats, graph = solve(n, state)
    for mi in path:
        state = spec.apply(state, spec.moves[mi])
    assert state == spec.solved
    assert stats["length"] == len(path) <= k
    assert graph["nodes"][0]["path"] and len(graph["nodes"]) >= len(path) + 1


def test_3x3_depth7_under_two_seconds():
    spec = get_spec(3)
    rng = random.Random(1)
    state = spec.solved
    for _ in range(7):
        state = spec.apply(state, rng.choice(spec.moves))
    t = time.perf_counter()
    solve(3, state)
    assert time.perf_counter() - t < 2
