"""アルバトロス TSD の 2巡目で、5 ミノを置いた時点で TSD を打てる形を全列挙する (SRS、途中消しあり)。

80/search.py との違い:
- 2巡目の 6 ミノ (I J L S Z O) のうち、来た順に先頭の 5 ミノだけを置き、そこで T を入れて TSD を打つ
  (6 番目のミノは置かない)。5 ミノの並びと 6 ミノのミノ順は 1 対 1 に対応するので、
  結果は 720 通りのミノ順ごとに記録する
- T より前にラインが消えてもよい (途中消し)。消えたら上の段が落ちる
- 盤面の高さは、ラインが消えたあとの状態で常に MAX_HEIGHT 段以下に制限する
- T は T-Spin Double でちょうど 2 段を消す (3 段消えるものは含めない)

「シルエット」は T を置く前に埋まっているマスの集合。同じシルエットでもミノの割り当て
(どのマスがどのミノの一部か。途中消しでミノが欠けることもある) が複数ありうるので、
割り当てごとに組めるミノ順を記録する。

出力: 80/patterns5.csv (1 行 = シルエット x ミノ割り。可視化は 80/visualize5.py)
  - field: T を置いたあとの盤面。1巡目の残りは小文字、2巡目のミノと T は大文字
  - mid_clears: T より前に消えた段数
  - orders: 組めるミノ順を空白区切りで並べたもの。ソフトドロップが必要なら「ミノ順:回数」
    (その割り当てになる置き方のうち最少の回数。最後の T は含めない)
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from search import STARTS  # noqa: E402

from lib.followup import NAMES, ORDER_BIT, ORDERS, WEIGHT, parse_board  # noqa: E402
from lib.srs import PIECES, H, W, find_tsd, row_mask  # noqa: E402

CSV_PATH = HERE / "patterns5.csv"
MAX_HEIGHT = 5  # 盤面の高さの上限 (ラインが消えたあとの状態で数える)
PLACED = 5  # T の前に置くミノの数

START_FIELD = STARTS["albatross"]
LIMIT = (1 << (MAX_HEIGHT * W)) - 1
COL0 = sum(1 << (y * W) for y in range(H))
TARGETS = [row_mask(y) | row_mask(y + 1) for y in range(MAX_HEIGHT - 1)]


def full_rows(board: int) -> int:
    """埋まっている段 y について、ビット y * W が立った値。"""
    t = board & board >> 1
    t2 = t & t >> 2
    return t2 & t2 >> 4 & t >> 8 & COL0


def clear_rows(board: int, full: int) -> int:
    for y in reversed(range(H)):
        if full >> (y * W) & 1:
            board = board & ((1 << (y * W)) - 1) | board >> ((y + 1) * W) << (y * W)
    return board


_tsd_cache: dict[int, list[tuple[int, int, int]]] = {}


def tsd_hits(board: int) -> list[tuple[int, int, int]]:
    """board に T を入れてちょうど 2 段消せる (下の段, T のマスク, T の向き) の一覧。"""
    hits = _tsd_cache.get(board)
    if hits is None:
        hits = []
        for row, target in enumerate(TARGETS):
            if (board & target).bit_count() != 2 * W - 4:
                continue
            hit = find_tsd(board, target)
            if hit is not None and full_rows(board | hit[0]).bit_count() == 2:
                hits.append((row, hit[0], hit[1]))
        _tsd_cache[board] = hits
    return hits


def explore(start: int) -> tuple[dict[int, list[tuple[int, int, bool, int]]], int]:
    """TSD に至る置き方だけを残したグラフを作る。

    状態は 盤面 << 6 | 使ったミノ。戻り値は 状態 -> [(ミノ番号, 置いたマスク, ハードドロップ可か, 次の盤面)]
    (TSD に至る手だけ) と、調べた状態数。
    """
    alive: dict[int, bool] = {}
    edges: dict[int, list[tuple[int, int, bool, int]]] = {}

    def dfs(used: int, board: int, depth: int) -> bool:
        key = board << 6 | used
        known = alive.get(key)
        if known is not None:
            return known
        out = []
        for ci, c in enumerate(NAMES):
            if used >> ci & 1:
                continue
            for m, hard in PIECES[c].placements_with_drop(board).items():
                nb = board | m
                full = full_rows(nb)
                if full:
                    nb = clear_rows(nb, full)
                if nb > LIMIT:
                    continue
                if depth == PLACED - 1:
                    # 2 段の合計が 16 マスの組がなければ TSD はない (ほとんどの盤面をここで落とす)
                    if any((nb & t).bit_count() == 2 * W - 4 for t in TARGETS) and tsd_hits(nb):
                        out.append((ci, m, hard, nb))
                elif dfs(used | 1 << ci, nb, depth + 1):
                    out.append((ci, m, hard, nb))
        alive[key] = bool(out)
        if out:
            edges[key] = out
        return bool(out)

    dfs(0, start, 0)
    return edges, len(alive)


Colored = tuple[str, ...]  # 下の段から。ミノの文字 (1巡目の残りは小文字) か '_'


def place_colored(col: Colored, c: str, m: int) -> Colored:
    rows = [list(r) for r in col]
    for i in range(H * W):
        if m >> i & 1:
            rows[i // W][i % W] = c
    kept = ["".join(r) for r in rows if "_" in r]
    return tuple(kept + ["_" * W] * (H - len(kept)))


def main() -> None:
    began = time.time()
    start = parse_board(START_FIELD)
    edges, visited = explore(start)
    print(f"調べた状態 {visited}, TSD に至る状態 {len(edges)} ({time.time() - began:.0f}s)", file=sys.stderr)

    # TSD に至る置き方をたどり、(状態, 色つき盤面) ごとに {ソフトドロップ回数: ミノ順集合} を求める
    lines = list(reversed(START_FIELD.lower().split("/")))
    col0: Colored = tuple(lines + ["_" * W] * (H - len(lines)))
    front: dict[tuple[int, Colored], dict[int, int]] = {(start << 6, col0): {0: 1}}
    for depth in range(PLACED):
        w = WEIGHT[depth]
        nxt: dict[tuple[int, Colored], dict[int, int]] = {}
        for (key, col), by_soft in front.items():
            used = key & 63
            for ci, m, hard, nb in edges.get(key, ()):
                rank = sum(1 for j in range(ci) if not used >> j & 1)
                dst = nxt.setdefault((nb << 6 | used | 1 << ci, place_colored(col, NAMES[ci], m)), {})
                for soft, orders in by_soft.items():
                    s = soft + (0 if hard else 1)
                    dst[s] = dst.get(s, 0) | orders << (rank * w)
        front = nxt

    # (TSD の段, T を置いた色つき盤面) ごとにまとめる。使ったミノが違っても同じ盤面ならまとめる
    patterns: dict[tuple[int, str], dict] = {}
    for (key, col), by_soft in front.items():
        board = key >> 6
        for row, t_mask, t_rot in tsd_hits(board):
            done = place_colored(col, "T", 0)  # 型をそろえるだけ (T は段を消す前の形で描く)
            rows = [list(r) for r in done]
            for i in range(H * W):
                if t_mask >> i & 1:
                    rows[i // W][i % W] = "T"
            top_down = ["".join(r) for r in reversed(rows)]
            while top_down[0] == "_" * W:
                top_down.pop(0)
            p = patterns.setdefault(
                (row, "/".join(top_down)),
                {"board": board, "t_rot": t_rot, "soft": {}},
            )
            for soft, orders in by_soft.items():
                p["soft"][soft] = p["soft"].get(soft, 0) | orders

    # シルエット (T を置く前のマスの集合 x TSD の段) ごとに番号を振る
    sil_ids: dict[tuple[int, int], str] = {}
    for row, field in sorted(patterns, key=lambda k: (k[0], patterns[k]["board"], k[1])):
        sil = (row, patterns[row, field]["board"])
        sil_ids.setdefault(sil, f"a5-{row + 1}-{sum(1 for s in sil_ids if s[0] == row) + 1:03d}")

    results = []
    for (row, field), p in sorted(patterns.items(), key=lambda kv: sil_ids[kv[0][0], kv[1]["board"]]):
        best = {}
        for o in ORDERS:
            softs = [s for s, orders in p["soft"].items() if orders >> ORDER_BIT[o] & 1]
            if softs:
                best[o] = min(softs)
        results.append(
            {
                "silhouette": sil_ids[row, p["board"]],
                "tsd_rows": f"{row + 1}-{row + 2}",
                "mid_clears": (start.bit_count() + 4 * PLACED - p["board"].bit_count()) // W,
                "t_rotation": "0R2L"[p["t_rot"]],
                "orders_count": len(best),
                "field": field,
                "orders": " ".join(o + (f":{s}" if s else "") for o, s in best.items()),
            }
        )

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    def summary(label: str, rows: list[dict]) -> None:
        covered = {o.split(":")[0] for r in rows for o in r["orders"].split()}
        hard = {o for r in rows for o in r["orders"].split() if ":" not in o}
        print(
            f"{label}: シルエット {len({r['silhouette'] for r in rows})} 種類, ミノ割り {len(rows)} 種類, "
            f"TSD を打てるミノ順 {len(covered)}/720 (ソフトドロップなし {len(hard)}/720)"
        )

    summary("全体", results)
    for n in sorted({r["mid_clears"] for r in results}):
        summary(f"途中消し {n} 段", [r for r in results if r["mid_clears"] == n])
    for rows_label in sorted({r["tsd_rows"] for r in results}):
        summary(f"TSD {rows_label} 段目", [r for r in results if r["tsd_rows"] == rows_label])
    print(f"wrote {CSV_PATH.relative_to(HERE.parent)} ({time.time() - began:.0f}s)")


if __name__ == "__main__":
    main()
