"""ある形 (前の巡の TSD 後に残る形) から、次の 1 巡で TSD を打てる形を全列挙する (SRS)。

開始形状に 6 ミノ (I J L S Z O) を来た順にホールドなしで置き、最後に来た T で TSD を打つ。
720 通りのミノ順すべてについて、TSD を打てる最終形を求める。05, 06 で共有する。

- T を置く前の高さは max_height 段以下に制限する (制限なしでは組み合わせ爆発する)
- T を置く前にラインが消える置き方は扱わない
- TSD で消す段は 1-2 段目から (max_height-1)-(max_height) 段目まですべて調べる
- 「シルエット」は T を置く前に埋まっているマスの集合。同じシルエットでもミノの
  割り当て (ミノ割り) が複数ありうるので、ミノ割りごとに組めるミノ順を記録する
- ソフトドロップが必要な置き方も含める (回数の定義は 01 と同じ。最後の T は含めない)

出力 CSV (1 行 = 開始形状 x シルエット x ミノ割り)
  - field: 開始形状のマスは小文字、この巡のミノと T は大文字
  - orders: 組めるミノ順を空白区切りで並べたもの。ソフトドロップが必要なら
    「ミノ順:対象ミノ」と書く
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from itertools import combinations, permutations
from multiprocessing import Pool
from pathlib import Path

from lib.srs import PIECES, H, W, find_tsd, row_mask

NAMES = "IJLSZO"
ORDERS = ["".join(p) for p in permutations(NAMES)]
ORDER_INDEX = {o: i for i, o in enumerate(ORDERS)}
ROWS = [row_mask(y) for y in range(H)]

# ミノ順の集合を整数のビット集合で持つ。k 手目に「未使用ミノのうち何番目か」を d_k として
# 番号を sum(d_k * WEIGHT[k]) と決めると、1 手進めることが左シフトになる
WEIGHT = [1, 6, 30, 120, 360, 720]


def order_bit(order: str) -> int:
    rest = list(NAMES)
    idx = 0
    for k, c in enumerate(order):
        idx += rest.index(c) * WEIGHT[k]
        rest.remove(c)
    return idx


ORDER_BIT = {o: order_bit(o) for o in ORDERS}


def parse_board(field: str) -> int:
    board = 0
    for y, row in enumerate(reversed(field.split("/"))):
        for x, c in enumerate(row):
            if c != "_":
                board |= 1 << (y * W + x)
    return board


def silhouettes(start: int, row: int, max_height: int) -> list[tuple[int, int, int, int]]:
    """row, row+1 段目 (0 始まり) で TSD を打てる (盤面, ミノ順集合, T のマスク, T の向き) の一覧。

    (使ったミノの集合, 盤面) を状態として、そこに到達できるミノ順の集合を手数ごとに求める。
    """
    target = ROWS[row] | ROWS[row + 1]
    outside = ~target
    # 消去する 2 段の外に置けるブロック数の上限 (T を置く前に 2 段で 16 マス埋まる)
    max_outside = start.bit_count() + 24 - 16
    limit = (1 << (max_height * W)) - 1
    rows = ROWS[:max_height]
    layer = {start << 6: 1}  # 盤面 << 6 | 使ったミノ -> ミノ順集合
    for k in range(6):
        nxt: dict[int, int] = {}
        w = WEIGHT[k]
        for key, orders in layer.items():
            used, board = key & 63, key >> 6
            rank = 0
            for ci, c in enumerate(NAMES):
                if used >> ci & 1:
                    continue
                shifted = orders << (rank * w)
                rank += 1
                used2 = used | 1 << ci
                for m in PIECES[c].placements(board):
                    nb = board | m
                    if nb > limit or (nb & outside).bit_count() > max_outside:
                        continue
                    # T より前にラインが消えてはいけない
                    if any(nb & r == r for r in rows):
                        continue
                    key2 = nb << 6 | used2
                    nxt[key2] = nxt.get(key2, 0) | shifted
        layer = nxt
    out = []
    for key, orders in layer.items():
        hit = find_tsd(key >> 6, target)
        if hit is not None:
            out.append((key >> 6, orders, hit[0], hit[1]))
    return out


# ミノごとに、最下位ビット -> その位置を最下位とするマスクの一覧 (ミノ割りの列挙用)
BY_LOW: dict[str, dict[int, list[int]]] = {}
for _c in NAMES:
    _table: dict[int, list[int]] = {}
    for _m in {m for m in PIECES[_c].mask if m >= 0}:
        _table.setdefault(_m & -_m, []).append(_m)
    BY_LOW[_c] = _table


def tilings(region: int) -> list[dict[str, int]]:
    """region を 6 ミノ (各 1 個) でちょうど覆う方法をすべて求める。"""
    out: list[dict[str, int]] = []
    cur: dict[str, int] = {}

    def dfs(rest: int) -> None:
        if not rest:
            out.append(dict(cur))
            return
        low = rest & -rest
        for c in NAMES:
            if c in cur:
                continue
            for m in BY_LOW[c].get(low, ()):
                if m & rest == m:
                    cur[c] = m
                    dfs(rest ^ m)
                    del cur[c]

    dfs(region)
    return out


def buildable_orders(start: int, tiling: dict[str, int]) -> dict[str, str]:
    """ミノ割りどおりに置けるミノ順 -> ソフトドロップが必要なミノ。"""
    cache: dict[tuple[int, str], bool | None] = {}
    out = {}
    for order in ORDERS:
        board = start
        soft = ""
        for c in order:
            key = (board, c)
            if key not in cache:
                cache[key] = PIECES[c].placements_with_drop(board).get(tiling[c])
            hard = cache[key]
            if hard is None:
                break
            if not hard:
                soft += c
            board |= tiling[c]
        else:
            out[order] = soft
    return out


def field_string(start_field: str, tiling: dict[str, int], t_mask: int, max_height: int) -> str:
    """上の段から '/' 区切り。開始形状のマスは小文字、この巡のミノと T は大文字。"""
    grid = [["_"] * W for _ in range(max_height + 1)]
    for y, row in enumerate(reversed(start_field.split("/"))):
        for x, c in enumerate(row):
            if c != "_":
                grid[y][x] = c.lower()
    for c, m in list(tiling.items()) + [("T", t_mask)]:
        for i in range((max_height + 1) * W):
            if m >> i & 1:
                grid[i // W][i % W] = c
    lines = ["".join(r) for r in reversed(grid)]
    while lines and lines[0] == "_" * W:
        lines.pop(0)
    return "/".join(lines)


def solve(task: tuple[str, str, int, int]) -> list[dict]:
    sid, start_field, row, max_height = task
    start = parse_board(start_field)
    out = []
    for n, (board, orders, t_mask, t_rot) in enumerate(sorted(silhouettes(start, row, max_height))):
        expected = {o for o in ORDERS if orders >> ORDER_BIT[o] & 1}
        found: set[str] = set()
        for tiling in tilings(board ^ start):
            ok = buildable_orders(start, tiling)
            if not ok:
                continue
            found |= set(ok)
            out.append(
                {
                    "start": sid,
                    "start_field": start_field,
                    "tsd_rows": f"{row + 1}-{row + 2}",
                    "silhouette": f"{sid}-{row + 1}-{n + 1:03d}",
                    "t_rotation": "0R2L"[t_rot],
                    "orders_count": len(ok),
                    "field": field_string(start_field, tiling, t_mask, max_height),
                    "orders": " ".join(o + (f":{s}" if s else "") for o, s in ok.items()),
                }
            )
        # 2 つの方法 (盤面の探索とミノ割りごとの確認) で求めたミノ順が一致するはず
        assert found == expected, (sid, row, n, len(found), len(expected))
    return out


def run(starts: dict[str, str], max_height: int, csv_path: Path, processes: int) -> None:
    """全開始形状 x TSD の段を並列に探索し、csv_path に書き出して要約を表示する。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", help="動作確認用: 調べる開始形状")
    parser.add_argument("--rows", nargs="*", type=int, help="動作確認用: TSD の下の段 (1 始まり)")
    parser.add_argument("--keep", action="store_true", help="--only と併用: 既存の CSV にある他の開始形状の行を残す")
    args = parser.parse_args()
    sids = args.only or list(starts)
    rows = [r - 1 for r in args.rows] if args.rows else list(range(max_height - 1))
    tasks = [(sid, starts[sid], row, max_height) for sid in sids for row in rows]

    began = time.time()
    results = []
    with Pool(processes, maxtasksperchild=1) as pool:
        for i, res in enumerate(pool.imap(solve, tasks), 1):
            results.extend(res)
            print(f"\r{i}/{len(tasks)} ({time.time() - began:.0f}s)", end="", file=sys.stderr)
    print(file=sys.stderr)

    if args.keep and csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8") as f:
            results += [r for r in csv.DictReader(f) if r["start"] not in sids]
        position = {sid: i for i, sid in enumerate(starts)}
        results.sort(key=lambda r: position[r["start"]])  # 安定ソートなので開始形状の中の順は変わらない

    fields = ["start", "start_field", "tsd_rows", "silhouette", "t_rotation", "orders_count", "field", "orders"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    for sid in sids:
        mine = [r for r in results if r["start"] == sid]
        covered = {o.split(":")[0] for r in mine for o in r["orders"].split()}
        hard = {o for r in mine for o in r["orders"].split() if ":" not in o}
        per_row = ", ".join(
            f"{row + 1}-{row + 2} 段目 {len({r['silhouette'] for r in mine if r['tsd_rows'] == f'{row + 1}-{row + 2}'})}"
            for row in rows
        )
        print(
            f"{sid}: シルエット {len({r['silhouette'] for r in mine})} 種類 ({per_row}), "
            f"ミノ割り {len(mine)} 種類, TSD を打てるミノ順 {len(covered)}/720 "
            f"(ソフトドロップなし {len(hard)}/720)"
        )
    print(f"wrote {csv_path}")


# ---- 列挙結果の読み込みと、2 つのシルエットの組の網羅率 ----


def load_patterns(csv_path: Path) -> dict[str, dict]:
    """シルエット id -> {id, start, rows, cells, tilings: [(field, {ミノ順: ソフトドロップ対象})]}。"""
    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    patterns: dict[str, dict] = {}
    for r in rows:
        p = patterns.setdefault(
            r["silhouette"],
            {
                "id": r["silhouette"],
                "start": r["start"],
                "rows": r["tsd_rows"],
                # T を置く前に埋まっているマス (ミノの区別なし)
                "cells": "/".join("".join("_" if c in "_T" else "X" for c in line) for line in r["field"].split("/")),
                "tilings": [],
            },
        )
        orders = dict((item.partition(":")[0], item.partition(":")[2]) for item in r["orders"].split())
        p["tilings"].append((r["field"], orders))
    for p in patterns.values():
        p["tilings"].sort(key=lambda t: -len(t[1]))
    return patterns


def coverage(p: dict, max_soft: int) -> int:
    """ソフトドロップ max_soft 回以内で組めるミノ順のビット集合。"""
    bits = 0
    for _, orders in p["tilings"]:
        for o, soft in orders.items():
            if len(soft) <= max_soft:
                bits |= 1 << ORDER_INDEX[o]
    return bits


CONDITIONS = [("no_soft_drop", 0), ("any_soft_drop", 6)]


def pair_report(groups: list[tuple[str, int, list[tuple[str, str, dict[int, int]]]]], pairs_csv: Path, top: int = 100) -> None:
    """グループ (名前, ミノ順の総数, [(id, 盤面, {ソフトドロップ上限: ミノ順集合})]) ごとに全ペアの網羅数を調べる。

    グループ x 条件ごとの上位 top 組を pairs_csv に書き、要約を表示する。
    """
    with pairs_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["group", "condition", "silhouette_1", "silhouette_2", "covered", "total", "field_1", "field_2"])
        for name, total, members in groups:
            line = f"{name}: シルエット {len(members)} 種類"
            for cond, m in CONDITIONS:
                best1 = max((c[m].bit_count() for _, _, c in members), default=0)
                pairs = sorted(
                    (((x[2][m] | y[2][m]).bit_count(), x, y) for x, y in combinations(members, 2)),
                    key=lambda t: -t[0],
                )
                full = sum(n == total for n, _, _ in pairs)
                for n, x, y in pairs[:top]:
                    writer.writerow([name, cond, x[0], y[0], n, total, x[1], y[1]])
                label = "ソフトドロップなし" if m == 0 else "ソフトドロップあり"
                best2 = pairs[0][0] if pairs else 0
                line += f" | {label}: 1 つで最大 {best1}/{total}, 2 つで最大 {best2}/{total} (全網羅 {full} 組)"
            print(line)


def start_groups(patterns: dict[str, dict], sids: list[str]) -> list[tuple[str, int, list[tuple[str, str, dict[int, int]]]]]:
    """開始形状ごとのグループ (ミノ順 720 通り)。"""
    return [
        (
            sid,
            720,
            [
                (p["id"], p["tilings"][0][0], {m: coverage(p, m) for _, m in CONDITIONS})
                for p in patterns.values()
                if p["start"] == sid
            ],
        )
        for sid in sids
    ]
