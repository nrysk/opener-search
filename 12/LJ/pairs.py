"""12/LJ/patterns.csv から「2 つのシルエットの組」の網羅率を求める (定義は 05/pairs.py と同じ)。

入力: 12/LJ/patterns.csv
出力: 12/LJ/pairs.csv (開始形状 x 条件ごとの上位ペア)
"""

from __future__ import annotations

from search import CSV_PATH, HERE, STARTS

from lib.followup import load_patterns, pair_report, start_groups

PAIRS_CSV = HERE / "pairs.csv"


def main() -> None:
    pair_report(start_groups(load_patterns(CSV_PATH), list(STARTS)), PAIRS_CSV)
    print(f"wrote {PAIRS_CSV.relative_to(HERE.parent.parent)}")


if __name__ == "__main__":
    main()
