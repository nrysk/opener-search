"""lib/followup.py の列挙結果を、単一ファイルの HTML として可視化する。05, 06 で共有する。

グループ (タブ) ごとにシルエットを並べ、各シルエットをどのミノ順で組めるかを 720 マス (始動ミノを固定したタブでは 120 マス) の
「ミノ順マップ」で表示する。2 つのシルエットの組の網羅数はブラウザ側で現在の条件に合わせて計算する。
"""

from __future__ import annotations

import json
from pathlib import Path

from lib.followup import NAMES, ORDER_INDEX

HTML_TEMPLATE = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root {
    --bg: #f6f7f9; --card: #fff; --line: #d9dde3; --text: #1c2128; --sub: #667080;
    --cell: #eef0f3; --clear: #e0a800; --ok: #1e8e4e; --soft: #d99a00; --accent: #7b3fc4; --chip: #eef0f3;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #14171c; --card: #1d2129; --line: #323843; --text: #e6e9ee; --sub: #98a2b3;
      --cell: #262b35; --clear: #e6b422; --ok: #5fd08d; --soft: #e6b422; --accent: #c39bff; --chip: #262b35;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 24px 16px 48px; background: var(--bg); color: var(--text);
         font: 14px/1.5 system-ui, -apple-system, "Hiragino Sans", sans-serif; }
  main { max-width: 1280px; margin: 0 auto; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  p.lead { margin: 0 0 16px; color: var(--sub); max-width: 86ch; }
  .tabs { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
  .tabs button { font: inherit; font-weight: 600; color: var(--sub); background: var(--card); min-width: 84px;
         border: 1px solid var(--line); border-radius: 8px; padding: 6px 8px 8px; cursor: pointer; }
  .tabs button[aria-selected="true"] { color: var(--accent); border-color: var(--accent); }
  .tabs small { display: block; font-size: 10px; font-weight: 400; line-height: 1.3; margin-top: 2px; }
  .tabs svg { display: block; width: 66px; height: auto; margin: 4px auto 0; }
  .tabs .tab-boards { display: flex; gap: 4px; }
  .summary { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: flex-start; margin-bottom: 16px; }
  .stats { display: flex; flex-wrap: wrap; gap: 8px; }
  .stat { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 8px 14px; }
  .stat b { display: block; font-size: 20px; font-variant-numeric: tabular-nums; }
  .stat span { color: var(--sub); font-size: 12px; }
  .panel { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 8px 12px 10px; }
  .panel h3 { margin: 0 0 6px; font-size: 12px; font-weight: 400; color: var(--sub); }
  .controls { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; margin-bottom: 12px; }
  .controls button, .controls select, .more { font: inherit; color: inherit; background: var(--card);
         border: 1px solid var(--line); border-radius: 6px; padding: 5px 10px; }
  .controls button, .more { cursor: pointer; }
  #slots select { font: 600 14px ui-monospace, Menlo, monospace; padding: 5px 6px; }
  .controls select.set { border-color: var(--accent); color: var(--accent); }
  .controls .label { color: var(--sub); }
  #slots { display: inline-flex; flex-wrap: wrap; gap: 4px; align-items: center; }
  #slots i { color: var(--sub); font-style: normal; }
  #count { color: var(--sub); }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 10px; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 10px; }
  .card.pin { border-color: var(--accent); }
  .card h2 { font-size: 13px; font-weight: 600; margin: 0 0 8px; }
  .card h2 label { display: flex; align-items: center; gap: 8px; cursor: pointer; }
  .card h2 small { color: var(--sub); font-weight: 400; }
  .card h2 input { width: 16px; height: 16px; margin: 0; accent-color: var(--accent); cursor: pointer; }
  .card svg { display: block; width: 100%; max-width: 260px; height: auto; margin: 0 auto; }
  .card .tiling { display: flex; justify-content: center; align-items: center; gap: 8px; margin-top: 6px;
         font-size: 12px; color: var(--sub); }
  .card .tiling button { font: inherit; color: inherit; background: var(--chip); border: 1px solid var(--line);
         border-radius: 4px; padding: 0 8px; cursor: pointer; }
  .card .tiling button.icon { display: inline-flex; align-items: center; padding: 2px 5px; }
  .card .tiling button.icon svg { width: 14px; height: 14px; margin: 0; pointer-events: none; }
  canvas.map { display: block; margin: 10px auto 0; cursor: crosshair; }
  .maps canvas.map { margin: 0; }
  .maps { display: flex; flex-wrap: wrap; gap: 8px 20px; }
  h4 { margin: 0 0 4px; font-size: 12px; font-weight: 600; color: var(--sub); }
  .grid.wide { grid-template-columns: repeat(auto-fill, minmax(460px, 1fr)); }
  .sides { display: flex; gap: 12px; }
  .side { flex: 1; min-width: 0; }
  .board { cursor: pointer; position: relative; }
  .board small { position: absolute; top: 0; left: 0; font-size: 11px; color: var(--sub); }
  #pairs { margin-bottom: 16px; }
  #pairs p { margin: 0 0 8px; font-size: 13px; }
  #pairs p b { font-size: 16px; font-variant-numeric: tabular-nums; }
  #pairs-list { display: flex; flex-wrap: wrap; gap: 8px; }
  .pair { display: grid; grid-template-columns: 84px 84px; gap: 4px 6px; font: inherit; color: inherit; cursor: pointer;
         background: var(--bg); border: 1px solid var(--line); border-radius: 8px; padding: 6px 8px; }
  .pair:hover { border-color: var(--accent); }
  .pair svg { width: 100%; height: auto; }
  .pair span { grid-column: 1 / 3; font-size: 12px; font-variant-numeric: tabular-nums; }
  .pair small { color: var(--sub); }
  .stat svg { display: block; width: 100px; height: auto; margin-bottom: 4px; }
  #pinned { margin-bottom: 20px; padding: 12px; border: 1px dashed var(--accent); border-radius: 10px; }
  #pinned[hidden], .tabs[hidden], .controls[hidden] { display: none; }
  #pinned header { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
  #pinned h3 { margin: 0; font-size: 14px; color: var(--accent); }
  #pinned header button { font: inherit; color: inherit; background: var(--card); border: 1px solid var(--line);
         border-radius: 6px; padding: 3px 10px; cursor: pointer; }
  #coverage { margin-top: 12px; }
  #coverage p { margin: 0 0 8px; font-size: 13px; }
  #coverage p b { font-size: 16px; font-variant-numeric: tabular-nums; }
  .legend { color: var(--sub); font-size: 12px; margin: 0 0 16px; max-width: 100ch; }
  .legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; vertical-align: -1px; margin-right: 3px; }
  .more { display: block; margin: 16px auto 0; }
  .more[hidden] { display: none; }
  #tip { position: fixed; z-index: 10; pointer-events: none; padding: 3px 8px; border-radius: 6px;
         background: var(--text); color: var(--bg); font: 12px ui-monospace, Menlo, monospace; white-space: nowrap; }
  #tip[hidden] { display: none; }
