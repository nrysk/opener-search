"""00/tsd.csv (search.py の探索結果) を 00/tsd.html として可視化する。

tsd.html はデータを埋め込んだ単一ファイルなので、そのままブラウザで開ける。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "tsd.csv"
HTML_PATH = HERE / "tsd.html"

HTML_TEMPLATE = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>1巡目 TSD 探索結果</title>
<style>
  :root {
    --bg: #f6f7f9; --card: #fff; --line: #d9dde3; --text: #1c2128; --sub: #667080;
    --cell: #eef0f3; --clear: #ffe9a8; --ng: #c0392b; --ok: #1e8e4e; --accent: #7b3fc4;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #14171c; --card: #1d2129; --line: #323843; --text: #e6e9ee; --sub: #98a2b3;
      --cell: #262b35; --clear: #5a4a12; --ng: #ff7b6b; --ok: #5fd08d; --accent: #c39bff;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 24px 16px 48px; background: var(--bg); color: var(--text);
         font: 14px/1.5 system-ui, -apple-system, "Hiragino Sans", sans-serif; }
  main { max-width: 1280px; margin: 0 auto; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  p.lead { margin: 0 0 16px; color: var(--sub); max-width: 80ch; }
  .stats { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
  .stat { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 8px 14px; }
  .stat b { display: block; font-size: 20px; font-variant-numeric: tabular-nums; }
  .stat span { color: var(--sub); font-size: 12px; }
  .controls { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 16px; }
  .controls button { font: inherit; color: inherit; background: var(--card);
         border: 1px solid var(--line); border-radius: 6px; padding: 5px 10px; }
  .controls button { cursor: pointer; }
  .controls button[aria-pressed="true"] { border-color: var(--accent); color: var(--accent); font-weight: 600; }
  .controls select { font: 600 14px ui-monospace, Menlo, monospace; color: inherit; background: var(--card);
         border: 1px solid var(--line); border-radius: 6px; padding: 5px 6px; }
  .controls select.set { border-color: var(--accent); color: var(--accent); }
  .controls .label { color: var(--sub); }
  #slots { display: inline-flex; flex-wrap: wrap; gap: 4px; align-items: center; }
  #slots i { color: var(--sub); font-style: normal; }
  #count { color: var(--sub); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 10px; }
  .card.ng { border-color: var(--ng); }
  .card h2 { font: 600 14px ui-monospace, Menlo, monospace; margin: 0 0 8px; letter-spacing: .12em; }
  .card h2 { display: flex; align-items: center; gap: 8px; }
  .card h2 label { display: flex; align-items: center; gap: 8px; cursor: pointer; flex: 1; }
  .card h2 input { width: 16px; height: 16px; margin: 0; accent-color: var(--accent); cursor: pointer; }
  .card.pin { border-color: var(--accent); }
  #pinned { margin-bottom: 20px; padding: 12px; border: 1px dashed var(--accent); border-radius: 10px; }
  #pinned[hidden] { display: none; }
  #pinned header { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
  #pinned h3 { margin: 0; font-size: 14px; color: var(--accent); }
  #pinned button { font: inherit; color: inherit; background: var(--card); border: 1px solid var(--line);
         border-radius: 6px; padding: 3px 10px; cursor: pointer; }
  .card h2 small { color: var(--sub); font-weight: 400; letter-spacing: .05em; }
  .pair { display: flex; gap: 10px; align-items: flex-end; }
  .board { flex: 1; min-width: 0; }
  .board svg { display: block; width: 100%; height: auto; }
  .cap { font-size: 12px; color: var(--sub); margin-top: 4px; }
  .cap .no { color: var(--ng); font-weight: 600; }
  .cap .yes { color: var(--ok); font-weight: 600; }
</style>
</head>
<body>
<main>
<h1>1巡目 TSD 探索結果</h1>
<p class="lead">T が最初に来てホールドに入り、残り 6 ミノを来た順にホールドなしで置いたあと T で TSD を打てるか。
720 通りのミノ順それぞれについて、1-2 段目で打つ形と 2-3 段目で打つ形を 1 つずつ示します
(探索は左右反転 S⇔Z, L⇔J で同一視した 360 通りで行い、残りは反転して表示しています)。
黄色の帯が TSD で消える段、紫が T ミノです。</p>
<div class="stats" id="stats"></div>
<section id="pinned" hidden>
  <header><h3 id="pinned-title"></h3><button id="unpin-all">すべて外す</button></header>
  <div class="grid" id="pinned-grid"></div>
</section>
<div class="controls">
  <button data-f="all" aria-pressed="true">すべて</button>
  <button data-f="both">両方で可能</button>
  <button data-f="only12">1-2 段目のみ可能</button>
  <button data-f="only23">2-3 段目のみ可能</button>
  <button data-f="none">どちらも不可能</button>
</div>
<div class="controls">
  <span class="label">ミノ順</span>
  <span id="slots"></span>
  <button id="reset">リセット</button>
  <span id="count"></span>
</div>
<div class="grid" id="grid"></div>
</main>
<script>
const ROWS = __DATA__;
const COLORS = {I:"#35b8d6", O:"#e6b422", T:"#9b4fd0", S:"#4caf50", Z:"#e0483e", J:"#3a66d0", L:"#ef8a24"};
const C = 12, MIN_H = 5;

// 探索は反転で同一視した 360 通りだけなので、残りは盤面を左右反転して補う
const SWAP = {S: "Z", Z: "S", L: "J", J: "L"};
const flip = line => [...line].reverse().map(c => SWAP[c] || c).join("");
const byOrder = new Map();
function add(order, mirror, r, field) {
  if (!byOrder.has(order)) byOrder.set(order, {order, mirror});
  byOrder.get(order)[r.tsd_rows] = {...r, order, field};
}
for (const r of ROWS) {
  add(r.order, r.mirror_order, r, r.field);
  add(r.mirror_order, r.order, r, r.field.split("/").map(flip).join("/"));
}
const orders = [...byOrder.values()].sort((a, b) => a.order < b.order ? -1 : 1);
const ok = (o, k) => o[k] && o[k].found === "1";
const kind = o => ok(o, "1-2") ? (ok(o, "2-3") ? "both" : "only12") : (ok(o, "2-3") ? "only23" : "none");

function boardSvg(r) {
  const lines = r.field ? r.field.split("/") : [];
  const h = Math.max(MIN_H, lines.length);
  const base = Number(r.tsd_rows[0]) - 1;
  let s = `<svg viewBox="0 0 ${10 * C} ${h * C}" role="img" aria-label="${r.order} ${r.tsd_rows}段目">`;
  for (let y = 0; y < h; y++) {
    const fill = (y === base || y === base + 1) ? "var(--clear)" : "var(--cell)";
    for (let x = 0; x < 10; x++)
      s += `<rect x="${x * C + .5}" y="${(h - 1 - y) * C + .5}" width="${C - 1}" height="${C - 1}" rx="1.5" fill="${fill}"/>`;
  }
  lines.forEach((line, i) => {
    const y = lines.length - 1 - i;
    [...line].forEach((ch, x) => {
      if (ch !== "_")
        s += `<rect x="${x * C + .5}" y="${(h - 1 - y) * C + .5}" width="${C - 1}" height="${C - 1}" rx="1.5" fill="${COLORS[ch]}"/>`;
    });
  });
  return s + "</svg>";
}

// チェックしたミノ順。絞り込みに関係なく上部に表示し続ける (ブラウザに保存)
const PIN_KEY = "tsd-pinned";
let pinned = new Set();
try { pinned = new Set(JSON.parse(localStorage.getItem(PIN_KEY) || "[]").filter(o => byOrder.has(o))); } catch {}
function savePinned() {
  try { localStorage.setItem(PIN_KEY, JSON.stringify([...pinned])); } catch {}
}

function card(o) {
  const el = document.createElement("div");
  const on = pinned.has(o.order);
  el.className = "card" + (kind(o) === "none" ? " ng" : "") + (on ? " pin" : "");
  let html = `<h2><label><input type="checkbox" data-order="${o.order}"${on ? " checked" : ""}>` +
    `<span>${o.order} <small>(反転: ${o.mirror})</small></span></label></h2><div class="pair">`;
  for (const k of ["1-2", "2-3"]) {
    const r = o[k];
    if (!r) continue;
    html += `<div class="board">${boardSvg(r)}<div class="cap">${k} 段目: ` +
      (r.found === "1" ? `<span class="yes">可能</span>` : `<span class="no">不可能</span>`) + `</div></div>`;
  }
  el.innerHTML = html + "</div>";
  return el;
}

let filter = "all";
const slots = document.getElementById("slots");
for (let i = 0; i < 6; i++) {
  if (i) slots.insertAdjacentHTML("beforeend", "<i>→</i>");
  const sel = document.createElement("select");
  sel.setAttribute("aria-label", `${i + 1} 番目のミノ`);
  sel.innerHTML = `<option value="">Any</option>` + [..."IJLSZO"].map(p => `<option>${p}</option>`).join("");
  sel.addEventListener("change", draw);
  slots.append(sel);
}
const selects = [...slots.querySelectorAll("select")];

function draw() {
  const pat = selects.map(s => s.value);
  for (const s of selects) {
    s.classList.toggle("set", s.value !== "");
    // 他の位置で指定済みのミノは選べないようにする
    for (const o of s.options) o.disabled = o.value !== "" && o.value !== s.value && pat.includes(o.value);
  }
  const list = orders.filter(o => (filter === "all" || kind(o) === filter) &&
    pat.every((p, i) => !p || o.order[i] === p));
  const grid = document.getElementById("grid");
  grid.replaceChildren(...list.map(card));
  // チェックした順に並べる
  document.getElementById("pinned").hidden = pinned.size === 0;
  document.getElementById("pinned-title").textContent = `チェックしたミノ順 (${pinned.size})`;
  document.getElementById("pinned-grid").replaceChildren(...[...pinned].map(o => card(byOrder.get(o))));
  document.getElementById("count").textContent = `${list.length} / ${orders.length} 件`;
}

const n = k => orders.filter(o => kind(o) === k).length;
const n12 = orders.filter(o => ok(o, "1-2")).length, n23 = orders.filter(o => ok(o, "2-3")).length;
document.getElementById("stats").innerHTML = [
  [`${orders.length - n("none")} / ${orders.length}`, "TSD を打てるミノ順"],
  [`${n12} / ${orders.length}`, "1-2 段目で打てる"],
  [`${n23} / ${orders.length}`, "2-3 段目で打てる"],
  [`${n("none")}`, "どちらでも打てない"],
].map(([v, l]) => `<div class="stat"><b>${v}</b><span>${l}</span></div>`).join("");

for (const b of document.querySelectorAll("button[data-f]"))
  b.addEventListener("click", () => {
    filter = b.dataset.f;
    document.querySelectorAll("button[data-f]").forEach(x => x.setAttribute("aria-pressed", x === b));
    draw();
  });
document.querySelector("main").addEventListener("change", e => {
  const order = e.target.dataset && e.target.dataset.order;
  if (!order) return;
  if (e.target.checked) pinned.add(order); else pinned.delete(order);
  savePinned();
  draw();
});
document.getElementById("unpin-all").addEventListener("click", () => {
  pinned.clear();
  savePinned();
  draw();
});
document.getElementById("reset").addEventListener("click", () => {
  selects.forEach(s => s.value = "");
  draw();
});
draw();
</script>
</body>
</html>
"""


def write_html(csv_path: Path, html_path: Path) -> None:
    with csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    data = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    html_path.write_text(HTML_TEMPLATE.replace("__DATA__", data), encoding="utf-8")


def main() -> None:
    write_html(CSV_PATH, HTML_PATH)
    print(f"wrote {HTML_PATH.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
