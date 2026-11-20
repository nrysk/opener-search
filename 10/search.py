"""開幕 TSS で打てる形を全列挙する (SRS)。

T が最初に来てホールドに入る前提で、残りの 6 ミノ (I J L S Z O) を来た順にホールドなしで
空の盤面に置き、最後にホールドの T で TSS (T-Spin Single。Mini は除く) を打つ。
720 通りのミノ順と TSS で消す段の組み合わせについて、組める形をすべて求める。

- 探索の本体は lib/followup.py (05, 06 と共有。lines=1 で TSS)。前提・出力形式もそちらを参照
- T を置く前の高さは MAX_HEIGHT 段以下に制限する。開幕 TSS は 1-3 段目でしか行わないので、その 3 通りを調べる
- T より前にラインが消える置き方、TSS で消す段以外もそろってしまう置き方は含めない

出力: 10/patterns.csv (1 行 = シルエット x ミノ割り。可視化は 10/visualize.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.followup import run  # noqa: E402

CSV_PATH = HERE / "patterns.csv"
MAX_HEIGHT = 5  # T を置く前の高さの上限
SPIN_ROWS = [1, 2, 3]  # TSS で消す段 (1 始まり)
PROCESSES = 1  # 高さ 5 では 1 プロセスで 6GB 前後使うので、1 段ずつ順に調べる
LINES = 1  # TSS

# 開始形状は空の盤面だけ (CSV の start 列とシルエット id の頭に使う)
STARTS = {"TSS": "__________"}

if __name__ == "__main__":
    run(STARTS, MAX_HEIGHT, CSV_PATH, PROCESSES, LINES, SPIN_ROWS)
