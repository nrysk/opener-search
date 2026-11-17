"""06/patterns.csv (search.py の列挙結果) を 06/patterns.html として可視化する。

開始形状 (2巡目の残り) ごとに、3巡目の終わりに TSD を打てるシルエットを並べ、
各シルエットをどのミノ順で組めるかと、2 つのシルエットの組の網羅数を表示する。
HTML の本体は lib/followup_view.py (05 と共有)。patterns.html はそのままブラウザで開ける。
"""

from __future__ import annotations

from search import CSV_PATH, HERE, MAX_HEIGHT, STARTS

from lib.followup import load_patterns
from lib.followup_view import group, write_html

HTML_PATH = HERE / "patterns.html"
TITLE = "3巡目 TSD のシルエットとミノ順"
LEAD = f"""テンプレ 3 で 2巡目の TSD を打ったあとに残る 4 つの形 (1巡目の終わり方 3A / 3B × 2巡目に組んだ形 1 / 2) から、
3巡目の 6 ミノを来た順にホールドなしで置き、最後に来た T で TSD を打てる形をすべて列挙したものです。
T を置く前の高さは {MAX_HEIGHT} 段以下に限り、T より前にラインが消える置き方は含みません。
シルエット (T を置く前に埋まっているマスの形) ごとに、それを組めるミノ順を「ミノ順マップ」で示します。"""


def main() -> None:
    patterns = load_patterns(CSV_PATH)
    data = {
        sid: group([sid], [field], [[p] for p in patterns.values() if p["start"] == sid])
        for sid, field in STARTS.items()
    }
    write_html(HTML_PATH, data, TITLE, LEAD, MAX_HEIGHT, "tsd3-patterns-pinned")


if __name__ == "__main__":
    main()
