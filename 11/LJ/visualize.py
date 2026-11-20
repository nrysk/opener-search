"""11/LJ/patterns.csv (search.py の列挙結果) を 11/LJ/patterns.html として可視化する。

組 (10 の TSS-2-4422 / TSS-2-4743) ごとのタブに、その組の 2 つの開始形状 (TSS の T の向きで変わる
消去後の形) から TST を打てるシルエットをまとめて並べる。ミノ順は、2 つのどちらかで TST を打てれば
打てるものとして数える。各シルエットをどのミノ順で組めるかと、2 つのシルエットの組の網羅数を表示する。
HTML の本体は lib/followup_view.py。patterns.html はそのままブラウザで開ける。
"""

from __future__ import annotations

from search import CSV_PATH, GROUPS, HERE, MAX_HEIGHT, STARTS

from lib.followup import load_patterns
from lib.followup_view import group, write_html

HTML_PATH = HERE / "patterns.html"
TITLE = "開幕 TSS (L 始動) 後の 2巡目 TST"
LEAD = f"""10 の開幕 TSS の形 (L 始動・2 段目) で TSS を打ったあとに残る形から、2巡目の 6 ミノを来た順に
ホールドなしで置き、最後の T で TST を打てる形をすべて列挙したものです。2巡目の途中で来る T はホールドしておく想定です。
TSS を打つときの T の向きで消去後の形が 2 通りあるので (A-1 / A-2 など)、2 つを 1 組として、
どちらかで TST を打てればそのミノ順は打てるものとして数えます。
T を置く前の高さは {MAX_HEIGHT} 段以下に限り、T より前にラインが消える置き方は含みません。
TST で消す段は 2-4 段目だけを調べています (1-3 段目を使う TST は考えません)。
シルエット (T を置く前に埋まっているマスの形) ごとに、それを組めるミノ順を「ミノ順マップ」で示します。
カードの見出しの A-1 などは、そのシルエットの開始形状です。"""


def main() -> None:
    patterns = load_patterns(CSV_PATH)
    data = {}
    for gid, (source, sids) in GROUPS.items():
        members = [[{**p, "note": p["start"]}] for p in patterns.values() if p["start"] in sids]
        name = f"{gid} ({source})"
        data[name] = group([name], [STARTS[sids[0]]], members, starts=[(sid, STARTS[sid]) for sid in sids])
    write_html(HTML_PATH, data, TITLE, LEAD, MAX_HEIGHT, "tst-11-lj-patterns-pinned", "TST")


if __name__ == "__main__":
    main()
