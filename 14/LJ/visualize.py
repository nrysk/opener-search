"""14/LJ/patterns.csv (search.py の列挙結果) を 14/LJ/patterns.html として可視化する。

開始形状 (12/LJ の 100-3-019 のライン消去後) から 3巡目の終わりに TSD を打てるシルエットを並べ、
各シルエットをどのミノ順で組めるかと、2 つのシルエットの組の網羅数を表示する (06 と同じ画面)。

タブは 2 つ。「I→Z」は I が Z より先に来る 360 通りだけを数える (Z が I より先なら理想形の TST を組めるので、
その裏で TSD を確実に組める形を探すため)。「すべて」は 720 通りすべてを数える。
HTML の本体は lib/followup_view.py。patterns.html はそのままブラウザで開ける。
"""

from __future__ import annotations

from search import CSV_PATH, HERE, MAX_HEIGHT, STARTS

from lib.followup import load_patterns
from lib.followup_view import group, write_html

HTML_PATH = HERE / "patterns.html"
TITLE = "TSS → TSD 後の 3巡目 TSD"
LEAD = f"""開幕 TSS (10 の TSS-2-100) → 2巡目 TSD (12/LJ の 100-3-019、3-4 段目) のあとに残る形から、
3巡目の 6 ミノを来た順にホールドなしで置き、最後の T で TSD を打てる形をすべて列挙したものです。
3巡目の途中で来る T はホールドしておく想定です。TSD で消す段は 2-3 段目、2・4 段目 (3 段目は残す)、4-5 段目、5-6 段目です (「TSD の段: 2,4 段目」が 2・4 段目)。
T を置く前の高さは {MAX_HEIGHT} 段以下に限り、
T より前にラインが消える置き方は含みません。
タブ「I→Z」は、I が Z より先に来る 360 通りのミノ順だけを数えます (Z が I より先なら理想形の TST を組めるため)。
シルエット (T を置く前に埋まっているマスの形) ごとに、それを組めるミノ順を「ミノ順マップ」で示します。"""


BEFORE = ("I", "Z")  # タブ「I→Z」: I が Z より先に来るミノ順だけを数える


def restricted(p: dict, a: str, b: str) -> dict | None:
    """パターン p のミノ順を、a が b より先に来るものだけにしたもの (1 つもなければ None)。"""
    tilings = [(f, {o: s for o, s in orders.items() if o.index(a) < o.index(b)}) for f, orders in p["tilings"]]
    tilings = sorted((t for t in tilings if t[1]), key=lambda t: -len(t[1]))
    return {**p, "tilings": tilings} if tilings else None


def main() -> None:
    patterns = load_patterns(CSV_PATH)
    a, b = BEFORE
    data = {}
    for sid, field in STARTS.items():
        mine = [p for p in patterns.values() if p["start"] == sid]
        name = f"{sid} {a}→{b}"
        data[name] = group([name], [field], [[q] for p in mine if (q := restricted(p, a, b))], before=BEFORE)
        data[f"{sid} すべて"] = group([f"{sid} すべて"], [field], [[p] for p in mine])
    write_html(HTML_PATH, data, TITLE, LEAD, MAX_HEIGHT, "tsd-14-lj-patterns-pinned", "TSD")


if __name__ == "__main__":
    main()
