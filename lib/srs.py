"""SRS (ぷよぷよテトリス準拠) のミノ操作と T スピン判定。各調査 (00, 01, ...) で共有する。

盤面は幅 W のビットボード (y * W + x 番目のビットがマス (x, y)、y は上向き)。
"""

from __future__ import annotations

W = 10  # 盤面の幅
H = 16  # 探索で扱う盤面の高さ (積みは高々 11 段にしかならない)
XOFF, YOFF = 2, 2  # ミノ位置 (バウンディングボックス左下) の負方向の余白
NX, NY = W + XOFF, H + YOFF

# 回転状態 0 (出現時の向き) の形。座標はボックス内 (x, y)、y は上向き。
SHAPES = {
    "I": (4, [(0, 2), (1, 2), (2, 2), (3, 2)]),
    "O": (2, [(0, 0), (1, 0), (0, 1), (1, 1)]),
    "T": (3, [(1, 2), (0, 1), (1, 1), (2, 1)]),
    "S": (3, [(1, 2), (2, 2), (0, 1), (1, 1)]),
    "Z": (3, [(0, 2), (1, 2), (1, 1), (2, 1)]),
    "J": (3, [(0, 2), (0, 1), (1, 1), (2, 1)]),
    "L": (3, [(2, 2), (0, 1), (1, 1), (2, 1)]),
}

