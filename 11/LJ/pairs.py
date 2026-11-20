"""11/LJ/patterns.csv から、組ごとに「2 つのシルエットの組」の網羅率を求める (定義は 05/pairs.py と同じ)。

組 (A: TSS-2-4422 / B: TSS-2-4743) の 2 つの開始形状のシルエットをまとめて 1 つのグループとし、
どちらの開始形状のシルエットでもよいので 2 つ覚えたとき、720 通りのミノ順のうちいくつで TST を打てるかを調べる。

入力: 11/LJ/patterns.csv
出力: 11/LJ/pairs.csv (組 x 条件ごとの上位ペア)
"""

from __future__ import annotations

from search import CSV_PATH, GROUPS, HERE

from lib.followup import CONDITIONS, coverage, load_patterns, pair_report

PAIRS_CSV = HERE / "pairs.csv"


def main() -> None:
    patterns = load_patterns(CSV_PATH)
    groups = []
    for gid, (_, sids) in GROUPS.items():
        members = [
            (p["id"], p["tilings"][0][0], {m: coverage(p, m) for _, m in CONDITIONS})
            for p in patterns.values()
            if p["start"] in sids
        ]
        groups.append((gid, 720, members))
    pair_report(groups, PAIRS_CSV)
    print(f"wrote {PAIRS_CSV.relative_to(HERE.parent.parent)}")


if __name__ == "__main__":
    main()
