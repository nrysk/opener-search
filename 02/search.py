"""テンプレでカバーできないミノ順について、TSD を打てる配置パターンを全列挙する (SRS)。

対象は、01 で「ソフトドロップなしでは開幕 TSD もアルバトロス TSD も組めなかった」ミノ順
(開幕 TSD の左右反転形は使わない条件) のうち、S 開始のものと J 開始のもの。
00 と同じく「T が最初に来てホールドに入り、残り 6 ミノを来た順にホールドなしで置き、
最後に T で TSD を打つ」状況で、1-2 段目または 2-3 段目で TSD を打てる最終形をすべて求める。

- 配置パターンは「どのミノがどのマスを占めるか」まで含めて区別する
- ソフトドロップが必要な置き方も含めて列挙し、ミノ順ごとの回数を記録する
  (回数の定義は 01 と同じ。最後の T は含めない)

入力: 01/templates.csv
出力: 02/patterns.csv (1 行 = ミノ順 x 配置パターン。可視化は 02/visualize.py)
"""

from __future__ import annotations

import csv
import sys
import time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.srs import PIECES, field_string, find_tsd, row_mask  # noqa: E402

TEMPLATES_CSV = HERE.parent / "01" / "templates.csv"
CSV_PATH = HERE / "patterns.csv"
STARTS = "SJ"  # 調べるミノ順の 1 番目のミノ
MAX_OUTSIDE = 8  # 消去する 2 段の外に置けるブロック数の上限 (24 - 16)


def uncovered_orders(allow_soft_drop: bool = False) -> list[str]:
    """01 で、どのテンプレ (反転形の開幕 TSD を除く) も組めなかったミノ順。

    既定ではソフトドロップなしで組めなかったもの。allow_soft_drop=True なら、
    ソフトドロップを使っても組めなかったもの (前者の部分集合) だけを返す。
    """
    with TEMPLATES_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    covered = {
        r["order"]
        for r in rows
        if r["buildable"] == "1"
        and (allow_soft_drop or r["soft_drops"] == "0")
        and not (r["family"] == "kaimaku" and r["mirrored"] == "1")
    }
    return sorted({r["order"] for r in rows} - covered)


def solve(task: tuple[str, int]) -> list[dict]:
    """ミノ順 order で、row 段目と row+1 段目 (0 始まり) を T で消す形をすべて求める。"""
    order, row = task
    target = row_mask(row) | row_mask(row + 1)
    targets = (row_mask(row), row_mask(row + 1))
    pieces = [PIECES[c] for c in order]
    # (手数, 盤面) -> そこから先の置き方の一覧。各要素は ((マスク, ハードドロップ可か), ..., T の情報)
    memo: dict[tuple[int, int], list[tuple]] = {}

    def dfs(board: int, i: int) -> list[tuple]:
        key = (i, board)
        if key in memo:
            return memo[key]
        res: list[tuple] = []
        if i == len(pieces):
            hit = find_tsd(board, target)
            if hit is not None:
                res.append((hit,))
        else:
            for m, hard in pieces[i].placements_with_drop(board).items():
                nb = board | m
                # 消す 2 段の外に置けるのは 8 ブロックまで (これで他の段のライン消去も起きない)
                if (nb & ~target).bit_count() > MAX_OUTSIDE:
                    continue
                # 消す段が T より前に埋まってはいけない
                if nb & targets[0] == targets[0] or nb & targets[1] == targets[1]:
                    continue
                for rest in dfs(nb, i + 1):
                    res.append(((m, hard),) + rest)
        memo[key] = res
        return res

    out = []
    for sol in dfs(0, 0):
        placed, (t_mask, t_rot, _) = sol[:-1], sol[-1]
        soft = "".join(c for c, (_, hard) in zip(order, placed) if not hard)
        out.append(
            {
                "start": order[0],
                "order": order,
                "tsd_rows": f"{row + 1}-{row + 2}",
                "soft_drops": len(soft),
                "soft_drop_pieces": soft,
                "t_rotation": "0R2L"[t_rot],
                "field": field_string([(c, m) for c, (m, _) in zip(order, placed)] + [("T", t_mask)]),
            }
        )
    return out


def main() -> None:
    orders = [o for o in uncovered_orders() if o[0] in STARTS]
    tasks = [(o, row) for o in orders for row in (0, 1)]
    start = time.time()
    results = []
    with Pool() as pool:
        for i, res in enumerate(pool.imap(solve, tasks), 1):
            results.extend(res)
            print(f"\r{i}/{len(tasks)} ({time.time() - start:.0f}s)", end="", file=sys.stderr)
    print(file=sys.stderr)

    fields = ["start", "order", "tsd_rows", "soft_drops", "soft_drop_pieces", "t_rotation", "field"]
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    for c in STARTS:
        mine = [o for o in orders if o[0] == c]
        rows = [r for r in results if r["start"] == c]
        hard = [r for r in rows if r["soft_drops"] == 0]
        print(
            f"{c} 開始: 対象 {len(mine)} 通り, 配置パターン {len({r['field'] for r in rows})} 種類 "
            f"(ソフトドロップなしで作れるもの {len({r['field'] for r in hard})} 種類), "
            f"パターンのあるミノ順 {len({r['order'] for r in rows})} 通り "
            f"(ソフトドロップなし {len({r['order'] for r in hard})} 通り)"
        )
    print(f"wrote {CSV_PATH.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
