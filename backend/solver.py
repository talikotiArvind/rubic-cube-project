"""Bidirectional BFS over the cube's move graph, plus a small graph slice for drawing."""
import time
from functools import lru_cache
from operator import itemgetter

from .cube import get_spec

# No fixed cap: the search runs until it finds the shortest solution.
# Set to an int to make solve() give up after that many explored states.
MAX_NODES = None
NEIGHBOURS_PER_PATH_NODE = 6


class SearchLimit(Exception):
    """Raised when the search cannot finish (explicit max_nodes hit, or out of memory)."""


@lru_cache(maxsize=None)
def _successors(n):
    """For each previous move (last index; len(moves) = none), the moves worth trying next.

    Turns of slices on the same axis commute, so they are only tried in one order
    (increasing layer); the same slice is never turned twice in a row.
    """
    spec = get_spec(n)
    getters = [itemgetter(*m.src) for m in spec.moves]
    table = []
    for last in list(spec.moves) + [None]:
        table.append([
            (mi, getters[mi]) for mi, m in enumerate(spec.moves)
            if last is None or m.axis != last.axis or m.layer > last.layer
        ])
    return table


def _expand_layer(succ, frontier, visited, other, max_nodes, other_size):
    """Expand `frontier` by one move. Returns (next_frontier, meetings)."""
    nxt, meetings = [], []
    none = len(succ) - 1
    for state in frontier:
        parent_info = visited[state]
        last = parent_info[1] if parent_info[1] is not None else none
        depth = parent_info[2] + 1
        for mi, get in succ[last]:
            new = bytes(get(state))
            if new in visited:
                continue
            visited[new] = (state, mi, depth)
            nxt.append(new)
            if new in other:
                meetings.append(new)
        if max_nodes is not None and len(visited) + other_size > max_nodes:
            raise SearchLimit("Search limit reached. Try a shorter scramble.")
    return nxt, meetings


def solve(n, start, max_nodes=None):
    """Return the shortest move list (as spec.moves indices) plus stats and a graph slice."""
    max_nodes = MAX_NODES if max_nodes is None else max_nodes
    spec = get_spec(n)
    succ = _successors(n)
    start_tuple = start
    start, goal = "".join(start).encode(), "".join(spec.solved).encode()
    t0 = time.perf_counter()

    fwd = {start: (None, None, 0)}   # state -> (parent, move index used to get here, depth)
    bwd = {goal: (None, None, 0)}
    meet = start if start == goal else None
    ffront, bfront = [start], [goal]

    try:
        while meet is None:
            if len(ffront) <= len(bfront):
                ffront, found = _expand_layer(succ, ffront, fwd, bwd, max_nodes, len(bwd))
            else:
                bfront, found = _expand_layer(succ, bfront, bwd, fwd, max_nodes, len(fwd))
            if found:
                meet = min(found, key=lambda s: fwd[s][2] + bwd[s][2])
            elif not ffront and not bfront:
                raise SearchLimit("No solution found.")
    except MemoryError:
        raise SearchLimit("Ran out of memory while searching.")

    # Forward half: walk parents back from the meeting state to the start.
    head = []
    s = meet
    while fwd[s][0] is not None:
        head.append(fwd[s][1])
        s = fwd[s][0]
    head.reverse()
    # Backward half: bwd[s] = (parent, m) means s = m(parent), so parent = inv(m)(s).
    tail = []
    s = meet
    while bwd[s][0] is not None:
        tail.append(spec.moves[bwd[s][1]].inv)
        s = bwd[s][0]
    path = head + tail

    states = [start_tuple]
    for mi in path:
        states.append(spec.apply(states[-1], spec.moves[mi]))

    stats = {
        "explored": len(fwd) + len(bwd),
        "length": len(path),
        "seconds": round(time.perf_counter() - t0, 3),
    }
    graph = _graph_for_view(spec, states, len(head), path, fwd, bwd)
    return path, states, stats, graph


def _graph_for_view(spec, states, meet_step, path, fwd, bwd):
    """Path nodes plus a few explored neighbours each, for drawing."""
    u_colours = lambda st: [st[i] for i in spec.u_index]
    total = len(path)
    nodes = [
        {"id": i, "u": u_colours(st), "path": True, "step": i,
         "side": "fwd" if i <= meet_step else "bwd"}
        for i, st in enumerate(states)
    ]
    edges = [
        {"a": i, "b": i + 1, "move": spec.moves[mi].name, "path": True}
        for i, mi in enumerate(path)
    ]

    path_index = {"".join(st).encode(): i for i, st in enumerate(states)}
    count = [0] * len(states)
    seen = set(path_index)
    for side, visited in (("fwd", fwd), ("bwd", bwd)):
        for st, (parent, mi, _) in visited.items():
            i = path_index.get(parent)
            if i is None or st in seen or count[i] >= NEIGHBOURS_PER_PATH_NODE:
                continue
            seen.add(st)
            count[i] += 1
            nid = len(nodes)
            nodes.append({"id": nid, "u": u_colours(st.decode()), "path": False,
                          "step": None, "side": side, "parent": i})
            edges.append({"a": i, "b": nid, "move": spec.moves[mi].name, "path": False})
    return {"total": total, "nodes": nodes, "edges": edges}
