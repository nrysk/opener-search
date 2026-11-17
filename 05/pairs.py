"""05/patterns.csv から「A・B 共通のシルエット」と「2 つのシルエットの組」の網羅率を求める。

- A・B 共通のシルエット: 同じテンプレの 2 つの開始形状 (A, B) のどちらからでも、
  T を置く前に埋まっているマス (1巡目の残りを含む) と TSD の段が同じになるもの。
  1巡目がどちらで終わっても同じ形を目指せる
- 2 つの組: シルエットを 2 つ覚えたとき、どちらかを組めるミノ順がいくつあるか。
  開始形状ごと (720 通り) と、A・B 共通のシルエットだけを使う場合
  (A の 720 通り + B の 720 通り = 1440 通り) について、全ペアを調べる

入力: 05/patterns.csv
出力: 05/common.csv (A・B 共通のシルエット), 05/pairs.csv (グループ x 条件ごとの上位ペア)
"""

from __future__ import annotations

import csv

from search import CSV_PATH, HERE, STARTS

from lib.followup import CONDITIONS, coverage, load_patterns, pair_report, start_groups

COMMON_CSV = HERE / "common.csv"
PAIRS_CSV = HERE / "pairs.csv"


def common_silhouettes(patterns: dict[str, dict]) -> dict[str, list[tuple[dict, dict]]]:
    """テンプレ番号 -> A・B 共通のシルエット (A 側, B 側) の一覧。"""
    out: dict[str, list[tuple[dict, dict]]] = {}
    for template in sorted({sid[:-1] for sid in STARTS}, key=int):
        a = {(p["rows"], p["cells"]): p for p in patterns.values() if p["start"] == template + "A"}
        b = {(p["rows"], p["cells"]): p for p in patterns.values() if p["start"] == template + "B"}
        out[template] = [(a[k], b[k]) for k in sorted(a.keys() & b.keys())]
    return out


def main() -> None:
    patterns = load_patterns(CSV_PATH)
    common = common_silhouettes(patterns)

    with COMMON_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["template", "tsd_rows", "silhouette_a", "silhouette_b"]
            + [f"orders_{s}_{c}" for s in "ab" for c, _ in CONDITIONS]
            + ["field_a", "field_b"]
        )
        for template, items in common.items():
            for pa, pb in items:
                writer.writerow(
                    [template, pa["rows"], pa["id"], pb["id"]]
                    + [coverage(p, m).bit_count() for p in (pa, pb) for _, m in CONDITIONS]
                    + [pa["tilings"][0][0], pb["tilings"][0][0]]
                )

    # グループ: 開始形状ごと (720 通り)、テンプレごとの A・B 共通 (A 720 + B 720 = 1440 通り)
    groups = start_groups(patterns, list(STARTS))
    for template, items in common.items():
        members = [
            (
                f"{pa['id']}+{pb['id']}",
                pa["tilings"][0][0],
                {m: coverage(pa, m) | coverage(pb, m) << 720 for _, m in CONDITIONS},
            )
            for pa, pb in items
        ]
        groups.append((template + "AB", 1440, members))
    pair_report(groups, PAIRS_CSV)
    print(f"wrote {COMMON_CSV.relative_to(HERE.parent)}, {PAIRS_CSV.name}")


if __name__ == "__main__":
    main()
