"""開幕 TSS (10 の L 始動・2 段目の形) のライン消去後の形から、2巡目に TSD を打てる形を全列挙する (SRS)。

開始形状は、10 の形を TSS で 1 段消したあとの形 (3045 以外は 10/patterns.csv のミノ割りそのまま)。
- 4743: TSS-2-4743 (11/LJ の B-1)
- 4403: TSS-2-4403 (11/LJ の I-1)
- 4486: TSS-2-4486 (11/LJ の M-1)
- 4827: TSS-2-4827 (11/LJ の O-1)
- 3045: TSS-2-3045 で T を下向きに入れた形 (消去後に T が横 3 マスで残る)
- 7024: TSS-2-7024、8183: TSS-2-8183、12651: TSS-2-12651、100: TSS-2-100 (11/LJ の E-1)
- 2845: TSS-2-2845 (11/LJ の F-1)
- 2845-2 / 100-2: TSS-2-2845 / TSS-2-100 で T を下向きに入れた形 (11/LJ の F-2 / E-2)

2巡目の 6 ミノ (I J L S Z O) を来た順にホールドなしで置き、最後の T で TSD を打つ
(2巡目の途中で来る T はホールドしておく想定)。720 通りのミノ順と TSD で消す段の組み合わせを調べる。

- 探索の本体は lib/followup.py (05, 06, 10, 11 と共有)。前提・出力形式もそちらを参照
- TSD で消す段は 2-3 段目か 3-4 段目 (1-2 段目は考えない)
- T を置く前の高さは MAX_HEIGHT 段以下。ただし I ミノだけは、1 マス以上がその中にあれば上にはみ出してよい
  (I の縦置きを考えるため)
- T より前にラインが消える置き方は含めない

出力: 12/LJ/patterns.csv (1 行 = 開始形状 x シルエット x ミノ割り。可視化は 12/LJ/visualize.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from lib.followup import run  # noqa: E402

CSV_PATH = HERE / "patterns.csv"
MAX_HEIGHT = 6  # T を置く前の高さの上限 (I ミノだけははみ出してよい)
OVERHANG = "I"  # 高さの上限からはみ出してよいミノ (一部が上限内にあればよい)
LINES = 2  # TSD
SPIN_ROWS = [2, 3]  # TSD で消す段の下の段 (1 始まり)。2-3 段目と 3-4 段目
PROCESSES = 4

STARTS = {
    "4743": "S_________/SS_______I/LS__J_Z__I/LLTJJZ_OOI",
    "4403": "I_________/IJJT______/IJTT___Z__/LLLSS_Z_OO",
    "4486": "S_________/SS___I____/LS__JI_Z__/LLTJJIZ_OO",
    "4827": "_S________/ISS_______/ILS__J_Z__/ILLTJJZ_OO",
    "3045": "____JJ___I/___ZJTTT_I/OOZLLLSS_I",
    "7024": "__S_______/__SS_____I/__LS__J_ZI/OOLLTJJZ_I",
    "8183": "___S______/__ISS_____/__ILS__J_Z/OOILLTJJZ_",
    "12651": "_____S____/____ISS___/_Z__ILS__J/Z_OOILLTJJ",
    "100": "I__JJT____/I_ZJTT____/IZLLLSS_OO",
    "100-2": "I__JJ_____/I_ZJTTT___/IZLLLSS_OO",
    "2845": "__JJT____I/_ZJTT____I/ZLLLSS_OOI",
    "2845-2": "__JJ_____I/_ZJTTT___I/ZLLLSS_OOI",
}

if __name__ == "__main__":
    run(STARTS, MAX_HEIGHT, CSV_PATH, PROCESSES, LINES, SPIN_ROWS, OVERHANG)