</style>
</head>
<body>
<main>
<h1>__TITLE__</h1>
<p class="lead">__LEAD__</p>
<div class="tabs" role="tablist" id="tabs"></div>
<div class="summary">
  <div class="stats" id="stats"></div>
  <div class="panel"><h3>この条件でどれかのシルエットを組めるミノ順</h3><div class="maps" id="union"></div></div>
</div>
<section class="panel" id="pairs">
  <h3>2 つのシルエットの組み合わせ (下の条件での網羅数が多い順。クリックするとその 2 つをチェックします)</h3>
  <p id="pairs-text"></p>
  <div id="pairs-list"></div>
</section>
<section id="pinned" hidden>
  <header><h3 id="pinned-title"></h3><button id="copy-pinned" title="チェックした盤面をまとめて 04/board.html に貼れる形でコピー">まとめてコピー</button><button id="unpin-all">すべて外す</button></header>
  <div class="grid" id="pinned-grid"></div>
  <div id="coverage"><p id="coverage-text"></p><div class="maps" id="pinned-map"></div></div>
</section>
<div class="controls">
  <span class="label">条件</span>
  <select id="maxsoft" aria-label="ソフトドロップ回数の上限">
    <option value="6">ソフトドロップ: 制限なし</option>
    <option value="0">ソフトドロップ: なし</option>
    <option value="1">ソフトドロップ: 1 回まで</option>
    <option value="2">ソフトドロップ: 2 回まで</option>
  </select>
  <select id="rows" aria-label="__SPIN__ を打つ段"></select>
  <select id="sort" aria-label="並び順">
    <option value="orders">組めるミノ順が多い順</option>
    <option value="height">低い順</option>
    <option value="clean">きれいな順 (消去後の穴が少ない順)</option>
  </select>
</div>
<div class="controls" id="order-controls">
  <span class="label">ミノ順</span>
  <span id="slots"></span>
  <button id="reset">リセット</button>
  <span id="count"></span>
</div>
<p class="legend">盤面: 両脇の黄色い印は __SPIN__ で消える段、紫は T ミノ<span id="legend-start">、薄い色は開始形状 (前の巡までの残り)</span>。
ミノ順マップ: 1 マスが 1 つのミノ順。左の文字が 1 番目のミノで、その中の 5 行が 2 番目のミノ、
24 列が残り 4 ミノの順番です。
<i style="background:var(--ok)"></i>ソフトドロップなしで組める
<i style="background:var(--soft)"></i>ソフトドロップが必要
<i style="background:var(--cell)"></i>組めない (最後の T は回数に含めません)。
マスにカーソルを置くとミノ順を表示<span id="legend-click">し、クリックするとそのミノ順で絞り込み</span>ます。
盤面をクリックすると、ライン消去後の地形に切り替わります (もう一度クリックで戻ります)。</p>
<div class="grid" id="grid"></div>
<button class="more" id="more" hidden></button>
</main>
<div id="tip" hidden></div>
<script>
const DATA = __DATA__;
const NAMES = "IJLSZO";
const COLORS = {I:"#35b8d6", O:"#e6b422", T:"#9b4fd0", S:"#4caf50", Z:"#e0483e", J:"#3a66d0", L:"#ef8a24"};
const C = 12, PAGE = 120, TOP_PAIRS = 12;
const $ = id => document.getElementById(id);

