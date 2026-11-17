"""80/patterns5.csv (search5.py の列挙結果) を 80/patterns5.html として可視化する。

アルバトロス TSD の 1巡目の残りに 5 ミノを置いた時点で TSD を打てるシルエット (途中消しあり) を並べ、
各シルエットをどのミノ順で組めるかと、2 つのシルエットの組の網羅数を表示する。
タブは「すべて / 途中消しなし / 途中消しあり」。HTML の本体は lib/followup_view.py。
"""

from __future__ import annotations

from pairs5 import GROUPS, load_patterns5
from search5 import HERE, MAX_HEIGHT, PLACED, START_FIELD

from lib.followup_view import group, write_html

HTML_PATH = HERE / "patterns5.html"
TITLE = "アルバトロス TSD の 2巡目 TSD (5 ミノ・途中消しあり)"
LEAD = f"""アルバトロス TSD で 1巡目の TSD を打ったあとに残る形から、2巡目のミノを来た順にホールドなしで {PLACED} つ置き、
その時点で T を入れて TSD を打てる形をすべて列挙したものです。ミノ順は 6 ミノの並びで表し、置くのは先頭の {PLACED} つだけです
(6 番目のミノは置きません)。T より前にラインが消える置き方も含み、盤面の高さは常に {MAX_HEIGHT} 段以下に限ります。
途中でラインが消えた形では、ミノの一部が欠けて表示されます。ソフトドロップの回数は、その形になる置き方のうち最少のものです。"""


def main() -> None:
    patterns = load_patterns5()
    data = {}
    for name, keep in GROUPS.items():
        # 同じシルエットが複数のタブに出るので、チェック状態を分けるために id にタブ名を付ける
        members = [[{**p, "id": f"{name}:{p['id']}"}] for p in patterns.values() if keep(p)]
        data[name] = group([name], [START_FIELD], members)
    write_html(HTML_PATH, data, TITLE, LEAD, MAX_HEIGHT, "albatross-tsd2-5-pinned")


if __name__ == "__main__":
    main()
