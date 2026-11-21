"""12/LJ/patterns.csv (search.py の列挙結果) を 12/LJ/patterns.html として可視化する。

開始形状 (10 の TSS-2-xxxx のライン消去後) ごとのタブに、2巡目の終わりに TSD を打てる
シルエットを並べ、各シルエットをどのミノ順で組めるかと、2 つのシルエットの組の網羅数を表示する (06 と同じ画面)。
HTML の本体は lib/followup_view.py。patterns.html はそのままブラウザで開ける。
"""

from __future__ import annotations

from search import CSV_PATH, HERE, MAX_HEIGHT, STARTS

from lib.followup import load_patterns
from lib.followup_view import group, write_html

HTML_PATH = HERE / "patterns.html"
TITLE = "開幕 TSS (L 始動) 後の 2巡目 TSD"
LEAD = f"""10 の開幕 TSS の形 (L 始動・2 段目) のいくつかで TSS を打ったあとに残る形 (タブ) から、
2巡目の 6 ミノを来た順にホールドなしで置き、最後の T で TSD を打てる形をすべて列挙したものです。
2巡目の途中で来る T はホールドしておく想定です。TSD で消す段は 2-3 段目か 3-4 段目です。
T を置く前の高さは {MAX_HEIGHT} 段以下に限り (I ミノだけは一部がその中にあれば上にはみ出してよい)、
T より前にラインが消える置き方は含みません。
シルエット (T を置く前に埋まっているマスの形) ごとに、それを組めるミノ順を「ミノ順マップ」で示します。"""


def main() -> None:
    patterns = load_patterns(CSV_PATH)
    data = {
        f"TSS-2-{sid}": group([f"TSS-2-{sid}"], [field], [[p] for p in patterns.values() if p["start"] == sid])
        for sid, field in STARTS.items()
    }
    write_html(HTML_PATH, data, TITLE, LEAD, MAX_HEIGHT, "tsd-12-lj-patterns-pinned", "TSD")


if __name__ == "__main__":
    main()
