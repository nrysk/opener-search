"""10/patterns.csv (search.py の列挙結果) を 10/patterns.html として可視化する。

始動ミノ (1 番目に来るミノ) ごとのタブに、開幕 TSS を打てるシルエットを並べ、各シルエットを
そのミノで始まる 120 通りのミノ順のうち何通りで組めるかと、2 つのシルエットの組の網羅数を表示する。
Z・J 始動は S・L 始動の左右反転なのでタブを作らない。
HTML の本体は lib/followup_view.py (05, 06 と共有)。patterns.html はそのままブラウザで開ける。
"""

from __future__ import annotations

from search import CSV_PATH, HERE, MAX_HEIGHT, STARTS

from lib.followup import load_patterns
from lib.followup_view import group, write_html

HTML_PATH = HERE / "patterns.html"
FIRSTS = "IOSL"  # タブにする始動ミノ
TITLE = "開幕 TSS のシルエットとミノ順"
LEAD = f"""T が最初に来てホールドに入る前提で、残りの 6 ミノ (I J L S Z O) を来た順にホールドなしで空の盤面に置き、
最後にホールドの T で TSS (T-Spin Single。Mini は除く) を打てる形をすべて列挙したものです。
T を置く前の高さは {MAX_HEIGHT} 段以下に限り、T より前にラインが消える置き方は含みません。
タブで始動ミノ (T の次に来る 1 番目のミノ) を選ぶと、そのミノで始まる 120 通りのミノ順のうち、
各シルエット (T を置く前に埋まっているマスの形) を何通りで組めるかを「ミノ順マップ」で示します。
Z・J 始動は S・L 始動の左右反転です。「TSS の段」で、何段目を消す TSS かを絞り込めます。"""


def starting_with(p: dict, first: str) -> dict | None:
    """パターン p のミノ順を first で始まるものだけにしたもの (1 つもなければ None)。"""
    tilings = [(f, {o: s for o, s in orders.items() if o[0] == first}) for f, orders in p["tilings"]]
    tilings = sorted((t for t in tilings if t[1]), key=lambda t: -len(t[1]))
    return {**p, "tilings": tilings} if tilings else None


def main() -> None:
    patterns = load_patterns(CSV_PATH)
    ((sid, field),) = STARTS.items()
    data = {}
    for first in FIRSTS:
        members = [[q] for p in patterns.values() if p["start"] == sid and (q := starting_with(p, first))]
        data[f"{first} 始動"] = group([f"{first} 始動"], [field], members, first)
    write_html(HTML_PATH, data, TITLE, LEAD, MAX_HEIGHT, "tss-opener-patterns-pinned", "TSS", order_filter=False)


if __name__ == "__main__":
    main()