# SRS キックテーブル (from, to) -> [(dx, dy)]、y は上向き。回転状態 0=出現, 1=右, 2=逆, 3=左
KICKS_JLSTZ = {
    (0, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (1, 0): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
    (1, 2): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
    (2, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (2, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
    (3, 2): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (3, 0): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (0, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
}
KICKS_I = {
    (0, 1): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
    (1, 0): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
    (1, 2): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
    (2, 1): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
    (2, 3): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
    (3, 2): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
    (3, 0): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
    (0, 3): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
}

# T の中心から見た 4 隅と、各回転状態での「前方」(凸側) の 2 隅
T_CORNERS = [(-1, -1), (1, -1), (-1, 1), (1, 1)]
T_FRONT = {
    0: [(-1, 1), (1, 1)],
    1: [(1, 1), (1, -1)],
    2: [(-1, -1), (1, -1)],
    3: [(-1, -1), (-1, 1)],
}


def row_mask(y: int) -> int:
    return ((1 << W) - 1) << (y * W)


class Piece:
    """ミノの全状態 (回転, x, y) について、マスクと遷移先を前計算したもの。"""

    def __init__(self, name: str) -> None:
        self.name = name
        size, cells = SHAPES[name]
        self.nrot = 1 if name == "O" else 4
        rots = [cells]
        for _ in range(self.nrot - 1):
            # 時計回り: (x, y) -> (y, size - 1 - x)
            rots.append([(y, size - 1 - x) for x, y in rots[-1]])
        self.cells = rots

        n = self.nrot * NX * NY
        self.mask: list[int] = [-1] * n  # -1 は盤外 (何とでも衝突する)
        self.moves: list[tuple[int, ...]] = [()] * n  # 左右下への移動先
        self.down: list[int] = [-1] * n
        # 回転ごとの (移動先, キック番号) の候補列。盤外になる候補は除いてある
        self.rots: list[tuple[tuple[tuple[int, int], ...], ...]] = [()] * n
        self.by_y: dict[int, list[int]] = {}

        for r in range(self.nrot):
            for x in range(-XOFF, W):
                for y in range(-YOFF, H):
                    m = 0
                    for cx, cy in rots[r]:
                        px, py = x + cx, y + cy
                        if not (0 <= px < W and 0 <= py < H):
                            m = -1
                            break
                        m |= 1 << (py * W + px)
                    self.mask[self.index(r, x, y)] = m

        kicks = KICKS_I if name == "I" else KICKS_JLSTZ
        for r in range(self.nrot):
            for x in range(-XOFF, W):
                for y in range(-YOFF, H):
                    s = self.index(r, x, y)
                    if self.mask[s] < 0:
                        continue
                    self.by_y.setdefault(y, []).append(s)
                    moves = []
                    for dx, dy in ((-1, 0), (1, 0), (0, -1)):
                        t = self.index_or_none(r, x + dx, y + dy)
                        if t is not None:
                            moves.append(t)
                            if dy:
                                self.down[s] = t
                    self.moves[s] = tuple(moves)
                    if self.nrot == 1:
                        continue
                    both = []
                    for dr in (1, 3):
                        r2 = (r + dr) % 4
                        cands = []
                        for k, (dx, dy) in enumerate(kicks[(r, r2)]):
                            t = self.index_or_none(r2, x + dx, y + dy)
                            if t is not None:
                                cands.append((t, k))
                        both.append(tuple(cands))
                    self.rots[s] = tuple(both)

    def index(self, r: int, x: int, y: int) -> int:
        return (r * NX + x + XOFF) * NY + y + YOFF

    def index_or_none(self, r: int, x: int, y: int) -> int | None:
        if not (-XOFF <= x < W and -YOFF <= y < H):
            return None
        s = self.index(r, x, y)
        return s if self.mask[s] >= 0 else None

    def decode(self, s: int) -> tuple[int, int, int]:
        r, rest = divmod(s, NX * NY)
        x, y = divmod(rest, NY)
        return r, x - XOFF, y - YOFF

    def reachable(self, board: int) -> set[int]:
        """盤面 board 上で、操作 (左右移動・落下・左右回転) により到達できる全状態。"""
        # 積みより上はすべて空なので、積みの高さから探索を始めれば十分
        height = (board.bit_length() + W - 1) // W
        mask, moves, rots = self.mask, self.moves, self.rots
        stack = list(self.by_y[height])
        seen = set(stack)
        while stack:
            s = stack.pop()
            for t in moves[s]:
                if t not in seen and not mask[t] & board:
                    seen.add(t)
                    stack.append(t)
            for cands in rots[s]:
                for t, _ in cands:
                    if not mask[t] & board:  # 最初に入るキックだけが採用される
                        if t not in seen:
                            seen.add(t)
                            stack.append(t)
                        break
        return seen

    def placements(self, board: int) -> list[int]:
        """設置可能なマスクの一覧 (低い位置を優先)。"""
        mask, down = self.mask, self.down
        out = set()
        for s in self.reachable(board):
            d = down[s]
            if d < 0 or mask[d] & board:
                out.add(mask[s])
        return sorted(out)

    def placements_with_drop(self, board: int) -> dict[int, bool]:
        """設置可能なマスク -> ハードドロップだけで置けるか。

        「空中で向きと列を決めて真下に落とす」で届く位置をハードドロップ可とする。
        """
        mask, down = self.mask, self.down
        height = (board.bit_length() + W - 1) // W
        hard = set()
        for s in self.by_y[height]:
            while True:
                d = down[s]
                if d < 0 or mask[d] & board:
                    break
                s = d
            hard.add(mask[s])
        out = {}
        for s in self.reachable(board):
            d = down[s]
            if d < 0 or mask[d] & board:
                out[mask[s]] = mask[s] in hard
        return out


PIECES = {name: Piece(name) for name in SHAPES}


def occupied(board: int, x: int, y: int) -> bool:
    if not (0 <= x < W and y >= 0):
        return True
    return y < H and bool(board >> (y * W + x) & 1)


def find_tsd(board: int, target: int) -> tuple[int, int, int] | None:
    """board に T を入れて target の 2 段を消す T-Spin Double を探す。

    戻り値は (T のマスク, 回転状態, キック番号)。
    """
    if (board & target).bit_count() < 2 * W - 4:
        return None
    t = PIECES["T"]
    mask, down = t.mask, t.down
    for s in t.reachable(board):
        for cands in t.rots[s]:
            for dst, kick in cands:
                if mask[dst] & board:
                    continue
                # dst は s から回転で入った位置。そのまま接地して 2 段消えるか
                d = down[dst]
                if (d < 0 or mask[d] & board) and (board | mask[dst]) & target == target:
                    r, x, y = t.decode(dst)
                    cx, cy = x + 1, y + 1
                    corners = sum(occupied(board, cx + dx, cy + dy) for dx, dy in T_CORNERS)
                    front = all(occupied(board, cx + dx, cy + dy) for dx, dy in T_FRONT[r])
                    if corners >= 3 and (front or kick == 4):
                        return mask[dst], r, kick
                break
    return None


def field_string(placed: list[tuple[str, int]]) -> str:
    """設置結果を、上の段から順に '/' 区切りで並べた文字列にする ('_' は空白)。"""
    full = 0
    for _, m in placed:
        full |= m
    height = (full.bit_length() + W - 1) // W
    rows = []
    for y in reversed(range(height)):
        line = ""
        for x in range(W):
            bit = 1 << (y * W + x)
            line += next((c for c, m in placed if m & bit), "_")
        rows.append(line)
    return "/".join(rows)
