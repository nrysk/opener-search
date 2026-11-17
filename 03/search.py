"""開幕 TSD とアルバトロス TSD を最もよく補完する「テンプレ 2 つの組」を探す (SRS)。

前提は 00-02 と同じ最悪ケース (T が最初に来てホールドに入り、残り 6 ミノを来た順に
ホールドなしで置き、最後に T で TSD を打つ)。

- 対象のミノ順: 01 で開幕 TSD でもアルバトロス TSD でも組めなかったミノ順
  (ソフトドロップなしで組めなかった 338 通り / ソフトドロップありでも組めなかった 220 通り)
- 候補のテンプレ: data/templates.csv のうち、6 ミノ + T でできていて、T が実際に
  T-Spin Double になる形。左右反転で同じになる形は 1 つにまとめ、開幕 TSD と
  アルバトロス TSD 自身は除く
- 各候補について、720 通りのミノ順それぞれで再現できるか・ソフトドロップが何回要るかを調べ
  (定義は 01 と同じ)、2 つの候補の和集合が対象のミノ順をいくつ網羅するかで順位を付ける

入力: data/templates.csv, 01/templates.csv
出力: 03/candidates.csv (候補テンプレ), 03/coverage.csv (候補 x ミノ順。再現できる行のみ),
      03/pairs.csv (全ペアの網羅数。左右反転形も使う場合)。可視化は 03/visualize.py
"""

from __future__ import annotations

import csv
import sys
from itertools import combinations, permutations
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.srs import PIECES, W, find_tsd, row_mask  # noqa: E402

TEMPLATES_CSV = HERE.parent / "data" / "templates.csv"
BASELINE_CSV = HERE.parent / "01" / "templates.csv"
CANDIDATES_CSV = HERE / "candidates.csv"
COVERAGE_CSV = HERE / "coverage.csv"
PAIRS_CSV = HERE / "pairs.csv"

ORDERS = ["".join(p) for p in permutations("IJLSZO")]
SWAP = str.maketrans("SZLJ", "ZSJL")


def mirror_field(field: str) -> str:
    return "/".join(row[::-1].translate(SWAP) for row in field.split("/"))


def mirror_order(order: str) -> str:
    return order.translate(SWAP)


def piece_masks(field: str) -> dict[str, int]:
    masks: dict[str, int] = {}
    for y, row in enumerate(reversed(field.split("/"))):
        for x, c in enumerate(row):
            if c != "_":
                masks[c] = masks.get(c, 0) | 1 << (y * W + x)
    return masks


def is_tsd(field: str, masks: dict[str, int]) -> bool:
    """6 ミノを置いたあと、T がテンプレの位置に T-Spin Double として入るか。"""
    board = sum(m for c, m in masks.items() if c != "T")
    target = 0
    for y, row in enumerate(reversed(field.split("/"))):
        if "_" not in row:
            target |= row_mask(y)
    if target.bit_count() != 2 * W:
        return False
    hit = find_tsd(board, target)
    return hit is not None and hit[0] == masks["T"]


def check(order: str, masks: dict[str, int]) -> str | None:
    """order の順にテンプレどおり置けるなら、ソフトドロップが必要なミノを返す (置けなければ None)。"""
    board = 0
    soft = ""
    for c in order:
        drops = PIECES[c].placements_with_drop(board)
        if masks[c] not in drops:
            return None
        if not drops[masks[c]]:
            soft += c
        board |= masks[c]
    return soft


def baseline() -> tuple[set[str], dict[str, set[str]]]:
    """01 の結果から、開幕 TSD・アルバトロス TSD の形と、対象のミノ順 (hard / soft) を得る。"""
    with BASELINE_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    shapes = {r["field"] for r in rows}
    used = [r for r in rows if not (r["family"] == "kaimaku" and r["mirrored"] == "1")]
    by_soft = {r["order"] for r in used if r["buildable"] == "1"}
    by_hard = {r["order"] for r in used if r["buildable"] == "1" and r["soft_drops"] == "0"}
    return shapes, {"hard": set(ORDERS) - by_hard, "soft": set(ORDERS) - by_soft}


