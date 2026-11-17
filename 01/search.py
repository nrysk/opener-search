"""開幕 TSD とアルバトロス TSD のテンプレを、各ミノ順で再現できるかの調査 (SRS)。

00 と同じく最悪ケースとして「T が最初に来てホールドに入り、残り 6 ミノ (I J L S Z O) を
来た順にホールドなしで置き、最後に T で TSD を打つ」状況を考える。
テンプレでは各ミノの置き場所が決まっているので、ミノ順 720 通りそれぞれについて
来た順にその場所へ置けるかを確かめるだけでよい。

- 再現可能: 6 ミノすべてが、来た時点の盤面で操作により到達でき、かつ接地する
  (支えになるミノが先に置かれていないと宙に浮くので置けない)
- ソフトドロップ回数: ハードドロップだけでは置けないミノの数。
  「空中で向きと列を決めて真下に落とす」で届かない位置を、ソフトドロップが必要と数える。
  最後の T (TSD) は必ずソフトドロップが要るので回数には含めない

出力: 01/templates.csv (可視化は 01/visualize.py)
"""

from __future__ import annotations

import csv
import sys
from itertools import permutations
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.srs import PIECES, W, Piece, find_tsd, row_mask  # noqa: E402

CSV_PATH = HERE / "templates.csv"

# テンプレ (上の段から)。T は TSD を打ったあとの位置
KAIMAKU_1 = """
___JJJ____
L__ZZJS___
LTTTZZSSOO
LLTIIIISOO
"""
KAIMAKU_2 = """
___SZZ____
L__SSZZ___
LTTTSJJJOO
LLTIIIIJOO
"""
ALBATROSS = """
I___ZZ____
ISTTTZZJJJ
ISSTOOLLLJ
I_S_OOL___
"""


def parse(text: str) -> list[str]:
    return text.split()


def mirror(rows: list[str]) -> list[str]:
    swap = str.maketrans("SZLJ", "ZSJL")
    return [row[::-1].translate(swap) for row in rows]


# (id, 系統, 反転形か, 盤面)
TEMPLATES = [
    ("kaimaku_1", "kaimaku", 0, parse(KAIMAKU_1)),
    ("kaimaku_2", "kaimaku", 0, parse(KAIMAKU_2)),
    ("kaimaku_1_mirror", "kaimaku", 1, mirror(parse(KAIMAKU_1))),
    ("kaimaku_2_mirror", "kaimaku", 1, mirror(parse(KAIMAKU_2))),
    ("albatross_l", "albatross", 0, parse(ALBATROSS)),
    ("albatross_r", "albatross", 1, mirror(parse(ALBATROSS))),
]


def piece_masks(rows: list[str]) -> dict[str, int]:
    masks: dict[str, int] = {}
    for y, row in enumerate(reversed(rows)):
        for x, c in enumerate(row):
            if c != "_":
                masks[c] = masks.get(c, 0) | 1 << (y * W + x)
    return masks


def place(piece: Piece, board: int, target: int) -> str | None:
    """board 上で piece を target の位置に置けるか。'hard' / 'soft' / None (置けない)。"""
    mask, down = piece.mask, piece.down
    height = (board.bit_length() + W - 1) // W
    result = None
    for s in piece.reachable(board):
        if mask[s] != target:
            continue
        d = down[s]
        if not (d < 0 or mask[d] & board):
            continue  # 接地しない
        result = "soft"
        # 同じ向き・同じ列のまま真上が空まで抜けていればハードドロップで置ける
        r, x, y = piece.decode(s)
        if all(not mask[piece.index(r, x, yy)] & board for yy in range(y + 1, height + 1)):
            return "hard"
    return result


def check(order: str, masks: dict[str, int]) -> dict:
    board = 0
    soft = ""
    for c in order:
        how = place(PIECES[c], board, masks[c])
        if how is None:
            return {"buildable": 0, "soft_drops": "", "soft_drop_pieces": "", "blocked_piece": c}
        if how == "soft":
            soft += c
        board |= masks[c]
    return {"buildable": 1, "soft_drops": len(soft), "soft_drop_pieces": soft, "blocked_piece": ""}


def verify_tsd(name: str, rows: list[str], masks: dict[str, int]) -> None:
    """テンプレ完成後に、T が実際に T-Spin Double として入ることを確かめる。"""
    board = sum(m for c, m in masks.items() if c != "T")
    target = 0
    for y, row in enumerate(reversed(rows)):
        if "_" not in row:
            target |= row_mask(y)
    hit = find_tsd(board, target)
    assert hit is not None and hit[0] == masks["T"], f"{name}: TSD にならない"


def main() -> None:
    orders = ["".join(p) for p in permutations("IJLSZO")]
    results = []
    for name, family, mirrored, rows in TEMPLATES:
        masks = piece_masks(rows)
        assert all(masks[c].bit_count() == 4 for c in "IJLSZOT"), name
        verify_tsd(name, rows, masks)
        for order in orders:
            results.append(
                {"order": order, "template": name, "family": family, "mirrored": mirrored}
                | check(order, masks)
                | {"field": "/".join(rows)}
            )

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    def covered(names: set[str], max_soft: int) -> set[str]:
        return {
            r["order"]
            for r in results
            if r["template"] in names and r["buildable"] and r["soft_drops"] <= max_soft
        }

    all_names = {t[0] for t in TEMPLATES}
    given = all_names - {"kaimaku_1_mirror", "kaimaku_2_mirror"}
    for label, names in (("画像の形のみ", given), ("開幕 TSD の反転形も含む", all_names)):
        print(f"[{label}]")
        for soft_label, max_soft in (("ソフトドロップ制限なし", 6), ("ソフトドロップなし", 0)):
            k = covered({n for n in names if n.startswith("kaimaku")}, max_soft)
            a = covered({n for n in names if n.startswith("albatross")}, max_soft)
            print(
                f"  {soft_label}: 開幕 TSD {len(k)}/720, アルバトロス {len(a)}/720, "
                f"どちらか {len(k | a)}/720"
            )
    print(f"wrote {CSV_PATH.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
