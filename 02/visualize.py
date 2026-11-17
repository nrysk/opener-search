"""02/patterns.csv (search.py の列挙結果) を 02/patterns.html として可視化する。

同じ配置パターンを 1 つにまとめ、そのパターンを作れるミノ順の一覧を付けて表示する。
data/templates.csv にある形 (左右反転を含む) と一致する配置には、その名前を付ける。
patterns.html はデータを埋め込んだ単一ファイルなので、そのままブラウザで開ける。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from search import STARTS, uncovered_orders

HERE = Path(__file__).resolve().parent
TEMPLATES_CSV = HERE.parent / "data" / "templates.csv"
CSV_PATH = HERE / "patterns.csv"
HTML_PATH = HERE / "patterns.html"

HTML_TEMPLATE = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>テンプレ外ミノ順の TSD パターン</title>
<style>
  :root {
    --bg: #f6f7f9; --card: #fff; --line: #d9dde3; --text: #1c2128; --sub: #667080;
    --cell: #eef0f3; --clear: #ffe9a8; --ng: #c0392b; --ok: #1e8e4e; --accent: #7b3fc4; --chip: #eef0f3;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #14171c; --card: #1d2129; --line: #323843; --text: #e6e9ee; --sub: #98a2b3;
      --cell: #262b35; --clear: #5a4a12; --ng: #ff7b6b; --ok: #5fd08d; --accent: #c39bff; --chip: #262b35;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 24px 16px 48px; background: var(--bg); color: var(--text);
         font: 14px/1.5 system-ui, -apple-system, "Hiragino Sans", sans-serif; }
  main { max-width: 1280px; margin: 0 auto; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  p.lead { margin: 0 0 16px; color: var(--sub); max-width: 86ch; }
  .tabs { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 1px solid var(--line); }
  .tabs button { font: inherit; font-weight: 600; color: var(--sub); background: none; border: 0;
         border-bottom: 3px solid transparent; padding: 8px 16px; cursor: pointer; }
  .tabs button[aria-selected="true"] { color: var(--accent); border-bottom-color: var(--accent); }
  .stats { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
  .stat { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 8px 14px; }
  .stat b { display: block; font-size: 20px; font-variant-numeric: tabular-nums; }
  .stat span { color: var(--sub); font-size: 12px; }
  .controls { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; margin-bottom: 12px; }
  .controls button, .controls select, .more { font: inherit; color: inherit; background: var(--card);
         border: 1px solid var(--line); border-radius: 6px; padding: 5px 10px; }
  .controls button, .more { cursor: pointer; }
  #slots select, #slots b { font: 600 14px ui-monospace, Menlo, monospace; }
  #slots select { padding: 5px 6px; }
  #slots b { padding: 5px 10px; border: 1px solid var(--accent); border-radius: 6px; color: var(--accent); }
  .controls select.set { border-color: var(--accent); color: var(--accent); }
  .controls .label { color: var(--sub); }
  #slots { display: inline-flex; flex-wrap: wrap; gap: 4px; align-items: center; }
  #slots i { color: var(--sub); font-style: normal; }
  #count { color: var(--sub); }
  .none { margin: 0 0 16px; color: var(--sub); font-size: 13px; }
  .none[hidden] { display: none; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 10px; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 10px; }
  .card.pin { border-color: var(--accent); }
  .card h2 { font-size: 13px; font-weight: 600; margin: 0 0 8px; }
  .card h2 label { display: flex; align-items: center; gap: 8px; cursor: pointer; }
  .card h2 small { color: var(--sub); font-weight: 400; }
  .card h2 input { width: 16px; height: 16px; margin: 0; accent-color: var(--accent); cursor: pointer; }
  .card .name { margin: 0 0 6px; font-size: 13px; font-weight: 600; color: var(--accent); }
  .card .name small { color: var(--sub); font-weight: 400; }
  .controls label { display: inline-flex; align-items: center; gap: 6px; cursor: pointer; }
  .controls input[type=checkbox] { width: 16px; height: 16px; margin: 0; accent-color: var(--accent); }
  .card svg { display: block; width: 100%; height: auto; }
  .chips { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
  .chip { font: 12px ui-monospace, Menlo, monospace; letter-spacing: .06em; color: inherit; background: var(--chip);
         border: 1px solid transparent; border-radius: 4px; padding: 1px 6px; cursor: pointer; }
  .chip:hover { border-color: var(--accent); }
  .chip.hard { color: var(--ok); font-weight: 600; }
  .chip small { color: var(--sub); letter-spacing: 0; font-weight: 400; }
  .chip.ng { color: var(--ng); }
  #pinned { margin-bottom: 20px; padding: 12px; border: 1px dashed var(--accent); border-radius: 10px; }
  #pinned[hidden] { display: none; }
  #pinned header { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
  #pinned h3 { margin: 0; font-size: 14px; color: var(--accent); }
  #pinned button { font: inherit; color: inherit; background: var(--card); border: 1px solid var(--line);
         border-radius: 6px; padding: 3px 10px; cursor: pointer; }
  #coverage { margin-top: 12px; }
  #coverage p { margin: 0 0 8px; font-size: 13px; }
  #coverage p b { font-size: 16px; font-variant-numeric: tabular-nums; }
  #coverage p span { color: var(--sub); }
  .bar { height: 8px; margin-bottom: 10px; border-radius: 4px; background: var(--chip); overflow: hidden; }
  .bar div { height: 100%; background: var(--ok); }
  .cover { display: grid; grid-template-columns: repeat(auto-fill, minmax(72px, 1fr)); gap: 4px; }
  .cover .chip { text-align: center; padding: 3px 0; }
  .cover .chip.on { background: var(--ok); color: #fff; font-weight: 600; }
  @media (prefers-color-scheme: dark) { .cover .chip.on { color: #0c1a12; } }
  .cover .chip.off { color: var(--sub); }
  .legend { color: var(--sub); font-size: 12px; margin: 0 0 16px; }
  .more { display: block; margin: 16px auto 0; }
  .more[hidden] { display: none; }
</style>
</head>
<body>
<main>
<h1>テンプレ外ミノ順の TSD パターン</h1>
<p class="lead">開幕 TSD もアルバトロス TSD も組めないミノ順のうち、S 開始・J 開始のものについて、
TSD を打てる配置をすべて列挙し、同じ配置を 1 つにまとめたものです。各配置の下に、それを作れるミノ順を並べています。
前提は「T が最初に来てホールドに入り、残り 6 ミノを来た順にホールドなしで置く」です。
既知のテンプレと同じ形の配置には名前を表示します。</p>
<div class="tabs" role="tablist" id="tabs"></div>
<div class="stats" id="stats"></div>
<section id="pinned" hidden>
  <header><h3 id="pinned-title"></h3><button id="unpin-all">すべて外す</button></header>
  <div class="grid" id="pinned-grid"></div>
  <div id="coverage"></div>
</section>
<div class="controls">
  <span class="label">対象</span>
  <select id="target" aria-label="対象のミノ順">
    <option value="hard">ソフトドロップなしではテンプレを組めないミノ順</option>
    <option value="soft">ソフトドロップありでもテンプレを組めないミノ順</option>
  </select>
</div>
<div class="controls">
  <span class="label">条件</span>
  <select id="maxsoft" aria-label="ソフトドロップ回数の上限">
    <option value="6">ソフトドロップ: 制限なし</option>
    <option value="0" selected>ソフトドロップ: なし</option>
    <option value="1">ソフトドロップ: 1 回まで</option>
    <option value="2">ソフトドロップ: 2 回まで</option>
  </select>
  <select id="rows" aria-label="TSD を打つ段">
    <option value="">TSD の段: すべて</option>
    <option value="1-2">TSD の段: 1-2 段目</option>
    <option value="2-3">TSD の段: 2-3 段目</option>
  </select>
  <select id="sort" aria-label="並び順">
    <option value="orders">作れるミノ順が多い順</option>
    <option value="height">低い順</option>
  </select>
  <label><input type="checkbox" id="named"> 名前のある配置のみ</label>
</div>
<div class="controls">
  <span class="label">ミノ順</span>
  <span id="slots"></span>
  <button id="reset">リセット</button>
  <span id="count"></span>
</div>
<p class="legend">黄色の帯は TSD で消える段、紫は T ミノ。ミノ順の後ろの数字はソフトドロップ回数と対象ミノ
(緑はソフトドロップなし。最後の T は回数に含めません)。ミノ順をクリックすると、そのミノ順で絞り込みます。</p>
<p class="none" id="none" hidden></p>
<div class="grid" id="grid"></div>
<button class="more" id="more" hidden></button>
</main>
<script>
const DATA = __DATA__;
const COLORS = {I:"#35b8d6", O:"#e6b422", T:"#9b4fd0", S:"#4caf50", Z:"#e0483e", J:"#3a66d0", L:"#ef8a24"};
const C = 12, PAGE = 240;
const $ = id => document.getElementById(id);

// パターン: {f: 盤面, r: TSD の段, n: [名前, ...], o: [[ミノ順, ソフトドロップ対象ミノ], ...]}
// 同じ配置が S 開始と J 開始の両方に出ることがあるので、開始ミノごとの索引も持つ
const byField = new Map(), byStart = {};
for (const start of Object.keys(DATA)) {
  byStart[start] = new Map();
  for (const p of DATA[start].patterns) { byField.set(p.f, p); byStart[start].set(p.f, p); }
}

let start = Object.keys(DATA)[0], limit = PAGE;

function boardSvg(p) {
  const lines = p.f.split("/"), h = Math.max(5, lines.length);
  let s = `<svg viewBox="0 0 ${10 * C} ${h * C}" role="img" aria-label="配置パターン">`;
  for (let y = 0; y < h; y++) {
    const line = lines[lines.length - 1 - y];
    const fill = line && !line.includes("_") ? "var(--clear)" : "var(--cell)";
    for (let x = 0; x < 10; x++) {
      const ch = line ? line[x] : "_";
      s += `<rect x="${x * C + .5}" y="${(h - 1 - y) * C + .5}" width="${C - 1}" height="${C - 1}" rx="1.5" fill="${ch === "_" ? fill : COLORS[ch]}"/>`;
    }
  }
  return s + "</svg>";
}

// チェックした配置。絞り込みに関係なく上部に表示し続ける (ブラウザに保存)
const PIN_KEY = "tsd-patterns-pinned";
let pinned = new Set();
try { pinned = new Set(JSON.parse(localStorage.getItem(PIN_KEY) || "[]").filter(f => byField.has(f))); } catch {}
function savePinned() {
  try { localStorage.setItem(PIN_KEY, JSON.stringify([...pinned])); } catch {}
}

const chip = ([order, soft]) =>
  `<button class="chip${soft ? "" : " hard"}" data-pick="${order}">${order}` +
  (soft ? ` <small>${soft.length} (${soft})</small>` : "") + `</button>`;

// orders: 表示するミノ順 (絞り込み後)。省略時 (チェックした配置の欄) は形だけを表示する
function card(p, orders) {
  const el = document.createElement("div");
  const on = pinned.has(p.f);
  el.className = "card" + (on ? " pin" : "");
  el.innerHTML = `<h2><label><input type="checkbox" data-field="${p.f}"${on ? " checked" : ""}>` +
    `<span>${orders ? `${orders.length} 通りのミノ順 <small>· ${p.r} 段目</small>` : `${p.r} 段目`}</span></label></h2>` +
    (p.n.length ? `<p class="name">${p.n.join(" / ")}</p>` : "") +
    boardSvg(p) + (orders ? `<div class="chips">${orders.map(chip).join("")}</div>` : "");
  return el;
}

const slots = $("slots");
slots.innerHTML = `<b id="first"></b>`;
for (let i = 1; i < 6; i++) {
  slots.insertAdjacentHTML("beforeend", "<i>→</i>");
  const sel = document.createElement("select");
  sel.setAttribute("aria-label", `${i + 1} 番目のミノ`);
  sel.addEventListener("change", () => { limit = PAGE; draw(); });
  slots.append(sel);
}
const selects = [...slots.querySelectorAll("select")];

function setStart(s) {
  start = s;
  limit = PAGE;
  $("first").textContent = s;
  for (const sel of selects)
    sel.innerHTML = `<option value="">Any</option>` +
      [..."IJLSZO"].filter(p => p !== s).map(p => `<option>${p}</option>`).join("");
  for (const b of $("tabs").children) b.setAttribute("aria-selected", b.dataset.start === s);
  draw();
}

function draw() {
  const pat = [start, ...selects.map(s => s.value)];
  for (const s of selects) {
    s.classList.toggle("set", s.value !== "");
    // 他の位置で指定済みのミノは選べないようにする
    for (const o of s.options) o.disabled = o.value !== "" && o.value !== s.value && pat.includes(o.value);
  }
  const maxSoft = Number($("maxsoft").value), rows = $("rows").value;
  const match = order => pat.every((p, i) => !p || order[i] === p);

  // 対象のミノ順。「ソフトドロップありでも組めない」は「なしでは組めない」の部分集合
  const {patterns} = DATA[start];
  const targets = $("target").value === "soft" ? DATA[start].strict : DATA[start].orders;
  const inTarget = new Set(targets);
  const namedOnly = $("named").checked;
  // 条件 (ソフトドロップ・段) を満たすもの。集計はミノ順の絞り込みをかける前の値で出す
  const usable = [];
  const reachable = new Set();
  for (const p of patterns) {
    if (rows && p.r !== rows) continue;
    if (namedOnly && !p.n.length) continue;
    const os = p.o.filter(o => o[1].length <= maxSoft && inTarget.has(o[0]));
    if (!os.length) continue;
    os.forEach(o => reachable.add(o[0]));
    usable.push([p, os]);
  }
  const missing = targets.filter(o => !reachable.has(o));
  $("stats").innerHTML = [
    [targets.length, `対象のミノ順 (${start} 開始)`],
    [usable.length, "配置パターン"],
    [`${reachable.size} / ${targets.length}`, "TSD を打てるミノ順"],
    [`${missing.length} / ${targets.length}`, "打てないミノ順"],
  ].map(([v, l]) => `<div class="stat"><b>${v}</b><span>${l}</span></div>`).join("");
  $("none").hidden = missing.length === 0;
  $("none").innerHTML = `この条件で TSD を打てないミノ順: ` +
    missing.map(o => `<button class="chip ng" data-pick="${o}">${o}</button>`).join(" ");

  const list = usable.map(([p, os]) => [p, os.filter(o => match(o[0]))]).filter(([, os]) => os.length);
  const height = p => p.f.split("/").length;
  if ($("sort").value === "height")
    list.sort((a, b) => height(a[0]) - height(b[0]) || b[1].length - a[1].length);
  else
    list.sort((a, b) => b[1].length - a[1].length || height(a[0]) - height(b[0]));

  $("grid").replaceChildren(...list.slice(0, limit).map(([p, os]) => card(p, os)));
  $("count").textContent = `${list.length} / ${usable.length} パターン`;
  $("more").hidden = list.length <= limit;
  $("more").textContent = `さらに表示 (残り ${list.length - limit})`;
  // チェックした順に並べる
  $("pinned").hidden = pinned.size === 0;
  $("pinned-title").textContent = `チェックした配置 (${pinned.size})`;
  $("pinned-grid").replaceChildren(...[...pinned].map(f => card(byField.get(f))));
  // チェックした配置のどれかを (現在のソフトドロップ条件で) 作れるミノ順が、対象をどれだけ網羅するか
  const covered = new Set();
  for (const f of pinned)
    for (const o of (byStart[start].get(f) || {o: []}).o) if (o[1].length <= maxSoft && inTarget.has(o[0])) covered.add(o[0]);
  const pct = targets.length ? Math.round(covered.size / targets.length * 100) : 0;
  $("coverage").innerHTML =
    `<p>チェックした配置で網羅できる対象のミノ順 (${start} 開始): <b>${covered.size} / ${targets.length}</b> ` +
    `<span>(${pct}%) · 緑が網羅済み</span></p>` +
    `<div class="bar"><div style="width:${targets.length ? covered.size / targets.length * 100 : 0}%"></div></div>` +
    `<div class="cover">` + targets.map(o =>
      `<button class="chip ${covered.has(o) ? "on" : "off"}" data-pick="${o}">${o}</button>`).join("") + `</div>`;
}

for (const s of Object.keys(DATA)) {
  const b = document.createElement("button");
  b.setAttribute("role", "tab");
  b.dataset.start = s;
  b.textContent = `${s} 開始`;
  b.addEventListener("click", () => setStart(s));
  $("tabs").append(b);
}
for (const id of ["target", "maxsoft", "rows", "sort", "named"]) $(id).addEventListener("change", () => { limit = PAGE; draw(); });
$("more").addEventListener("click", () => { limit += PAGE; draw(); });
document.querySelector("main").addEventListener("change", e => {
  const field = e.target.dataset && e.target.dataset.field;
  if (!field) return;
  if (e.target.checked) pinned.add(field); else pinned.delete(field);
  savePinned();
  draw();
});
// ミノ順のチップをクリックしたら、そのミノ順で絞り込む
document.querySelector("main").addEventListener("click", e => {
  const chipEl = e.target.closest && e.target.closest("[data-pick]");
  if (!chipEl) return;
  const order = chipEl.dataset.pick;
  if (order[0] !== start) setStart(order[0]);
  selects.forEach((s, i) => s.value = order[i + 1]);
  limit = PAGE;
  draw();
});
$("unpin-all").addEventListener("click", () => { pinned.clear(); savePinned(); draw(); });
$("reset").addEventListener("click", () => { selects.forEach(s => s.value = ""); limit = PAGE; draw(); });
setStart(start);
</script>
</body>
</html>
"""