def load_candidates(exclude: set[str]) -> tuple[list[dict], list[dict]]:
    """候補テンプレと、除外したテンプレ (理由つき) を返す。"""
    with TEMPLATES_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_shape: dict[str, dict] = {}
    skipped = []
    for r in rows:
        field = r["field"]
        label = r["name"] + (f" ({r['note']})" if r["note"] else "")
        masks = piece_masks(field)
        if sorted(masks) != sorted("IJLSZOT") or any(m.bit_count() != 4 for m in masks.values()):
            reason = "6 ミノ + T ではない"
        elif field in exclude or mirror_field(field) in exclude:
            reason = "開幕 TSD / アルバトロス TSD 自身"
        elif not is_tsd(field, masks):
            reason = "T が T-Spin Double にならない"
        else:
            key = min(field, mirror_field(field))
            c = by_shape.setdefault(key, {"id": r["id"], "labels": [], "field": field})
            if label not in c["labels"]:
                c["labels"].append(label)
            continue
        skipped.append({"id": r["id"], "label": label, "reason": reason})
    return list(by_shape.values()), skipped


def main() -> None:
    shapes, targets = baseline()
    candidates, skipped = load_candidates(shapes)
    print(f"候補テンプレ: {len(candidates)} 個 (除外 {len(skipped)} 行)")
    for reason in sorted({s["reason"] for s in skipped}):
        names = sorted({s["label"] for s in skipped if s["reason"] == reason})
        print(f"  除外 [{reason}]: {', '.join(names)}")

    # soft[id][order] = ソフトドロップが必要なミノ (テンプレの向きそのまま)
    soft: dict[str, dict[str, str]] = {}
    for c in candidates:
        masks = piece_masks(c["field"])
        soft[c["id"]] = {o: s for o in ORDERS if (s := check(o, masks)) is not None}

    with CANDIDATES_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "field", "buildable_orders"])
        for c in candidates:
            writer.writerow([c["id"], " / ".join(c["labels"]), c["field"], len(soft[c["id"]])])

    with COVERAGE_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "order", "soft_drops", "soft_drop_pieces"])
        for c in candidates:
            for o, s in soft[c["id"]].items():
                writer.writerow([c["id"], o, len(s), s])

    # 左右反転形も使う場合: 反転形でミノ順 o を組める <=> 元の形で mirror_order(o) を組める
    def covered(cid: str, max_soft: int) -> set[str]:
        own = {o for o, s in soft[cid].items() if len(s) <= max_soft}
        return own | {mirror_order(o) for o in own}

    configs = [("hard", 0), ("hard", 6), ("soft", 0), ("soft", 6)]
    cover = {(c["id"], cfg): covered(c["id"], cfg[1]) & targets[cfg[0]] for c in candidates for cfg in configs}
    name = {c["id"]: " / ".join(c["labels"]) for c in candidates}
    pairs = []
    for a, b in combinations([c["id"] for c in candidates], 2):
        pairs.append([a, b, name[a], name[b]] + [len(cover[a, cfg] | cover[b, cfg]) for cfg in configs])

    with PAIRS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["id_a", "id_b", "name_a", "name_b"]
            + [f"covered_{t}_target_{'no_soft_drop' if m == 0 else 'any_soft_drop'}" for t, m in configs]
        )
        writer.writerows(sorted(pairs, key=lambda p: [-x for x in p[4:]]))

    labels = {"hard": "ソフトドロップなしでは組めないミノ順", "soft": "ソフトドロップありでも組めないミノ順"}
    for i, (t, m) in enumerate(configs):
        print(f"[対象: {labels[t]} {len(targets[t])} 通り / 条件: ソフトドロップ{'なし' if m == 0 else '制限なし'}]")
        for p in sorted(pairs, key=lambda p: -p[4 + i])[:3]:
            print(f"  {p[4 + i]:3d}  {p[2]} + {p[3]}")
    print(f"wrote {CANDIDATES_CSV.relative_to(HERE.parent)}, {COVERAGE_CSV.name}, {PAIRS_CSV.name}")


if __name__ == "__main__":
    main()
