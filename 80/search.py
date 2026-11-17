"""アルバトロス TSD の 1巡目の TSD 後に残る形から、2巡目の終わりに TSD を打てる形を全列挙する (SRS)。

アルバトロス TSD (data/templates.csv の s2-05-04) で TSD を打つと 2 段消えて 8 マス残る。
そこに 2巡目の 6 ミノ (I J L S Z O) を来た順にホールドなしで置き、最後に来た T で TSD を打つ。
720 通りのミノ順すべてについて、TSD を打てる最終形を求める。

- 探索の本体は lib/followup.py (05, 06 と共有)。前提・出力形式もそちらを参照
- T を置く前の高さは MAX_HEIGHT 段以下に制限する (制限なしでは組み合わせ爆発する)
- 左右反転形のアルバトロス TSD は、結果を左右反転 (S<->Z, L<->J) すればよいので調べない

出力: 80/patterns.csv (1 行 = 開始形状 x シルエット x ミノ割り。可視化は 80/visualize.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lib.followup import run  # noqa: E402

CSV_PATH = HERE / "patterns.csv"
MAX_HEIGHT = 5  # T を置く前の高さの上限
PROCESSES = 4

# アルバトロス TSD (上の段から)。T は TSD を打ったあとの位置
TEMPLATE = "I___ZZ____/ISTTTZZJJJ/ISSTOOLLLJ/I_S_OOL___"
# TSD で消える段 (すべて埋まっている段) を除いた、1巡目の残り
STARTS = {"albatross": "/".join(line for line in TEMPLATE.split("/") if "_" in line)}

if __name__ == "__main__":
    run(STARTS, MAX_HEIGHT, CSV_PATH, PROCESSES)
