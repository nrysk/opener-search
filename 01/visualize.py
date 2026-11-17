"""01/templates.csv (search.py の調査結果) を 01/templates.html として可視化する。

templates.html はデータを埋め込んだ単一ファイルなので、そのままブラウザで開ける。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "templates.csv"
HTML_PATH = HERE / "templates.html"

HTML_TEMPLATE = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>開幕 TSD / アルバトロス TSD のカバー範囲</title>
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
  p.lead { margin: 0 0 16px; color: var(--sub); max-width: 86ch; }
  .stats { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
  .stat { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 8px 14px; }
  .stat b { display: block; font-size: 20px; font-variant-numeric: tabular-nums; }
  .stat span { color: var(--sub); font-size: 12px; }
  .controls { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; margin-bottom: 12px; }
  .controls button, .controls select { font: inherit; color: inherit; background: var(--card);
         border: 1px solid var(--line); border-radius: 6px; padding: 5px 10px; }
  .controls button { cursor: pointer; }
  .controls button[aria-pressed="true"] { border-color: var(--accent); color: var(--accent); font-weight: 600; }
  #slots select { font: 600 14px ui-monospace, Menlo, monospace; padding: 5px 6px; }
  .controls select.set { border-color: var(--accent); color: var(--accent); }
  .controls .label { color: var(--sub); }
  .controls label { display: inline-flex; align-items: center; gap: 6px; cursor: pointer; }
  .controls input[type=checkbox], .card h2 input { width: 16px; height: 16px; margin: 0; accent-color: var(--accent); cursor: pointer; }
  #slots { display: inline-flex; flex-wrap: wrap; gap: 4px; align-items: center; }
  #slots i { color: var(--sub); font-style: normal; }
  #count { color: var(--sub); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 10px; }
  .card.ng { border-color: var(--ng); }
  .card.pin { border-color: var(--accent); }
  .card h2 { font: 600 14px ui-monospace, Menlo, monospace; margin: 0 0 8px; letter-spacing: .12em; }
  .card h2 label { display: flex; align-items: center; gap: 8px; cursor: pointer; }
  .pair { display: flex; gap: 10px; align-items: flex-start; }
  .board { flex: 1; min-width: 0; }
  .board svg { display: block; width: 100%; height: auto; }
  .board.off svg { opacity: .22; }
  .cap { font-size: 12px; color: var(--sub); margin-top: 4px; }
  .cap b { display: block; color: var(--text); font-weight: 600; }
  .cap .no { color: var(--ng); font-weight: 600; }
  .cap .yes { color: var(--ok); font-weight: 600; }
  #pinned { margin-bottom: 20px; padding: 12px; border: 1px dashed var(--accent); border-radius: 10px; }
  #pinned[hidden] { display: none; }
  #pinned header { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
  #pinned h3 { margin: 0; font-size: 14px; color: var(--accent); }
  #pinned button { font: inherit; color: inherit; background: var(--card); border: 1px solid var(--line);
         border-radius: 6px; padding: 3px 10px; cursor: pointer; }
  .legend { color: var(--sub); font-size: 12px; margin: 0 0 16px; }
  .legend svg { width: 12px; height: 12px; vertical-align: -1px; }
</style>
</head>
<body>
<main>
<h1>開幕 TSD / アルバトロス TSD のカバー範囲</h1>
<p class="lead">T が最初に来てホールドに入り、残り 6 ミノを来た順にホールドなしで置く最悪ケースで、
各テンプレをそのまま再現できるかを 720 通りのミノ順すべてについて調べた結果です。
テンプレに複数の形がある場合は、ソフトドロップが最も少ない形を表示します。</p>
<div class="stats" id="stats"></div>
<section id="pinned" hidden>
  <header><h3 id="pinned-title"></h3><button id="unpin-all">すべて外す</button></header>
  <div class="grid" id="pinned-grid"></div>
</section>
<div class="controls">
  <span class="label">条件</span>
  <select id="maxsoft" aria-label="ソフトドロップ回数の上限">
    <option value="6">ソフトドロップ: 制限なし</option>
    <option value="0">ソフトドロップ: なし</option>
    <option value="1">ソフトドロップ: 1 回まで</option>
  </select>
  <label><input type="checkbox" id="mirror"> 開幕 TSD の左右反転形も使う</label>
</div>
<div class="controls">
  <span class="label">結果</span>
  <button data-f="all" aria-pressed="true">すべて</button>
  <button data-f="both">両方で可能</button>
  <button data-f="kaimaku">開幕 TSD のみ可能</button>
  <button data-f="albatross">アルバトロスのみ可能</button>
  <button data-f="none">どちらも不可能</button>
</div>
<div class="controls">
  <span class="label">ミノ順</span>
  <span id="slots"></span>
  <button id="reset">リセット</button>
  <span id="count"></span>
</div>
<p class="legend">黄色の帯は TSD で消える段、紫は T ミノ。
<svg viewBox="0 0 12 12"><rect width="12" height="12" rx="2" fill="#8892a0"/><circle cx="6" cy="6" r="2.4" fill="#fff"/></svg>
白丸のついたミノはソフトドロップが必要 (最後の T は回数に含めません)。</p>
<div class="grid" id="grid"></div>
</main>
<script>
const ROWS = __DATA__;
const COLORS = {I:"#35b8d6", O:"#e6b422", T:"#9b4fd0", S:"#4caf50", Z:"#e0483e", J:"#3a66d0", L:"#ef8a24"};
const FAMILIES = [["kaimaku", "開幕 TSD"], ["albatross", "アルバトロス"]];
const C = 12, BOARD_H = 5;

const byOrder = new Map();
for (const r of ROWS) {
  if (!byOrder.has(r.order)) byOrder.set(r.order, {order: r.order, rows: []});
  byOrder.get(r.order).rows.push(r);
}
const orders = [...byOrder.values()];

const maxSoftEl = document.getElementById("maxsoft"), mirrorEl = document.getElementById("mirror");
// 現在の条件で使えるテンプレのうち、ソフトドロップが最少のもの (なければ null)
function best(o, family) {
  const maxSoft = Number(maxSoftEl.value);
  let res = null;
  for (const r of o.rows) {
    if (r.family !== family || r.buildable !== "1" || Number(r.soft_drops) > maxSoft) continue;
    if (family === "kaimaku" && r.mirrored === "1" && !mirrorEl.checked) continue;
    if (!res || Number(r.soft_drops) < Number(res.soft_drops)) res = r;
  }
  return res;
}
const kind = o => best(o, "kaimaku") ? (best(o, "albatross") ? "both" : "kaimaku")
                                     : (best(o, "albatross") ? "albatross" : "none");

function boardSvg(r, label) {
  const lines = r.field.split("/");
  let s = `<svg viewBox="0 0 ${10 * C} ${BOARD_H * C}" role="img" aria-label="${label}">`;
  for (let y = 0; y < BOARD_H; y++) {
    const line = lines[lines.length - 1 - y];
    const fill = line && !line.includes("_") ? "var(--clear)" : "var(--cell)";
    for (let x = 0; x < 10; x++) {
      const ch = line ? line[x] : "_";
      const px = x * C + .5, py = (BOARD_H - 1 - y) * C + .5;
      s += `<rect x="${px}" y="${py}" width="${C - 1}" height="${C - 1}" rx="1.5" fill="${ch === "_" ? fill : COLORS[ch]}"/>`;
      if (ch !== "_" && r.soft_drop_pieces.includes(ch))
        s += `<circle cx="${px + (C - 1) / 2}" cy="${py + (C - 1) / 2}" r="2.2" fill="#fff"/>`;
    }
  }
  return s + "</svg>";
}

// チェックしたミノ順。絞り込みに関係なく上部に表示し続ける (ブラウザに保存)
const PIN_KEY = "tsd-templates-pinned";
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
    `<span>${o.order}</span></label></h2><div class="pair">`;
  for (const [family, name] of FAMILIES) {
    const r = best(o, family);
    if (r) {
      const n = Number(r.soft_drops);
      html += `<div class="board">${boardSvg(r, `${o.order} ${name}`)}<div class="cap"><b>${name}</b>` +
        `<span class="yes">可能</span> · ソフトドロップ ${n} 回${n ? ` (${[...r.soft_drop_pieces].join(", ")})` : ""}</div></div>`;
    } else {
      const shape = o.rows.find(x => x.family === family);
      html += `<div class="board off">${boardSvg({...shape, soft_drop_pieces: ""}, `${o.order} ${name}`)}` +
        `<div class="cap"><b>${name}</b><span class="no">不可能</span></div></div>`;
    }
  }
  el.innerHTML = html + "</div>";
  return el;
}

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

let filter = "all";
function draw() {
  const pat = selects.map(s => s.value);
  for (const s of selects) {
    s.classList.toggle("set", s.value !== "");
    // 他の位置で指定済みのミノは選べないようにする
    for (const o of s.options) o.disabled = o.value !== "" && o.value !== s.value && pat.includes(o.value);
  }
  const kinds = new Map(orders.map(o => [o.order, kind(o)]));
  const n = k => orders.filter(o => kinds.get(o.order) === k).length;
  const total = orders.length;
  document.getElementById("stats").innerHTML = [
    [`${total - n("none")} / ${total}`, "どちらかで組めるミノ順"],
    [`${n("both") + n("kaimaku")} / ${total}`, "開幕 TSD で組める"],
    [`${n("both") + n("albatross")} / ${total}`, "アルバトロスで組める"],
    [`${n("none")} / ${total}`, "どちらでも組めない"],
  ].map(([v, l]) => `<div class="stat"><b>${v}</b><span>${l}</span></div>`).join("");

  const list = orders.filter(o => (filter === "all" || kinds.get(o.order) === filter) &&
    pat.every((p, i) => !p || o.order[i] === p));
  document.getElementById("grid").replaceChildren(...list.map(card));
  document.getElementById("count").textContent = `${list.length} / ${total} 件`;
  // チェックした順に並べる
  document.getElementById("pinned").hidden = pinned.size === 0;
  document.getElementById("pinned-title").textContent = `チェックしたミノ順 (${pinned.size})`;
  document.getElementById("pinned-grid").replaceChildren(...[...pinned].map(o => card(byOrder.get(o))));
}

for (const b of document.querySelectorAll("button[data-f]"))
  b.addEventListener("click", () => {
    filter = b.dataset.f;
    document.querySelectorAll("button[data-f]").forEach(x => x.setAttribute("aria-pressed", x === b));
    draw();
  });
maxSoftEl.addEventListener("change", draw);
mirrorEl.addEventListener("change", draw);
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
