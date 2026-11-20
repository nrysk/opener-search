"""10/patterns.csv から、始動ミノごとに「2 つのシルエットの組」の網羅率を求める。

始動ミノ (I O S L。Z・J は S・L の反転) ごとに、シルエットを 2 つ覚えたとき、どちらかを組める
ミノ順がそのミノで始まる 120 通りのうちいくつあるかを全ペアについて調べる
(定義は 05/pairs.py と同じ。TSS の段は問わない)。

入力: 10/patterns.csv
出力: 10/pairs.csv (始動ミノ x 条件ごとの上位ペア)
"""

from __future__ import annotations

from search import CSV_PATH, HERE
from visualize import FIRSTS

from lib.followup import CONDITIONS, ORDERS, coverage, load_patterns, pair_report

PAIRS_CSV = HERE / "pairs.csv"


def main() -> None:
    patterns = load_patterns(CSV_PATH)
    groups = []
    for first in FIRSTS:
        mask = sum(1 << i for i, o in enumerate(ORDERS) if o[0] == first)
        members = []
        for p in patterns.values():
            cov = {m: coverage(p, m) & mask for _, m in CONDITIONS}
            if any(cov.values()):
                members.append((p["id"], p["tilings"][0][0], cov))
        groups.append((f"{first} 始動", 120, members))
    pair_report(groups, PAIRS_CSV)
    print(f"wrote {PAIRS_CSV.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
