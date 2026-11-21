"""14/LJ/patterns.csv から「2 つのシルエットの組」の網羅率を求める (定義は 05/pairs.py と同じ)。

開始形状ごとに、I が Z より先に来る 360 通りだけを数えるグループ (visualize.py のタブ「I→Z」) と、
720 通りすべてを数えるグループを調べる。

入力: 14/LJ/patterns.csv
出力: 14/LJ/pairs.csv (グループ x 条件ごとの上位ペア)
"""

from __future__ import annotations

from search import CSV_PATH, HERE, STARTS
from visualize import BEFORE

from lib.followup import CONDITIONS, ORDERS, coverage, load_patterns, pair_report

PAIRS_CSV = HERE / "pairs.csv"


def main() -> None:
    patterns = load_patterns(CSV_PATH)
    a, b = BEFORE
    mask = sum(1 << i for i, o in enumerate(ORDERS) if o.index(a) < o.index(b))
    groups = []
    for sid in STARTS:
        mine = [p for p in patterns.values() if p["start"] == sid]
        for name, m, total in ((f"{sid} {a}→{b}", mask, 360), (f"{sid} すべて", (1 << 720) - 1, 720)):
            members = [(p["id"], p["tilings"][0][0], {c: coverage(p, c) & m for _, c in CONDITIONS}) for p in mine]
            groups.append((name, total, [x for x in members if any(x[2].values())]))
    pair_report(groups, PAIRS_CSV)
    print(f"wrote {PAIRS_CSV.relative_to(HERE.parent.parent)}")


if __name__ == "__main__":
    main()
