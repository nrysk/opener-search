"""1巡目の TSD 後に残る形から、2巡目の終わりに TSD を打てる形を全列挙する (SRS)。

対象は 12 個のテンプレの「1巡目が終わったときの形」(テンプレごとに 2 通り、計 24 形状)。
そこに 2巡目の 6 ミノ (I J L S Z O) を来た順にホールドなしで置き、最後に来た T で
TSD を打つ。720 通りのミノ順すべてについて、TSD を打てる最終形を求める。

- 探索の本体は lib/followup.py (06 と共有)
- T を置く前の高さは MAX_HEIGHT 段以下に制限する (制限なしでは組み合わせ爆発する)
- T を置く前にラインが消える置き方は扱わない
- TSD で消す段は 1-2 段目から 4-5 段目まですべて調べる
- 「シルエット」は T を置く前に埋まっているマスの集合。同じシルエットでもミノの
  割り当て (ミノ割り) が複数ありうるので、ミノ割りごとに組めるミノ順を記録する
- ソフトドロップが必要な置き方も含める (回数の定義は 01 と同じ。最後の T は含めない)

出力: 05/patterns.csv (1 行 = 開始形状 x シルエット x ミノ割り。可視化は 05/visualize.py)
  - field: 1巡目の残りは小文字、2巡目のミノと T は大文字
  - orders: 組めるミノ順を空白区切りで並べたもの。ソフトドロップが必要なら
    「ミノ順:対象ミノ」と書く
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.followup import run  # noqa: E402

CSV_PATH = HERE / "patterns.csv"
MAX_HEIGHT = 5  # T を置く前の高さの上限
PROCESSES = 8  # 1 プロセスが 1 GB 近く使うので、コア数より少なくする

# 1巡目が終わったときの形 (画像から読み取ったもの)。番号がテンプレ、A/B がその 2 通り
STARTS = {
    "1A": "___ZZ____I/_S_L__OO_I",
    "1B": "___ZZ____I/_S_L___JJI",
    "2A": "___ZZ_I___/_S_L__I_JJ",
    "2B": "___ZZ_I___/_S_L__IOO_",
    "3A": "I___ZZ____/I_S_L___JJ",
    "3B": "I___ZZ____/I_S_L__OO_",
    "4A": "___ZZ____I/_S___J_OOI",
    "4B": "___ZZ____I/_S___JLL_I",
    "5A": "___ZZ_I___/_S___JILL_",
    "5B": "___ZZ_I___/_S___JI_OO",
    "6A": "I___ZZ____/I_S___JLL_",
    "6B": "I___ZZ____/I_S___J_OO",
    "7A": "I______ZZ_/IOO__S_L__",
    "7B": "I______ZZ_/I_JJ_S_L__",
    "8A": "___I___ZZ_/OO_I_S_L__",
    "8B": "___I___ZZ_/_JJI_S_L__",
    "9A": "______ZZ_I/OO__S_L__I",
    "9B": "______ZZ_I/_JJ_S_L__I",
    "10A": "I______ZZ_/ILL__S___J",
    "10B": "I______ZZ_/I_OO_S___J",
    "11A": "___I___ZZ_/LL_I_S___J",
    "11B": "___I___ZZ_/_OOI_S___J",
    "12A": "______ZZ_I/LL__S___JI",
    "12B": "______ZZ_I/_OO_S___JI",
}


if __name__ == "__main__":
    run(STARTS, MAX_HEIGHT, CSV_PATH, PROCESSES)
