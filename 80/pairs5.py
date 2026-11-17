"""80/patterns5.csv から「2 つのシルエットの組」の網羅率を求める。

シルエットを 2 つ覚えたとき、どちらかを組めるミノ順が 720 通りのうちいくつあるかを、
全シルエット / 途中消しなしのシルエットだけ、のそれぞれについて全ペアで調べる。

入力: 80/patterns5.csv
出力: 80/pairs5.csv (グループ x 条件ごとの上位ペア)
"""

from __future__ import annotations

import csv

from search5 import CSV_PATH, HERE

from lib.followup import CONDITIONS, coverage, pair_report

PAIRS_CSV = HERE / "pairs5.csv"
GROUPS = {"すべて": lambda p: True, "途中消しなし": lambda p: p["mid_clears"] == 0, "途中消しあり": lambda p: p["mid_clears"] > 0}


def load_patterns5() -> dict[str, dict]:
    """シルエット id -> lib.followup.load_patterns と同じ形の値 (mid_clears, note を追加)。

    ソフトドロップは回数だけを記録しているので、対象ミノの代わりに回数ぶんの '*' を入れる。
    """
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    patterns: dict[str, dict] = {}
    for r in rows:
        n = int(r["mid_clears"])
        p = patterns.setdefault(
            r["silhouette"],
            {
                "id": r["silhouette"],
                "start": "albatross",
                "rows": r["tsd_rows"],
                "mid_clears": n,
                "note": f"途中消し {n} 段" if n else "",
                "tilings": [],
            },
        )
        orders = {}
        for item in r["orders"].split():
            order, _, soft = item.partition(":")
            orders[order] = "*" * int(soft or 0)
        p["tilings"].append((r["field"], orders))
    for p in patterns.values():
        p["tilings"].sort(key=lambda t: -len(t[1]))
    return patterns


def main() -> None:
    patterns = load_patterns5()
    groups = [
        (name, 720, [(p["id"], p["tilings"][0][0], {m: coverage(p, m) for _, m in CONDITIONS}) for p in patterns.values() if keep(p)])
        for name, keep in GROUPS.items()
    ]
    pair_report(groups, PAIRS_CSV)
    print(f"wrote {PAIRS_CSV.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
