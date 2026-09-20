"""NxN Rubik's cube model: stickers, and moves as permutations of sticker indices.

Cubie centres sit at -(n-1), -(n-3), ..., (n-1) on each axis (step 2), so coordinates
stay integers for odd and even n. A state is a tuple of face letters, one per sticker.
"""
from dataclasses import dataclass
from functools import lru_cache

FACES = "UDRLFB"
NORMALS = {
    "U": (0, 1, 0), "D": (0, -1, 0),
    "R": (1, 0, 0), "L": (-1, 0, 0),
    "F": (0, 0, 1), "B": (0, 0, -1),
}
AXES = "xyz"
# Sign of the right-hand rotation about the face's axis that is a clockwise turn
# when looking at that face from outside.
CW_SIGN = {"R": -1, "U": -1, "F": -1, "L": 1, "D": 1, "B": 1}


def _rot90(v, axis):
    """Rotate vector v by +90 degrees (right-hand) about the given axis index."""
    x, y, z = v
    if axis == 0:
        return (x, -z, y)
    if axis == 1:
        return (z, y, -x)
    return (-y, x, z)


def _rotate(v, axis, q):
    for _ in range(q % 4):
        v = _rot90(v, axis)
    return v


@dataclass(frozen=True)
class Move:
    name: str
    face: str
    depth: int
    turns: int       # 1 = clockwise, 2 = half, 3 = counter-clockwise
    axis: str        # "x" | "y" | "z"
    layer: int       # coordinate of the slice on `axis`
    q: int           # signed right-hand quarter turns: -1, 1 or 2
    src: tuple       # new[j] = old[src[j]]
    inv: int         # index of the inverse move in the spec's move list
    slice_id: tuple  # (face, depth): used to avoid turning the same slice twice in a row

    def as_dict(self):
        return {"name": self.name, "axis": self.axis, "layer": self.layer, "q": self.q}


class CubeSpec:
    def __init__(self, n):
        self.n = n
        self.stickers = self._make_stickers(n)
        index = {s: i for i, s in enumerate(self.stickers)}
        self.solved = tuple(
            next(f for f in FACES if NORMALS[f] == nm) for _, nm in self.stickers
        )
        self.moves = self._make_moves(n, index)
        self.move_by_name = {m.name: m for m in self.moves}
        # U-face stickers in top-down reading order (back row first, left to right).
        u = [i for i, (_, nm) in enumerate(self.stickers) if nm == NORMALS["U"]]
        self.u_index = sorted(u, key=lambda i: (self.stickers[i][0][2], self.stickers[i][0][0]))

    @staticmethod
    def _make_stickers(n):
        coords = range(-(n - 1), n, 2)
        out = []
        for f in FACES:
            nm = NORMALS[f]
            fixed = next(i for i in range(3) if nm[i] != 0)
            free = [i for i in range(3) if i != fixed]
            for a in coords:
                for b in coords:
                    p = [0, 0, 0]
                    p[fixed] = nm[fixed] * (n - 1)
                    p[free[0]], p[free[1]] = a, b
                    out.append((tuple(p), nm))
        return out

    def _make_moves(self, n, index):
        moves = []
        for f in FACES:
            nm = NORMALS[f]
            axis = next(i for i in range(3) if nm[i] != 0)
            sign = nm[axis]
            for depth in range(1, n // 2 + 1):
                layer = sign * (n - 1 - 2 * (depth - 1))
                for turns in (1, 2, 3):
                    q = {1: CW_SIGN[f], 2: 2, 3: -CW_SIGN[f]}[turns]
                    src = list(range(len(self.stickers)))
                    for j, (p, s_nm) in enumerate(self.stickers):
                        if p[axis] == layer:
                            k = index[(_rotate(p, axis, q), _rotate(s_nm, axis, q))]
                            src[k] = j
                    prefix = "" if depth == 1 else str(depth)
                    suffix = {1: "", 2: "2", 3: "'"}[turns]
                    moves.append(Move(prefix + f + suffix, f, depth, turns, AXES[axis],
                                      layer, q, tuple(src), -1, (f, depth)))
        # Resolve inverse indices (turns 1 <-> 3, turns 2 is self-inverse).
        by_key = {(m.face, m.depth, m.turns): i for i, m in enumerate(moves)}
        return [
            Move(m.name, m.face, m.depth, m.turns, m.axis, m.layer, m.q, m.src,
                 by_key[(m.face, m.depth, {1: 3, 2: 2, 3: 1}[m.turns])], m.slice_id)
            for m in moves
        ]

    def apply(self, state, move):
        return tuple([state[i] for i in move.src])

    def state_to_json(self, state):
        return {
            "n": self.n,
            "stickers": [
                {"p": list(p), "nm": list(nm), "c": c}
                for (p, nm), c in zip(self.stickers, state)
            ],
        }

    def state_from_json(self, stickers):
        if len(stickers) != len(self.stickers):
            raise ValueError("wrong number of stickers for this cube size")
        state = tuple(s["c"] for s in stickers)
        if any(c not in FACES for c in state):
            raise ValueError("unknown sticker colour")
        if any(state.count(f) != self.n ** 2 for f in FACES):
            raise ValueError("each colour must appear n*n times")
        return state


@lru_cache(maxsize=None)
def get_spec(n):
    if n < 2:
        raise ValueError("cube size must be at least 2")
    return CubeSpec(n)
