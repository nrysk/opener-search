"""05/patterns.csv (search.py の列挙結果) を 05/patterns.html として可視化する。

開始形状ごとのタブに加えて、テンプレごとの「A・B 共通」のタブ (pairs.py と同じ定義) を作り、
各タブで「2 つのシルエットの組」の網羅数を表示する (ブラウザ側で現在の条件に合わせて計算する)。

開始形状 (1巡目の残り) ごとに、2巡目の終わりに TSD を打てるシルエットを並べ、
各シルエットをどのミノ順で組めるかを 720 マスの「ミノ順マップ」で表示する。
HTML の本体は lib/followup_view.py (06 と共有)。patterns.html はデータを埋め込んだ単一ファイルなので、そのままブラウザで開ける。
"""

from __future__ import annotations

from pairs import common_silhouettes
from search import CSV_PATH, HERE, MAX_HEIGHT, STARTS

from lib.followup import load_patterns
from lib.followup_view import group, write_html

HTML_PATH = HERE / "patterns.html"
TITLE = "2巡目 TSD のシルエットとミノ順"
LEAD = f"""1巡目の TSD 後に残る形 (12 テンプレ × 2 通り) から、2巡目の 6 ミノを来た順にホールドなしで置き、
最後に来た T で TSD を打てる形をすべて列挙したものです。T を置く前の高さは {MAX_HEIGHT} 段以下に限り、
T より前にラインが消える置き方は含みません。シルエット (T を置く前に埋まっているマスの形) ごとに、
それを組めるミノ順を「ミノ順マップ」で示します。
「共通」のタブは、同じテンプレの 2 つの開始形状 (A, B) のどちらからでも同じシルエットになるものだけを集めたもので、
ミノ順は A の 720 通りと B の 720 通りを合わせた 1440 通りで数えます。"""


def main() -> None:
    patterns = load_patterns(CSV_PATH)
    data = {}
    for template, items in common_silhouettes(patterns).items():
        for sid in (template + "A", template + "B"):
            data[sid] = group([sid], [STARTS[sid]], [[p] for p in patterns.values() if p["start"] == sid])
        ab = [template + "A", template + "B"]
        data[template + "AB"] = group(ab, [STARTS[s] for s in ab], [[a, b] for a, b in items])
    write_html(HTML_PATH, data, TITLE, LEAD, MAX_HEIGHT, "tsd2-patterns-pinned")


if __name__ == "__main__":
    main()
