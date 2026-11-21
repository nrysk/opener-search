"""12/LJ の 3巡目の入り (TSS-2-100 → 2巡目 TSD のライン消去後の形) から、3巡目に TSD を打てる形を全列挙する (SRS)。

開始形状は、12/LJ の 100-3-019 (TSS-2-100 で 3-4 段目 TSD) を打ったあとに残る形
(12/LJ/patterns.csv の 1 つ目のミノ割りのライン消去後)。

3巡目の 6 ミノ (I J L S Z O) を来た順にホールドなしで置き、最後の T で TSD を打つ
(3巡目の途中で来る T はホールドしておく想定)。720 通りのミノ順と TSD で消す段の組み合わせを調べる。

- 探索の本体は lib/followup.py (05, 06, 10-13 と共有)。前提・出力形式もそちらを参照
- TSD で消す段は 2-3 段目、2・4 段目 (3 段目は残す。縦向きの T で上下の段だけを消す)、4-5 段目、5-6 段目
  (1 段目は触れられないため 1-2 段目は調べない)
- T を置く前の高さは MAX_HEIGHT 段以下。8 段あれば I の縦置きも入るので、はみ出しは許さない
- T より前にラインが消える置き方は含めない

出力: 14/LJ/patterns.csv (1 行 = 開始形状 x シルエット x ミノ割り。可視化は 14/LJ/visualize.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from lib.followup import run  # noqa: E402

CSV_PATH = HERE / "patterns.csv"
MAX_HEIGHT = 8  # T を置く前の高さの上限
OVERHANG = ""  # 高さの上限からはみ出してよいミノ (なし)
LINES = 2  # TSD
SPIN_ROWS = [2, (2, 4), 4, 5]  # TSD で消す段 (1 始まり)。整数は下の段 (2 → 2-3 段目)、(2, 4) は 2・4 段目
PROCESSES = 2  # 2-3 段目の探索は 1 プロセス 6GB 程度使う

STARTS = {
    "100-3-019": "__ILOO____/S_ILOO____/I_ZJTT_ZJJ/IZLLLSS_OO",
}

if __name__ == "__main__":
    run(STARTS, MAX_HEIGHT, CSV_PATH, PROCESSES, LINES, SPIN_ROWS, OVERHANG)
