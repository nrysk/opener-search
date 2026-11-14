"""1巡目に確定で TSD を打てるかの全探索 (ぷよぷよテトリス準拠 / SRS)。

最悪ケースとして「T が最初に来てホールドに入り、残り 6 ミノ (I J L S Z O) を
来た順にホールドなしで置き、最後に T で TSD を打つ」状況を考える。

- ミノ順 720 通りは左右反転 (S<->Z, L<->J) で 360 通りに減らす (L が J より先のものを代表とする)
- TSD で消す段を「1,2 段目」「2,3 段目」に固定して別々に探索する → 360 x 2 = 720 通り
- 各ミノの設置は SRS (壁蹴り込み) で実際に到達可能な位置だけを使う
- T スピン判定は 3 コーナールール。前方 2 隅が埋まっていない場合は Mini
  (ただし 5 番目のキックで入った場合は Mini にならない) とし、Mini は TSD と認めない

出力: 00/tsd.csv (可視化は 00/visualize.py)
"""

from __future__ import annotations

import csv
import sys
import time
from itertools import permutations
from multiprocessing import Pool
from pathlib import Path

W = 10  # 盤面の幅
H = 16  # 探索で扱う盤面の高さ (積みは高々 11 段にしかならない)
XOFF, YOFF = 2, 2  # ミノ位置 (バウンディングボックス左下) の負方向の余白
NX, NY = W + XOFF, H + YOFF
MAX_OUTSIDE = 8  # 消去する 2 段の外に置けるブロック数の上限 (24 - 16)

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "tsd.csv"

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


def solve(task: tuple[str, int]) -> dict:
    """ミノ順 order を順に置き、row 段目と row+1 段目 (0 始まり) を T で消す形を探す。"""
    order, row = task
    target = row_mask(row) | row_mask(row + 1)
    targets = (row_mask(row), row_mask(row + 1))
    pieces = [PIECES[c] for c in order]
    dead: set[tuple[int, int]] = set()  # 解がないと分かった (手数, 盤面)
    nodes = 0

    def dfs(board: int, i: int) -> list[int] | None:
        nonlocal nodes
        nodes += 1
        if i == len(pieces):
            hit = find_tsd(board, target)
            return None if hit is None else [hit[0], hit[1], hit[2]]
        for m in pieces[i].placements(board):
            nb = board | m
            # 消す 2 段の外に置けるのは 8 ブロックまで (これで他の段のライン消去も起きない)
            if (nb & ~target).bit_count() > MAX_OUTSIDE:
                continue
            # 消す段が T より前に埋まってはいけない
            if nb & targets[0] == targets[0] or nb & targets[1] == targets[1]:
                continue
            key = (i, nb)
            if key in dead:
                continue
            res = dfs(nb, i + 1)
            if res is not None:
                return [m] + res
            dead.add(key)
        return None

    res = dfs(0, 0)
    out = {
        "order": order,
        "mirror_order": mirror(order),
        "tsd_rows": f"{row + 1}-{row + 2}",
        "found": int(res is not None),
        "t_rotation": "",
        "t_kick": "",
        "field": "",
        "nodes": nodes,
    }
    if res is not None:
        masks, t_mask, t_rot, t_kick = res[:6], res[6], res[7], res[8]
        out["t_rotation"] = "0R2L"[t_rot]
        out["t_kick"] = t_kick + 1
        out["field"] = render_field(list(zip(order, masks)) + [("T", t_mask)])
    return out


def render_field(placed: list[tuple[str, int]]) -> str:
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


def mirror(order: str) -> str:
    return order.translate(str.maketrans("SZLJ", "ZSJL"))


def canonical_orders() -> list[str]:
    """左右反転で同一視した 360 通りのミノ順 (L が J より先のもの)。"""
    orders = ["".join(p) for p in permutations("IJLSZO")]
    return [o for o in orders if o.index("L") < o.index("J")]


def main() -> None:
    tasks = [(o, row) for o in canonical_orders() for row in (0, 1)]
    start = time.time()
    results = []
    with Pool() as pool:
        for i, res in enumerate(pool.imap(solve, tasks), 1):
            results.append(res)
            print(f"\r{i}/{len(tasks)} ({time.time() - start:.0f}s)", end="", file=sys.stderr)
    print(file=sys.stderr)

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    orders = canonical_orders()
    found = {(r["order"], r["tsd_rows"]) for r in results if r["found"]}
    n12 = sum((o, "1-2") in found for o in orders)
    n23 = sum((o, "2-3") in found for o in orders)
    ng = [o for o in orders if (o, "1-2") not in found and (o, "2-3") not in found]
    print(f"1-2 段目で TSD 可能: {n12}/{len(orders)}")
    print(f"2-3 段目で TSD 可能: {n23}/{len(orders)}")
    print(f"どちらでも不可能: {len(ng)} 通り {' '.join(ng)}")
    print(f"wrote {CSV_PATH.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
