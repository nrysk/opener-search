"""13/LJ/patterns.csv (search.py の列挙結果) を 13/LJ/patterns.html として可視化する。

開始形状 (12/LJ の 4486-3-013 / 4486-3-037 のライン消去後) ごとのタブに、3巡目の終わりに TST を打てる
シルエットを並べ、各シルエットをどのミノ順で組めるかと、2 つのシルエットの組の網羅数を表示する (06 と同じ画面)。
HTML の本体は lib/followup_view.py。patterns.html はそのままブラウザで開ける。
"""

from __future__ import annotations

from search import CSV_PATH, HERE, MAX_HEIGHT, STARTS

from lib.followup import load_patterns
from lib.followup_view import group, write_html

HTML_PATH = HERE / "patterns.html"
TITLE = "TSS → TSD 後の 3巡目 TST"
LEAD = f"""開幕 TSS (10 の TSS-2-4486) → 2巡目 TSD (12/LJ の 4486-3-013 / 4486-3-037、3-4 段目) のあとに残る形から、
3巡目の 6 ミノを来た順にホールドなしで置き、最後の T で 2-4 段目の TST を打てる形をすべて列挙したものです。
3巡目の途中で来る T はホールドしておく想定です。
T を置く前の高さは {MAX_HEIGHT} 段以下に限り (どのミノも一部がその中にあれば上にはみ出してよい)、
T より前にラインが消える置き方は含みません。
シルエット (T を置く前に埋まっているマスの形) ごとに、それを組めるミノ順を「ミノ順マップ」で示します。"""


def main() -> None:
    patterns = load_patterns(CSV_PATH)
    data = {
        f"4486-3-{sid}": group([f"4486-3-{sid}"], [field], [[p] for p in patterns.values() if p["start"] == sid])
        for sid, field in STARTS.items()
    }
    write_html(HTML_PATH, data, TITLE, LEAD, MAX_HEIGHT, "tst-13-lj-patterns-pinned", "TST")


if __name__ == "__main__":
    main()