// 720 通りのミノ順 (辞書順。search.py の ORDERS と同じ並び)
const ORDERS = [];
(function perm(prefix, rest) {
  if (!rest.length) { ORDERS.push(prefix); return; }
  for (const c of rest) perm(prefix + c, rest.replace(c, ""));
})("", NAMES);

// グループ: {l: [開始形状の名前, ...], f: [開始形状, ...], p: [パターン, ...]}。開始形状ごとのグループは
// l が 1 つ、A・B 共通のグループは 2 つ。パターン: {id, r: T スピンで消す段, n: 補足 (省略可), s: [開始形状ごとのミノ割り一覧]}、
// ミノ割りは [盤面, ミノ順の列]。ミノ順の列は 3 文字ずつで、36 進 2 桁のミノ順番号 + ソフトドロップ回数。
// グループに first (始動ミノ) があれば、そのミノで始まる 120 通りだけを扱い、ミノ順番号もその中での番号になる。
// st[k * N + i] = k 番目の開始形状でミノ順 i が 0 (組めない) / ソフトドロップ回数 + 1 (N はグループのミノ順の数)
function decode(s, n) {
  const st = new Uint8Array(n);
  for (let i = 0; i < s.length; i += 3) st[parseInt(s.slice(i, i + 2), 36)] = Number(s[i + 2]) + 1;
  return st;
}
const merge = (dst, src, off = 0) => {
  for (let i = 0; i < src.length; i++) if (src[i] && (!dst[off + i] || src[i] < dst[off + i])) dst[off + i] = src[i];
};
const isEmpty = field => !/[^_\/]/.test(field);
// グループの開始形状 [[名前, 形], ...]。starts があれば (いくつかの開始形状をまとめたタブ) それを使う
const startsOf = g => g.starts || g.l.map((l, k) => [l, g.f[k]]);
const byId = new Map();
for (const gid of Object.keys(DATA)) {
  const g = DATA[gid];
  g.ord = g.first ? ORDERS.filter(o => o[0] === g.first) : ORDERS;
  // before = [a, b] なら、a が b より先に来るミノ順だけを数える (ほかのミノ順はマップで薄く表示する)
  g.valid = g.before ? g.ord.map(o => o.indexOf(g.before[0]) < o.indexOf(g.before[1])) : null;
  g.total = g.valid ? g.valid.filter(Boolean).length : g.ord.length;
  const n = g.ord.length;
  for (const p of g.p) {
    p.gid = gid;
    p.key = g.first || g.before ? gid + ":" + p.id : p.id;  // 同じシルエットが複数のタブに出るので、タブごとに区別する
    p.sides = p.s.map(ts => ({ts: ts.map(([f, o]) => ({f, st: decode(o, n)})), shown: 0}));
    p.st = new Uint8Array(n * p.sides.length);  // ミノ割りをまたいだ最良 (ソフトドロップ最少)
    p.sides.forEach((side, k) => side.ts.forEach(t => merge(p.st, t.st, k * n)));
    p.h = p.sides[0].ts[0].f.split("/").length;
    p.holes = p.sides.reduce((n, side) => n + holes(afterClear(side.ts[0].f)), 0);
    byId.set(p.key, p);
  }
}

let start = Object.keys(DATA)[0], limit = PAGE;

function boardSvg(field, minRows) {
  const lines = field.split("/"), h = Math.max(minRows, lines.length);
  let s = `<svg viewBox="-6 0 ${10 * C + 12} ${h * C}" role="img" aria-label="盤面">`;
  for (let y = 0; y < h; y++) {
    const line = lines[lines.length - 1 - y];
    // T スピンで消える段 (すべて埋まっている段) の両脇に印を付ける
    if (line && !line.includes("_")) for (const x of [-6, 10 * C + 2])
      s += `<rect x="${x}" y="${(h - 1 - y) * C + .5}" width="4" height="${C - 1}" rx="1.5" fill="var(--clear)"/>`;
    for (let x = 0; x < 10; x++) {
      const ch = line ? line[x] : "_", up = ch.toUpperCase();
      const attr = ch === "_" ? `fill="var(--cell)"` : `fill="${COLORS[up]}"` + (ch === up ? "" : ` opacity=".4"`);
      s += `<rect x="${x * C + .5}" y="${(h - 1 - y) * C + .5}" width="${C - 1}" height="${C - 1}" rx="1.5" ${attr}/>`;
    }
  }
  return s + "</svg>";
}

