"""1巡目に確定で TSD を打てるかの全探索 (ぷよぷよテトリス準拠 / SRS)。

最悪ケースとして「T が最初に来てホールドに入り、残り 6 ミノ (I J L S Z O) を
来た順にホールドなしで置き、最後に T で TSD を打つ」状況を考える。

- ミノ順 720 通りは左右反転 (S<->Z, L<->J) で 360 通りに減らす (L が J より先のものを代表とする)
- TSD で消す段を「1,2 段目」「2,3 段目」に固定して別々に探索する → 360 x 2 = 720 通り
- 各ミノの設置は SRS (壁蹴り込み) で実際に到達可能な位置だけを使う
- T スピン判定は 3 コーナールール。前方 2 隅が埋まっていない場合は Mini
  (ただし 5 番目のキックで入った場合は Mini にならない) とし、Mini は TSD と認めない

出力: 00/tsd.csv (可視化は 00/visualize.py)
"""

from __future__ import annotations

import csv
import sys
import time
from itertools import permutations
from multiprocessing import Pool
from pathlib import Path

MAX_OUTSIDE = 8  # 消去する 2 段の外に置けるブロック数の上限 (24 - 16)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.srs import PIECES, field_string, find_tsd, row_mask  # noqa: E402

CSV_PATH = HERE / "tsd.csv"


def solve(task: tuple[str, int]) -> dict:
    """ミノ順 order を順に置き、row 段目と row+1 段目 (0 始まり) を T で消す形を探す。"""
    order, row = task
    target = row_mask(row) | row_mask(row + 1)
    targets = (row_mask(row), row_mask(row + 1))
    pieces = [PIECES[c] for c in order]
    dead: set[tuple[int, int]] = set()  # 解がないと分かった (手数, 盤面)
    nodes = 0

    def dfs(board: int, i: int) -> list[int] | None:
        nonlocal nodes
        nodes += 1
        if i == len(pieces):
            hit = find_tsd(board, target)
            return None if hit is None else [hit[0], hit[1], hit[2]]
        for m in pieces[i].placements(board):
            nb = board | m
            # 消す 2 段の外に置けるのは 8 ブロックまで (これで他の段のライン消去も起きない)
            if (nb & ~target).bit_count() > MAX_OUTSIDE:
                continue
            # 消す段が T より前に埋まってはいけない
            if nb & targets[0] == targets[0] or nb & targets[1] == targets[1]:
                continue
            key = (i, nb)
            if key in dead:
                continue
            res = dfs(nb, i + 1)
            if res is not None:
                return [m] + res
            dead.add(key)
        return None

    res = dfs(0, 0)
    out = {
        "order": order,
        "mirror_order": mirror(order),
        "tsd_rows": f"{row + 1}-{row + 2}",
        "found": int(res is not None),
        "t_rotation": "",
        "t_kick": "",
        "field": "",
        "nodes": nodes,
    }
    if res is not None:
        masks, t_mask, t_rot, t_kick = res[:6], res[6], res[7], res[8]
        out["t_rotation"] = "0R2L"[t_rot]
        out["t_kick"] = t_kick + 1
        out["field"] = field_string(list(zip(order, masks)) + [("T", t_mask)])
    return out


def mirror(order: str) -> str:
    return order.translate(str.maketrans("SZLJ", "ZSJL"))


def canonical_orders() -> list[str]:
    """左右反転で同一視した 360 通りのミノ順 (L が J より先のもの)。"""
    orders = ["".join(p) for p in permutations("IJLSZO")]
    return [o for o in orders if o.index("L") < o.index("J")]


def main() -> None:
    tasks = [(o, row) for o in canonical_orders() for row in (0, 1)]
    start = time.time()
    results = []
    with Pool() as pool:
        for i, res in enumerate(pool.imap(solve, tasks), 1):
            results.append(res)
            print(f"\r{i}/{len(tasks)} ({time.time() - start:.0f}s)", end="", file=sys.stderr)
    print(file=sys.stderr)

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    orders = canonical_orders()
    found = {(r["order"], r["tsd_rows"]) for r in results if r["found"]}
    n12 = sum((o, "1-2") in found for o in orders)
    n23 = sum((o, "2-3") in found for o in orders)
    ng = [o for o in orders if (o, "1-2") not in found and (o, "2-3") not in found]
    print(f"1-2 段目で TSD 可能: {n12}/{len(orders)}")
    print(f"2-3 段目で TSD 可能: {n23}/{len(orders)}")
    print(f"どちらでも不可能: {len(ng)} 通り {' '.join(ng)}")
    print(f"wrote {CSV_PATH.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
