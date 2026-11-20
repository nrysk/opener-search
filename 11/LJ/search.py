"""開幕 TSS (10 の L 始動・2 段目の形) のライン消去後の形から、2巡目に TST を打てる形を全列挙する (SRS)。

開始形状は、10 の形を TSS で 1 段消したあとの形。TSS を打つときの T の向きで消去後の形が変わるので、
1 つの形につき 2 通りあり、2 つで 1 組 (GROUPS) として扱う (どちらかで TST を打てればよい)。
- A: TSS-2-4422
  - A-1: 10/patterns.csv のミノ割りそのまま (T は左向きで、消去後に縦 2 + 横 1 の形で残る)
  - A-2: T を下向きに入れた形 (消去後に T が横 3 マスで残る)
- B: TSS-2-4743
  - B-1: 10/patterns.csv のミノ割りそのまま (T は下向きで、消去後に T が 1 マス残る)
  - B-2: T の残る 1 マスが 2 段目にある形
- C: TSS-2-4408
  - C-1: 10/patterns.csv のミノ割りそのまま (T は左向きで、消去後に縦 2 + 横 1 の形で残る)
  - C-2: T を下向きに入れた形 (消去後に T が横 3 マスで残る)
- D: TSS-2-594
  - D-1: 10/patterns.csv のミノ割りそのまま (T は左向きで、消去後に縦 2 + 横 1 の形で残る)
  - D-2: T を下向きに入れた形 (消去後に T が横 3 マスで残る)
- E: TSS-2-100、F: TSS-2-2845、G: TSS-2-109、H: TSS-2-2851
  - -1 は 10/patterns.csv のミノ割りそのまま (T は左向き)、-2 は T を下向きに入れた形
- I: TSS-2-4403、J: TSS-2-681、L: TSS-2-2858、P: TSS-2-6453、Q: TSS-2-6461、R: TSS-2-610、S: TSS-2-682 (-1 / -2 は E-H と同じ)
- K: TSS-2-12568、M: TSS-2-4486、N: TSS-2-4617、O: TSS-2-4827
  - K-1: 10/patterns.csv のミノ割りそのまま (T は下向きで、消去後に T が 1 マス残る)
  - K-2: T の残る 1 マスが 2 段目にある形

2巡目の 6 ミノ (I J L S Z O) を来た順にホールドなしで置き、最後の T で TST を打つ
(2巡目の途中で来る T はホールドしておく想定)。720 通りのミノ順と TST で消す段の組み合わせを調べる。

- 探索の本体は lib/followup.py (05, 06, 10 と共有。lines=3 で TST)。前提・出力形式もそちらを参照
- T を置く前の高さは MAX_HEIGHT 段以下に制限する (8 段あれば I の縦置きも入る)
- TST で消す段は 2-4 段目だけを調べる (1-3 段目を使う TST は考えない)
- T より前にラインが消える置き方は含めない

出力: 11/LJ/patterns.csv (1 行 = 開始形状 x シルエット x ミノ割り。可視化は 11/LJ/visualize.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from lib.followup import run  # noqa: E402

CSV_PATH = HERE / "patterns.csv"
MAX_HEIGHT = 8  # T を置く前の高さの上限 (C++ の探索は 8 段まで)
LINES = 3  # TST
SPIN_ROWS = [2]  # TST で消す段の一番下 (1 始まり)。2-4 段目だけ
PROCESSES = 4

STARTS = {
    "A-1": "I_________/IJJT______/IJTT__S__Z/LLL_OO_SZ_",
    "A-2": "I_________/IJJ_______/IJTTT_S__Z/LLL_OO_SZ_",
    "B-1": "S_________/SS_______I/LS__J_Z__I/LLTJJZ_OOI",
    "B-2": "S_________/SS_______I/LST_J_Z__I/LL_JJZ_OOI",
    "C-1": "I_________/IJJT______/IJTT_Z__S_/LLL_Z_OO_S",
    "C-2": "I_________/IJJ_______/IJTTTZ__S_/LLL_Z_OO_S",
    "D-1": "I____JJT__/I___ZJTT__/IOOZLLLSS_",
    "D-2": "I____JJ___/I___ZJTTT_/IOOZLLLSS_",
    "E-1": "I__JJT____/I_ZJTT____/IZLLLSS_OO",
    "E-2": "I__JJ_____/I_ZJTTT___/IZLLLSS_OO",
    "F-1": "__JJT____I/_ZJTT____I/ZLLLSS_OOI",
    "F-2": "__JJ_____I/_ZJTTT___I/ZLLLSS_OOI",
    "G-1": "I__JJT____/I_ZJTT__S_/IZLLL_OO_S",
    "G-2": "I__JJ_____/I_ZJTTT_S_/IZLLL_OO_S",
    "H-1": "__JJT____I/_ZJTT__S_I/ZLLL_OO_SI",
    "H-2": "__JJ_____I/_ZJTTT_S_I/ZLLL_OO_SI",
    "I-1": "I_________/IJJT______/IJTT___Z__/LLLSS_Z_OO",
    "I-2": "I_________/IJJ_______/IJTTT__Z__/LLLSS_Z_OO",
    "J-1": "__I__JJT__/__I_ZJTT__/OOIZLLLSS_",
    "J-2": "__I__JJ___/__I_ZJTTT_/OOIZLLLSS_",
    "K-1": "_____S____/I____SS___/I_Z__LS__J/IZ_OOLLTJJ",
    "K-2": "_____S____/I____SS___/I_Z__LST_J/IZ_OOLL_JJ",
    "L-1": "__JJT____I/OOJTT_ZS_I/_LLL_Z__SI",
    "L-2": "__JJ_____I/OOJTTTZS_I/_LLL_Z__SI",
    "M-1": "S_________/SS___I____/LS__JI_Z__/LLTJJIZ_OO",
    "M-2": "S_________/SS___I____/LST_JI_Z__/LL_JJIZ_OO",
    "N-1": "S_________/SS_____I__/LS__J_ZI__/LLTJJZ_IOO",
    "N-2": "S_________/SS_____I__/LST_J_ZI__/LL_JJZ_IOO",
    "O-1": "_S________/ISS_______/ILS__J_Z__/ILLTJJZ_OO",
    "O-2": "_S________/ISS_______/ILST_J_Z__/ILL_JJZ_OO",
    "P-1": "__I_______/__IJJT____/S_IJTT_Z__/_SLLL_Z_OO",
    "P-2": "__I_______/__IJJ_____/S_IJTTTZ__/_SLLL_Z_OO",
    "Q-1": "__I_______/__IJJT____/_ZIJTT__S_/Z_LLL_OO_S",
    "Q-2": "__I_______/__IJJ_____/_ZIJTTT_S_/Z_LLL_OO_S",
    "R-1": "I____JJT__/I_ZOOJTT__/IZ__LLLSS_",
    "R-2": "I____JJ___/I_ZOOJTTT_/IZ__LLLSS_",
    "S-1": "__I__JJT__/S_I_ZJTT__/_SIZLLL_OO",
    "S-2": "__I__JJ___/S_I_ZJTTT_/_SIZLLL_OO",
}
# 組 -> (10 のシルエット, 組に入る開始形状)
GROUPS = {
    "A": ("TSS-2-4422", ["A-1", "A-2"]),
    "B": ("TSS-2-4743", ["B-1", "B-2"]),
    "C": ("TSS-2-4408", ["C-1", "C-2"]),
    "D": ("TSS-2-594", ["D-1", "D-2"]),
    "E": ("TSS-2-100", ["E-1", "E-2"]),
    "F": ("TSS-2-2845", ["F-1", "F-2"]),
    "G": ("TSS-2-109", ["G-1", "G-2"]),
    "H": ("TSS-2-2851", ["H-1", "H-2"]),
    "I": ("TSS-2-4403", ["I-1", "I-2"]),
    "J": ("TSS-2-681", ["J-1", "J-2"]),
    "K": ("TSS-2-12568", ["K-1", "K-2"]),
    "L": ("TSS-2-2858", ["L-1", "L-2"]),
    "M": ("TSS-2-4486", ["M-1", "M-2"]),
    "N": ("TSS-2-4617", ["N-1", "N-2"]),
    "O": ("TSS-2-4827", ["O-1", "O-2"]),
    "P": ("TSS-2-6453", ["P-1", "P-2"]),
    "Q": ("TSS-2-6461", ["Q-1", "Q-2"]),
    "R": ("TSS-2-610", ["R-1", "R-2"]),
    "S": ("TSS-2-682", ["S-1", "S-2"]),
}

if __name__ == "__main__":
    run(STARTS, MAX_HEIGHT, CSV_PATH, PROCESSES, LINES, SPIN_ROWS)