// ライン消去後の地形: そろった段を取り除いて上の段を下ろす (読み込み時にも使うので関数宣言にしておく)
function afterClear(field) {
  return field.split("/").filter(line => line.includes("_")).join("/");
}
// 形のきれいさ: 盤面で、上 (同じ列のどこか) にブロックがある空白マスの数 (穴の数)。少ないほどきれい
function holes(field) {
  const lines = field.split("/");
  let n = 0;
  for (let x = 0; x < 10; x++) {
    let covered = false;
    for (const line of lines) {  // 上の段から見ていく
      if (line[x] !== "_") covered = true;
      else if (covered) n++;
    }
  }
  return n;
}

// 04/board.html に貼れる形 (1 行 = 「タイトル<Tab>盤面」) にする。表示中のミノ割りと、消去前 / 後の状態をそのまま写す。
// 開始形状のマス (小文字) も通常のミノの色にする
function boxText(p, k) {
  const g = DATA[p.gid], side = p.sides[k], t = side.ts[side.shown];
  const field = (p.after ? afterClear(t.f) : t.f).toUpperCase();
  const title = [p.id, g.l[k], `${p.r} 段目`].concat(p.after ? ["消去後"] : []).join(" ");
  return `${title}\t${field}`;
}
// コピーボタンのアイコン (重なった 2 枚の紙) と、コピーした直後に出すチェック
const ICON = d => `<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5" ` +
  `stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
const COPY_ICON = ICON(`<rect x="5.5" y="5.5" width="8" height="8" rx="1.5"/><path d="M10.5 3.5v-.5a1.5 1.5 0 0 0-1.5-1.5H4A1.5 1.5 0 0 0 2.5 3v5A1.5 1.5 0 0 0 4 9.5h.5"/>`);
const CHECK_ICON = ICON(`<path d="M3 8.5l3 3 7-7"/>`);
function copyText(text, button) {
  const done = () => {
    // アイコンだけのボタンはチェックに、文字のボタンは「コピーしました」に一時的に変える
    const icon = button.classList.contains("icon"), before = button.innerHTML;
    if (button.dataset.busy) return;
    button.dataset.busy = "1";
    if (icon) button.innerHTML = CHECK_ICON; else button.textContent = "コピーしました";
    setTimeout(() => { button.innerHTML = before; delete button.dataset.busy; }, 1200);
  };
  const fallback = () => {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.append(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
    done();
  };
  if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, fallback);
  else fallback();
}

// ミノ順マップ: 1 番目のミノごとのブロック (6 個。始動ミノを固定したタブでは 1 個) x 2 番目のミノ (5 行) x 残り (24 列)
const CW = 8, GAP = 4, GUT = 14, MAP_W = GUT + 24 * CW;
function drawMap(canvas, st, maxSoft, off, ord, valid = null) {
  const dpr = window.devicePixelRatio || 1, css = getComputedStyle(document.documentElement);
  const v = name => css.getPropertyValue(name).trim();
  const nb = ord.length / 120, CH = nb === 1 ? 10 : 5, MAP_H = nb * 5 * CH + (nb - 1) * GAP;
  canvas.width = MAP_W * dpr; canvas.height = MAP_H * dpr;
  canvas.style.width = MAP_W + "px"; canvas.style.height = MAP_H + "px";
  Object.assign(canvas, {st, maxSoft, off, ord, nb, ch: CH, valid});
  const g = canvas.getContext("2d");
  g.scale(dpr, dpr);
  g.font = "600 11px ui-monospace, Menlo, monospace";
  g.textBaseline = "middle";
  const cell = v("--cell"), ok = v("--ok"), soft = v("--soft");
  for (let b = 0; b < nb; b++) {
    const y0 = b * (5 * CH + GAP);
    g.fillStyle = v("--sub");
    g.fillText(ord[b * 120][0], 0, y0 + 5 * CH / 2);
    for (let r = 0; r < 5; r++) for (let c = 0; c < 24; c++) {
      const i = b * 120 + r * 24 + c, s = st[off + i];
      g.fillStyle = !s || s - 1 > maxSoft ? cell : s === 1 ? ok : soft;
      g.globalAlpha = valid && !valid[i] ? .25 : 1;  // 数えないミノ順は薄くする
      g.fillRect(GUT + c * CW, y0 + r * CH, CW - 1, CH - 1);
      g.globalAlpha = 1;
    }
  }
}
function mapIndex(canvas, e) {
  const rect = canvas.getBoundingClientRect();
  const x = e.clientX - rect.left - GUT, y = e.clientY - rect.top, CH = canvas.ch;
  const b = Math.floor(y / (5 * CH + GAP)), r = Math.floor((y - b * (5 * CH + GAP)) / CH), c = Math.floor(x / CW);
  return x < 0 || c > 23 || b < 0 || b >= canvas.nb || r > 4 ? -1 : b * 120 + r * 24 + c;
}
// 開始形状ごとのマップを横に並べる (A・B 共通のグループでは 2 枚)
function mapsInto(el, st, maxSoft) {
  const labels = DATA[start].l, ord = DATA[start].ord;
  el.replaceChildren(...labels.map((label, k) => {
    const box = document.createElement("div");
    if (labels.length > 1) box.innerHTML = `<h4>${label}</h4>`;
    const canvas = document.createElement("canvas");
    canvas.className = "map";
    box.append(canvas);
    drawMap(canvas, st, maxSoft, k * ord.length, ord, DATA[start].valid);
    return box;
  }));
}

const PIN_KEY = "__PIN_KEY__";
let pinned = new Set();
try { pinned = new Set(JSON.parse(localStorage.getItem(PIN_KEY) || "[]").filter(id => byId.has(id))); } catch {}
function savePinned() {
  try { localStorage.setItem(PIN_KEY, JSON.stringify([...pinned])); } catch {}
}

// match を渡すと、ミノ順の絞り込みに合うものだけを数える
const count = (st, maxSoft, match, from = 0, to = st.length) => {
  let n = 0;
  for (let i = from; i < to; i++) if (st[i] && st[i] - 1 <= maxSoft && (!match || match[i % match.length])) n++;
  return n;
};

function card(p, maxSoft) {
  const el = document.createElement("div");
  const on = pinned.has(p.key), labels = DATA[p.gid].l, multi = labels.length > 1, ord = DATA[p.gid].ord, n = ord.length;
  el.className = "card" + (on ? " pin" : "");
  const per = labels.map((_, k) => count(p.st, maxSoft, null, k * n, k * n + n));
  const title = multi ? labels.map((l, k) => `${l.slice(-1)} ${per[k]}`).join(" + ") + " 通りのミノ順" :
    `${per[0]}${DATA[p.gid].total < 720 ? " / " + DATA[p.gid].total : ""} 通りのミノ順`;
  el.innerHTML = `<h2><label><input type="checkbox" data-pin="${p.key}"${on ? " checked" : ""}>` +
    `<span>${title} <small>· ${multi ? "" : labels[0] + " · "}${p.r} 段目 · 穴 ${p.holes}${p.n ? " · " + p.n : ""}</small></span></label></h2>` +
    `<div class="sides">` + p.sides.map((side, k) => {
      const t = side.ts[side.shown];
      return `<div class="side">` + (multi ? `<h4>${labels[k]}</h4>` : "") +
        `<div class="board" data-after="${p.key}" title="クリックでライン消去前 / 後を切り替え">` +
        (p.after ? `<small>消去後</small>` + boardSvg(afterClear(t.f), __MAXH__) : boardSvg(t.f, __MAXH__)) + `</div>` +
        `<div class="tiling"><button class="icon" data-copy="${p.key}" data-side="${k}" title="この盤面を 04/board.html に貼れる形でコピー" aria-label="コピー">${COPY_ICON}</button>` +
        (side.ts.length > 1 ? `<button data-cycle="${p.key}" data-side="${k}">◀▶</button>` +
          `<span>ミノ割り ${side.shown + 1} / ${side.ts.length} (この割り方で ${count(t.st, maxSoft)} 通り)</span>` : "") + `</div>` +
        `<canvas class="map"></canvas></div>`;
    }).join("") + `</div>`;
  el.querySelectorAll("canvas").forEach((c, k) => drawMap(c, p.st, maxSoft, k * n, ord, DATA[p.gid].valid));
  return el;
}

// 2 つのシルエットの組の網羅数。ミノ順の集合を 32 bit ごとの配列で持ち、全ペアを調べる
const pop = x => { x -= x >>> 1 & 0x55555555; x = (x & 0x33333333) + (x >>> 2 & 0x33333333); return (x + (x >>> 4) & 0x0f0f0f0f) * 0x01010101 >>> 24; };
// ミノ順集合が同じシルエットはまとめて 1 回だけ比べる (全網羅の組数はまとめた数を掛けて数える)。
// 上位の組には、まとめたうちの最も低いシルエットを代表として出す
function bestPairs(usable, maxSoft, total) {
  const same = new Map();  // ミノ順集合 -> {w, ps}
  for (const p of usable) {
    const w = new Uint32Array(Math.ceil(p.st.length / 32));
    for (let i = 0; i < p.st.length; i++) if (p.st[i] && p.st[i] - 1 <= maxSoft) w[i >> 5] |= 1 << (i & 31);
    const key = w.join(",");
    if (!same.has(key)) same.set(key, {w, ps: []});
    same.get(key).ps.push(p);
  }
  const uniq = [...same.values()];
  for (const u of uniq) u.ps.sort((a, b) => a.h - b.h);
  const words = uniq.length ? uniq[0].w.length : 0;
  let full = 0;
  const top = [];  // [網羅数, p, q] を網羅数の多い順に TOP_PAIRS 個まで
  const offer = (n, p, q) => {
    if (top.length < TOP_PAIRS || n > top[top.length - 1][0]) {
      top.push([n, p, q]);
      top.sort((a, b) => b[0] - a[0]);
      if (top.length > TOP_PAIRS) top.pop();
    }
  };
  for (let i = 0; i < uniq.length; i++) {
    const a = uniq[i];
    if (a.ps.length > 1) {
      let n = 0;
      for (let k = 0; k < words; k++) n += pop(a.w[k]);
      if (n === total) full += a.ps.length * (a.ps.length - 1) / 2;
      offer(n, a.ps[0], a.ps[1]);
    }
    for (let j = i + 1; j < uniq.length; j++) {
      const b = uniq[j];
      let n = 0;
      for (let k = 0; k < words; k++) n += pop(a.w[k] | b.w[k]);
      if (n === total) full += a.ps.length * b.ps.length;
      offer(n, a.ps[0], b.ps[0]);
    }
  }
  return {full, total, top};
}

const pairCache = new Map();
// ミノ順で絞り込む欄を出すか (出さない場合はマップのクリックでも絞り込まない)
const ORDER_FILTER = __ORDER_FILTER__;
$("order-controls").hidden = !ORDER_FILTER;
$("legend-click").hidden = !ORDER_FILTER;
const slots = $("slots");
for (let i = 0; i < 6; i++) {
  if (i) slots.insertAdjacentHTML("beforeend", "<i>→</i>");
  const sel = document.createElement("select");
  sel.setAttribute("aria-label", `${i + 1} 番目のミノ`);
  sel.innerHTML = `<option value="">Any</option>` + [...NAMES].map(p => `<option>${p}</option>`).join("");
  sel.addEventListener("change", () => { limit = PAGE; draw(); });
  slots.append(sel);
}
const selects = [...slots.querySelectorAll("select")];

function setStart(s) {
  start = s;
  limit = PAGE;
  const rows = [...new Set(DATA[s].p.map(p => p.r))].sort();
  $("rows").innerHTML = `<option value="">__SPIN__ の段: すべて</option>` +
    rows.map(r => `<option value="${r}">__SPIN__ の段: ${r} 段目</option>`).join("");
  for (const b of $("tabs").children) b.setAttribute("aria-selected", b.dataset.start === s);
  draw();
}

function draw() {
  const pat = selects.map(s => s.value);
  for (const s of selects) {
    s.classList.toggle("set", s.value !== "");
    for (const o of s.options) o.disabled = o.value !== "" && o.value !== s.value && pat.includes(o.value);
  }
  const maxSoft = Number($("maxsoft").value), rows = $("rows").value;
  const filtered = pat.some(Boolean);
  const group = DATA[start], labels = group.l, n = group.ord.length, total = group.total * labels.length;
  const match = group.ord.map(o => pat.every((p, i) => !p || o[i] === p));
  for (const id of ["grid", "pinned-grid"]) $(id).classList.toggle("wide", labels.length > 1);

  // 条件 (ソフトドロップ・段) を満たすシルエット。集計はミノ順の絞り込みをかける前の値で出す
  const usable = [], union = new Uint8Array(n * labels.length);
  for (const p of group.p) {
    if (rows && p.r !== rows) continue;
    if (!count(p.st, maxSoft)) continue;
    usable.push(p);
    merge(union, p.st);
  }
  const covered = count(union, maxSoft);
  $("stats").innerHTML =
    startsOf(group).map(([l, f]) => isEmpty(f) ? "" :
      `<div class="stat">${boardSvg(f, 2)}<span>開始形状 ${l}</span></div>`).join("") + [
      [usable.length, labels.length > 1 ? "A・B 共通のシルエット" : "シルエット"],
      [`${covered} / ${total}`, "__SPIN__ を打てるミノ順" + (labels.length > 1 ? ` (A ${n} + B ${n})` : group.first ? ` (${group.first} 始動)` :
        group.before ? ` (${group.before[0]} が ${group.before[1]} より先)` : "")],
      [`${count(union, 0)} / ${total}`, "うちソフトドロップなし"],
      [`${total - covered} / ${total}`, "打てないミノ順"],
    ].map(([v, l]) => `<div class="stat"><b>${v}</b><span>${l}</span></div>`).join("");
  mapsInto($("union"), union, maxSoft);

  // 2 つの組み合わせ (シルエットが多いと重いので、条件ごとに 1 回だけ計算する)
  const pairKey = `${start}|${maxSoft}|${rows}`;
  if (!pairCache.has(pairKey)) pairCache.set(pairKey, bestPairs(usable, maxSoft, total));
  const pairs = pairCache.get(pairKey);
  $("pairs-text").innerHTML = pairs.top.length === 0 ? "シルエットが 2 つ以上ありません。" :
    pairs.full ? `2 つで全 ${total} 通りを網羅できる組: <b>${pairs.full} 組</b>` :
    `2 つで全 ${total} 通りを網羅できる組はありません (最大 <b>${pairs.top[0][0]} / ${total}</b>)。`;
  $("pairs-list").replaceChildren(...pairs.top.map(([n, a, b]) => {
    const el = document.createElement("button");
    el.className = "pair";
    el.dataset.pair = a.key + "," + b.key;
    el.title = "この 2 つをチェックする";
    el.innerHTML = boardSvg(a.sides[0].ts[0].f, __MAXH__) + boardSvg(b.sides[0].ts[0].f, __MAXH__) +
      `<span><b>${n}</b> / ${total} <small>(${Math.round(n / total * 100)}%)</small></span>`;
    return el;
  }));

  // ミノ順で絞り込んでも、並び順はシルエット全体の「組めるミノ順の数」を使う
  const list = usable.filter(p => !filtered || count(p.st, maxSoft, match)).map(p => [p, count(p.st, maxSoft)]);
  if ($("sort").value === "height") list.sort((a, b) => a[0].h - b[0].h || b[1] - a[1]);
  else if ($("sort").value === "clean") list.sort((a, b) => a[0].holes - b[0].holes || b[1] - a[1] || a[0].h - b[0].h);
  else list.sort((a, b) => b[1] - a[1] || a[0].h - b[0].h);

  $("grid").replaceChildren(...list.slice(0, limit).map(([p]) => card(p, maxSoft)));
  $("count").textContent = `${list.length} / ${usable.length} シルエット`;
  $("more").hidden = list.length <= limit;
  $("more").textContent = `さらに表示 (残り ${list.length - limit})`;

  // チェックしたシルエット (このグループのもの) と、それらで網羅できるミノ順
  const mine = [...pinned].map(id => byId.get(id)).filter(p => p.gid === start);
  $("pinned").hidden = mine.length === 0;
  $("pinned-title").textContent = `チェックしたシルエット (${mine.length})`;
  $("pinned-grid").replaceChildren(...mine.map(p => card(p, maxSoft)));
  const pu = new Uint8Array(n * labels.length);
  for (const p of mine) merge(pu, p.st);
  const pc = count(pu, maxSoft);
  $("coverage-text").innerHTML = `チェックしたシルエットで網羅できるミノ順: <b>${pc} / ${total}</b> (${Math.round(pc / total * 100)}%)` +
    (labels.length > 1 ? " — " + labels.map((l, k) => `${l}: ${count(pu, maxSoft, null, k * n, k * n + n)} / ${n}`).join(", ") : "");
  mapsInto($("pinned-map"), pu, maxSoft);
}

// 開始形状が空の盤面だけ (開幕) なら、タブと開始形状の説明を出さない
$("tabs").hidden = Object.keys(DATA).length === 1;
$("legend-start").hidden = Object.values(DATA).every(g => g.f.every(isEmpty));
for (const gid of Object.keys(DATA)) {
  const b = document.createElement("button"), g = DATA[gid];
  b.setAttribute("role", "tab");
  b.dataset.start = gid;
  b.innerHTML = g.l.length > 1 ? `${gid.slice(0, -2)} 共通<small>A・B 同形<br>${g.p.length} 種類</small>` :
    isEmpty(g.f[0]) ? `${gid}<small>${g.p.length} 種類</small>` :
    gid + `<span class="tab-boards">${startsOf(g).map(([, f]) => boardSvg(f, 2)).join("")}</span>`;
  b.addEventListener("click", () => setStart(gid));
  $("tabs").append(b);
}
for (const id of ["maxsoft", "rows", "sort"]) $(id).addEventListener("change", () => { limit = PAGE; draw(); });
$("more").addEventListener("click", () => { limit += PAGE; draw(); });
const main = document.querySelector("main");
main.addEventListener("change", e => {
  const id = e.target.dataset && e.target.dataset.pin;
  if (!id) return;
  if (e.target.checked) pinned.add(id); else pinned.delete(id);
  savePinned();
  draw();
});
function unpinGroup() {
  for (const id of [...pinned]) if (byId.get(id).gid === start) pinned.delete(id);
}
main.addEventListener("click", e => {
  const pair = e.target.closest(".pair");
  if (pair) {
    unpinGroup();
    for (const id of pair.dataset.pair.split(",")) pinned.add(id);
    savePinned();
    draw();
    $("pinned").scrollIntoView({behavior: "smooth", block: "start"});
    return;
  }
  const board = e.target.closest(".board");
  if (board) {
    const p = byId.get(board.dataset.after);
    p.after = !p.after;
    draw();
    return;
  }
  const cp = e.target.dataset && e.target.dataset.copy;
  if (cp) {
    copyText(boxText(byId.get(cp), Number(e.target.dataset.side)), e.target);
    return;
  }
  const cyc = e.target.dataset && e.target.dataset.cycle;
  if (cyc) {
    const side = byId.get(cyc).sides[Number(e.target.dataset.side)];
    side.shown = (side.shown + 1) % side.ts.length;
    draw();
    return;
  }
  if (!e.target.classList.contains("map")) return;
  const i = mapIndex(e.target, e);
  if (i < 0) return;
  if (!ORDER_FILTER) return;
  selects.forEach((s, k) => s.value = DATA[start].ord[i][k]);
  limit = PAGE;
  draw();
});
const tip = $("tip");
main.addEventListener("mousemove", e => {
  const i = e.target.classList.contains("map") ? mapIndex(e.target, e) : -1;
  tip.hidden = i < 0;
  if (i < 0) return;
  const s = e.target.st[e.target.off + i], ok = s && s - 1 <= e.target.maxSoft;
  tip.textContent = e.target.ord[i] + (e.target.valid && !e.target.valid[i] ? ": 数えないミノ順" :
    !ok ? ": 組めない" : s === 1 ? ": ソフトドロップなし" : `: ソフトドロップ ${s - 1} 回`);
  tip.style.left = Math.min(e.clientX + 12, window.innerWidth - 220) + "px";
  tip.style.top = e.clientY + 14 + "px";
});
main.addEventListener("mouseleave", () => { tip.hidden = true; });
$("copy-pinned").addEventListener("click", e => {
  const mine = [...pinned].map(id => byId.get(id)).filter(p => p.gid === start);
  copyText(mine.flatMap(p => p.sides.map((_, k) => boxText(p, k))).join("\n"), e.target);
});
$("unpin-all").addEventListener("click", () => { unpinGroup(); savePinned(); draw(); });
$("reset").addEventListener("click", () => { selects.forEach(s => s.value = ""); limit = PAGE; draw(); });
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", draw);
setStart(start);
</script>
</body>
</html>
"""

DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def encode_orders(orders: dict[str, str], first: str | None = None) -> str:
    """ミノ順 -> ソフトドロップ対象ミノ を、36 進 2 桁のミノ順番号 + ソフトドロップ回数の列にする。

    first (始動ミノ) を指定すると、ミノ順番号はそのミノで始まる 120 通りの中での番号になる。
    """
    out = []
    for order, soft in orders.items():
        i = ORDER_INDEX[order]
        if first:
            assert order[0] == first
            i -= NAMES.index(first) * 120
        out.append(DIGITS[i // 36] + DIGITS[i % 36] + str(len(soft)))
    return "".join(out)


def group(
    labels: list[str],
    fields: list[str],
    members: list[list[dict]],
    first: str | None = None,
    starts: list[tuple[str, str]] | None = None,
    before: tuple[str, str] | None = None,
) -> dict:
    """タブ 1 つ分のデータ。

    labels / fields は開始形状の名前と形 (通常 1 つ。複数の開始形状に共通のシルエットを扱うなら複数)、
    members の各要素は開始形状ごとのパターン (lib.followup.load_patterns の値) を並べたもの。
    パターンに note があれば、カードの見出しに補足として表示する。
    first (始動ミノ) を指定すると、そのミノで始まる 120 通りのミノ順だけを扱うタブになる
    (members のミノ順はそのミノで始まるものだけにしておく)。
    starts ([(名前, 形), ...]) を指定すると、いくつかの開始形状のシルエットをまとめた 1 つのタブとして、
    その開始形状をすべて表示する (どれかから組めればよい、という見方。各パターンの note に開始形状の名前を入れておく)。
    before ((a, b)) を指定すると、a が b より先に来るミノ順だけを数えるタブになる
    (members のミノ順はその条件を満たすものだけにしておく。ほかのミノ順はマップで薄く表示する)。
    """
    return {
        **({"first": first} if first else {}),
        **({"starts": [list(s) for s in starts]} if starts else {}),
        **({"before": list(before)} if before else {}),
        "l": labels,
        "f": fields,
        "p": [
            {
                "id": "+".join(p["id"] for p in ps),
                "r": ps[0]["rows"],
                "n": ps[0].get("note", ""),
                "s": [[[field, encode_orders(orders, first)] for field, orders in p["tilings"]] for p in ps],
            }
            for ps in members
        ],
    }


def write_html(
    path: Path,
    data: dict[str, dict],
    title: str,
    lead: str,
    max_height: int,
    pin_key: str,
    spin: str = "TSD",
    order_filter: bool = True,
) -> None:
    """data はタブ名 -> group() の値。lead は見出し下の説明文 (HTML)。spin は "TSD" か "TSS"。

    order_filter が False なら、ミノ順で絞り込む欄を出さない。
    """
    html = (
        HTML_TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        .replace("__MAXH__", str(max_height))
        .replace("__TITLE__", title)
        .replace("__LEAD__", lead)
        .replace("__PIN_KEY__", pin_key)
        .replace("__SPIN__", spin)
        .replace("__ORDER_FILTER__", "true" if order_filter else "false")
    )
    path.write_text(html, encoding="utf-8")
    print(f"wrote {path}")
