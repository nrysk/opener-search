"""2巡目の TSD 後に残る形から、3巡目の終わりに TSD を打てる形を全列挙する (SRS)。

対象は、05 で採用したテンプレ 3 の 4 形状。1巡目の終わり方 (3A / 3B) それぞれについて、
2巡目に組む形を 2 つ選んであり (2 つで全ミノ順を網羅できる組)、その TSD 後に残る形から始める。
そこに 3巡目の 6 ミノ (I J L S Z O) を来た順にホールドなしで置き、最後に来た T で TSD を打つ。

- 探索の本体は lib/followup.py (05 と共有)。前提・出力形式もそちらを参照
- T を置く前の高さは MAX_HEIGHT 段以下に制限する (制限なしでは組み合わせ爆発する)

出力: 06/patterns.csv (1 行 = 開始形状 x シルエット x ミノ割り。可視化は 06/visualize.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.followup import run  # noqa: E402

CSV_PATH = HERE / "patterns.csv"
MAX_HEIGHT = 6  # T を置く前の高さの上限
PROCESSES = 6  # 1 プロセスのメモリ使用量が大きいので、コア数より少なくする

# 2巡目の TSD 後に残る形。名前は「1巡目の終わり方 - 2巡目に組んだ形の番号」で、
# SOURCES は元になった 05 のシルエット (05/patterns.csv の silhouette 列)
STARTS = {
    "3A-1": "OO__S___J_/OO__SSI_J_/I_S_L_I_JJ",
    "3A-2": "___SSZ___I/__SSZZ__JI/ILS_L___JJ",
    "3B-1": "OO__S_____/OO__SSI__L/I_S_L_IOOJ",
    "3B-2": "___SSZ____/__SSZZ__JI/ILS_L__OOI",
}
SOURCES = {"3A-1": "3A-2-080", "3A-2": "3A-2-175", "3B-1": "3B-2-011", "3B-2": "3B-2-026"}

if __name__ == "__main__":
    run(STARTS, MAX_HEIGHT, CSV_PATH, PROCESSES)
