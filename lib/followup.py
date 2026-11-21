"""ある形 (前の巡の TSD 後に残る形や空の盤面) から、次の 1 巡で T スピンを打てる形を全列挙する (SRS)。

開始形状に 6 ミノ (I J L S Z O) を来た順にホールドなしで置き、最後に来た T で TSD (または TSS) を打つ。
720 通りのミノ順すべてについて、T スピンを打てる最終形を求める。05, 06, 10 で共有する。

- lines = 1 / 2 / 3 で TSS / TSD / TST (どれも Mini は除き、ちょうどその段数だけ消えるもの)
- 重い盤面探索は C++ (lib/spin_search.cpp、初回実行時に build/ へ自動ビルド)。ミノ割りの列挙と
  ミノ順ごとの検証は Python で行い、両者の結果が一致することを確かめている
- T を置く前の高さは max_height 段以下に制限する (制限なしでは組み合わせ爆発する)
- T を置く前にラインが消える置き方は扱わない
- 消す段は下の段が 1 段目から (max_height-1) 段目までをすべて調べる
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
import heapq
import os
import subprocess
import sys
import time
from itertools import combinations, permutations
from multiprocessing import Pool
from pathlib import Path

from lib.srs import PIECES, H, W, find_tspin, row_mask

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


# 消す段数 -> T を置く前に消す段の中で埋まっている必要があるマス数 (TSS は 10 - 3、TSD は 20 - 4、TST は 30 - 4)
NEED = {1: W - 3, 2: 2 * W - 4, 3: 3 * W - 4}
SPIN = {1: "TSS", 2: "TSD", 3: "TST"}


def is_contiguous(rows: tuple[int, ...]) -> bool:
    return rows[-1] - rows[0] == len(rows) - 1


def need_for(rows: tuple[int, ...]) -> int:
    """消す段 rows (0 始まり) に対し、T を置く前に埋まっている必要があるマス数。

    連続した段は NEED。1 段あけた 2 段 (縦向きの T で上下の段だけを消す TSD) は T が各段に 1 マスしか入らないので 18。
    """
    return NEED[len(rows)] if is_contiguous(rows) else len(rows) * W - len(rows)


def rows_label(rows: tuple[int, ...]) -> str:
    """消す段の表記 (1 始まり)。TSS は "1"、TSD は "1-2"、TST は "1-3"、あいだの段を残す TSD は "2,4"。"""
    if not is_contiguous(rows):
        return ",".join(str(r + 1) for r in rows)
    return f"{rows[0] + 1}-{rows[-1] + 1}" if len(rows) > 1 else str(rows[0] + 1)


def rows_id(rows: tuple[int, ...]) -> str:
    """シルエット id に入れる消す段。連続した段は一番下の段 (1 始まり)、そうでなければ "2_4" のように並べる。"""
    return str(rows[0] + 1) if is_contiguous(rows) else "_".join(str(r + 1) for r in rows)


def silhouettes(
    start: int, rows: tuple[int, ...], max_height: int, overhang: str = ""
) -> list[tuple[int, int, int, int]]:
    """段 rows (0 始まり) を T スピンでちょうど消せる (盤面, ミノ順集合, T のマスク, T の向き) の一覧。

    盤面とミノ順集合は C++ (lib/spin_search.cpp) で求め、T の位置はここで find_tspin を使って求める。
    """
    target = 0
    for r in rows:
        target |= ROWS[r]
    res = subprocess.run(
        [str(spin_search_binary()), f"{start:x}", ",".join(map(str, rows)), str(max_height), overhang or "-"],
        capture_output=True, text=True, check=True,
    )
    out = []
    for line in res.stdout.splitlines():
        board_hex, orders_bin = line.split()
        board = int(board_hex, 16)
        hit = find_tspin(board, target, need_for(rows))
        assert hit is not None, (rows, board_hex)
        out.append((board, int(orders_bin, 2), hit[0], hit[1]))
    return out


SPIN_SEARCH_SRC = Path(__file__).resolve().parent / "spin_search.cpp"
SPIN_SEARCH_BIN = Path(__file__).resolve().parent.parent / "build" / "spin_search"


def spin_search_binary() -> Path:
    """C++ の探索プログラムのパス。無いかソースより古ければビルドする。"""
    src, binary = SPIN_SEARCH_SRC, SPIN_SEARCH_BIN
    if not binary.exists() or binary.stat().st_mtime < src.stat().st_mtime:
        binary.parent.mkdir(exist_ok=True)
        cxx = os.environ.get("CXX", "c++")
        subprocess.run([cxx, "-O2", "-std=c++20", "-o", str(binary), str(src)], check=True)
    return binary


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
    grid = [["_"] * W for _ in range(H)]  # I ミノがはみ出す場合もあるので盤面の高さぶん用意して、上の空行を落とす
    for y, row in enumerate(reversed(start_field.split("/"))):
        for x, c in enumerate(row):
            if c != "_":
                grid[y][x] = c.lower()
    for c, m in list(tiling.items()) + [("T", t_mask)]:
        for i in range(H * W):
            if m >> i & 1:
                grid[i // W][i % W] = c
    lines = ["".join(r) for r in reversed(grid)]
    while lines and lines[0] == "_" * W:
        lines.pop(0)
    return "/".join(lines)


def fits_height(tiling: dict[str, int], max_height: int, overhang: str) -> bool:
    """ミノ割りが高さの上限を守っているか。overhang に含まれるミノは、一部が上限内にあればはみ出してよい。"""
    limit = (1 << (max_height * W)) - 1
    return all(
        (m & limit) != 0 if c in overhang else m & ~limit == 0
        for c, m in tiling.items()
    )


def solve(task: tuple[str, str, tuple[int, ...], int, str]) -> list[dict]:
    sid, start_field, rows, max_height, overhang = task
    start = parse_board(start_field)
    out = []
    for n, (board, orders, t_mask, t_rot) in enumerate(sorted(silhouettes(start, rows, max_height, overhang))):
        expected = {o for o in ORDERS if orders >> ORDER_BIT[o] & 1}
        found: set[str] = set()
        for tiling in tilings(board ^ start):
            # 同じシルエットでも、はみ出してよくないミノが高さの上限をはみ出すミノ割りは使えない
            if not fits_height(tiling, max_height, overhang):
                continue
            ok = buildable_orders(start, tiling)
            if not ok:
                continue
            found |= set(ok)
            out.append(
                {
                    "start": sid,
                    "start_field": start_field,
                    ROWS_COLUMN[len(rows)]: rows_label(rows),
                    "silhouette": f"{sid}-{rows_id(rows)}-{n + 1:03d}",
                    "t_rotation": "0R2L"[t_rot],
                    "orders_count": len(ok),
                    "field": field_string(start_field, tiling, t_mask, max_height),
                    "orders": " ".join(o + (f":{s}" if s else "") for o, s in ok.items()),
                }
            )
        # 2 つの方法 (盤面の探索とミノ割りごとの確認) で求めたミノ順が一致するはず
        assert found == expected, (sid, rows, n, len(found), len(expected))
    return out


# CSV で消す段を書く列の名前 (05, 06 の CSV との互換のため TSD は tsd_rows)
ROWS_COLUMN = {1: "tss_rows", 2: "tsd_rows", 3: "tst_rows"}


def run(
    starts: dict[str, str],
    max_height: int,
    csv_path: Path,
    processes: int,
    lines: int = 2,
    spin_rows: list[int | tuple[int, ...]] | None = None,
    overhang: str = "",
) -> None:
    """全開始形状 x 消す段を並列に探索し、csv_path に書き出して要約を表示する。

    spin_rows は調べる消す段 (1 始まり) の一覧。整数は一番下の段で、そこから lines 段を消す。
    タプルは消す段そのもの (例: (2, 4) は 3 段目を残して 2・4 段目を消す TSD)。省略時は 1 段目から (max_height-1) 段目まで。
    overhang はミノの文字の並び (例: "I"、"IJLSZO")。そのミノは一部が max_height 段以内にあれば上にはみ出してよい。
    """
    spin = SPIN[lines]
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", help="動作確認用: 調べる開始形状")
    parser.add_argument("--rows", nargs="*", type=int, help=f"動作確認用: {spin} の下の段 (1 始まり)")
    parser.add_argument("--keep", action="store_true", help="--only と併用: 既存の CSV にある他の開始形状の行を残す")
    args = parser.parse_args()
    sids = args.only or list(starts)
    rows = [
        tuple(x - 1 for x in r) if isinstance(r, tuple) else tuple(range(r - 1, r - 1 + lines))
        for r in args.rows or spin_rows or range(1, max_height)
    ]
    tasks = [(sid, starts[sid], r, max_height, overhang) for sid in sids for r in rows]

    spin_search_binary()  # 並列実行の前に一度だけビルドしておく
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

    fields = ["start", "start_field", ROWS_COLUMN[lines], "silhouette", "t_rotation", "orders_count", "field", "orders"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    for sid in sids:
        mine = [r for r in results if r["start"] == sid]
        covered = {o.split(":")[0] for r in mine for o in r["orders"].split()}
        hard = {o for r in mine for o in r["orders"].split() if ":" not in o}
        per_row = ", ".join(
            f"{rows_label(t)} 段目 {len({r['silhouette'] for r in mine if r[ROWS_COLUMN[lines]] == rows_label(t)})}"
            for t in rows
        )
        print(
            f"{sid}: シルエット {len({r['silhouette'] for r in mine})} 種類 ({per_row}), "
            f"ミノ割り {len(mine)} 種類, {spin} を打てるミノ順 {len(covered)}/720 "
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
                "rows": next(r[c] for c in ROWS_COLUMN.values() if c in r),
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
    シルエットが多くても計算できるよう、ミノ順集合が同じシルエットはまとめて 1 回だけ比べる
    (全網羅の組数は、まとめたシルエットの数を掛けて数えるので正確)。上位の組には、まとめたうちの
    先頭のシルエットを代表として書く。
    """
    with pairs_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["group", "condition", "silhouette_1", "silhouette_2", "covered", "total", "field_1", "field_2"])
        for name, total, members in groups:
            line = f"{name}: シルエット {len(members)} 種類"
            for cond, m in CONDITIONS:
                best1 = max((c[m].bit_count() for _, _, c in members), default=0)
                same: dict[int, list] = {}  # ミノ順集合 -> それを持つシルエット (members の順)
                for x in members:
                    if x[2][m]:  # この条件で 1 通りも組めないシルエットは組に入れない
                        same.setdefault(x[2][m], []).append(x)
                uniq = list(same.items())
                full = 0
                cands = []  # (網羅数, -登場順, シルエット 1, シルエット 2)
                for i, (a, xs) in enumerate(uniq):
                    if len(xs) > 1:
                        n = a.bit_count()
                        full += len(xs) * (len(xs) - 1) // 2 if n == total else 0
                        cands.append((n, -i * len(uniq) - i, xs[0], xs[1]))
                    for j in range(i + 1, len(uniq)):
                        b, ys = uniq[j]
                        n = (a | b).bit_count()
                        if n == total:
                            full += len(xs) * len(ys)
                        cands.append((n, -i * len(uniq) - j, xs[0], ys[0]))
                pairs = heapq.nlargest(top, cands, key=lambda t: t[:2])
                for n, _, x, y in pairs:
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