def mirror_field(field: str) -> str:
    swap = str.maketrans("SZLJ", "ZSJL")
    return "/".join(row[::-1].translate(swap) for row in field.split("/"))


def template_names(path: Path) -> dict[str, list[str]]:
    """盤面 -> その形を持つ既知テンプレの名前。左右反転した形にも同じ名前を付ける。"""
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    names: dict[str, list[str]] = {}
    for r in rows:
        label = r["name"] + (f" <small>({r['note']})</small>" if r["note"] else "")
        for field in (r["field"], mirror_field(r["field"])):
            if label not in names.setdefault(field, []):
                names[field].append(label)
    return names


def build_data(csv_path: Path) -> dict:
    """開始ミノごとに、対象のミノ順と、重複をまとめた配置パターンの一覧を作る。"""
    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    targets = uncovered_orders()
    strict = uncovered_orders(allow_soft_drop=True)
    names = template_names(TEMPLATES_CSV)
    data = {}
    for start in STARTS:
        patterns: dict[str, dict] = {}
        for r in rows:
            if r["start"] != start:
                continue
            p = patterns.setdefault(
                r["field"],
                {"f": r["field"], "r": r["tsd_rows"], "n": names.get(r["field"], []), "o": []},
            )
            p["o"].append([r["order"], r["soft_drop_pieces"]])
        for p in patterns.values():
            p["o"].sort(key=lambda o: (len(o[1]), o[0]))
        data[start] = {
            "orders": [o for o in targets if o[0] == start],
            "strict": [o for o in strict if o[0] == start],
            "patterns": list(patterns.values()),
        }
    return data


def main() -> None:
    data = json.dumps(build_data(CSV_PATH), ensure_ascii=False, separators=(",", ":"))
    HTML_PATH.write_text(HTML_TEMPLATE.replace("__DATA__", data), encoding="utf-8")
    print(f"wrote {HTML_PATH.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
