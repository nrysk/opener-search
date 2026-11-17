"""03 の結果 (candidates.csv, coverage.csv) を 03/pairs.html として可視化する。

対象 (どのミノ順を補完したいか) と条件 (ソフトドロップ上限・左右反転形を使うか) を
画面で選べるように、ペアの順位付けはブラウザ側で計算する。
pairs.html はデータを埋め込んだ単一ファイルなので、そのままブラウザで開ける。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from search import CANDIDATES_CSV, COVERAGE_CSV, ORDERS, baseline

HERE = Path(__file__).resolve().parent
HTML_PATH = HERE / "pairs.html"

HTML_TEMPLATE = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>開幕 TSD + アルバトロス TSD を補完するテンプレの組</title>
<style>
  :root {
    --bg: #f6f7f9; --card: #fff; --line: #d9dde3; --text: #1c2128; --sub: #667080;
    --cell: #eef0f3; --clear: #ffe9a8; --accent: #7b3fc4; --chip: #eef0f3;
    --a: #2f6fd6; --b: #e07b1a; --both: #1e8e4e; --on: #fff;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #14171c; --card: #1d2129; --line: #323843; --text: #e6e9ee; --sub: #98a2b3;
      --cell: #262b35; --clear: #5a4a12; --accent: #c39bff; --chip: #262b35;
      --a: #6ea4ff; --b: #ffa64d; --both: #5fd08d; --on: #10141a;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 24px 16px 48px; background: var(--bg); color: var(--text);
         font: 14px/1.5 system-ui, -apple-system, "Hiragino Sans", sans-serif; }
  main { max-width: 1180px; margin: 0 auto; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  h2 { font-size: 15px; margin: 24px 0 10px; }
  p.lead { margin: 0 0 16px; color: var(--sub); max-width: 86ch; }
  .controls { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; margin-bottom: 12px; }
  .controls select { font: inherit; color: inherit; background: var(--card); max-width: 100%;
         border: 1px solid var(--line); border-radius: 6px; padding: 5px 10px; }
  .controls .label { color: var(--sub); min-width: 2.5em; }
  .controls label { display: inline-flex; align-items: center; gap: 6px; cursor: pointer; }
  .controls input[type=checkbox] { width: 16px; height: 16px; margin: 0; accent-color: var(--accent); }
  .stats { display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0; }
  .stat { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 8px 14px; }
  .stat b { display: block; font-size: 20px; font-variant-numeric: tabular-nums; }
  .stat span { color: var(--sub); font-size: 12px; }
  .panel { background: var(--card); border: 1px solid var(--accent); border-radius: 10px; padding: 14px; }
  .pairhead { display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-start; margin-bottom: 12px; }
  .tpl { width: 190px; max-width: 100%; }
  .tpl svg { display: block; width: 100%; height: auto; }
  .tpl .nm { font-weight: 600; font-size: 13px; margin-bottom: 4px; display: flex; gap: 6px; align-items: baseline; }
  .tpl .nm i { flex: none; width: 10px; height: 10px; border-radius: 2px; }
  .tpl .sub { color: var(--sub); font-size: 12px; margin-top: 4px; }
  .summary { flex: 1; min-width: 220px; }
  .summary b { font-size: 26px; font-variant-numeric: tabular-nums; }
  .summary span { color: var(--sub); }
  .bar { display: flex; height: 10px; margin: 8px 0; border-radius: 5px; background: var(--chip); overflow: hidden; }
  .bar div { height: 100%; }
  .legend { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 12px; color: var(--sub); }
  .legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 4px; }
  .cover { display: grid; grid-template-columns: repeat(auto-fill, minmax(72px, 1fr)); gap: 4px; }
  .cover span { font: 12px ui-monospace, Menlo, monospace; letter-spacing: .06em; text-align: center;
         padding: 3px 0; border-radius: 4px; background: var(--chip); color: var(--sub); }
  .cover .a { background: var(--a); color: var(--on); font-weight: 600; }
  .cover .b { background: var(--b); color: var(--on); font-weight: 600; }
  .cover .ab { background: var(--both); color: var(--on); font-weight: 600; }
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; font-size: 12px; font-weight: 400; color: var(--sub); padding: 4px 8px; border-bottom: 1px solid var(--line); }
  td { padding: 8px; border-bottom: 1px solid var(--line); vertical-align: middle; }
  tbody tr { cursor: pointer; }
  tbody tr:hover { background: var(--card); }
  tbody tr.sel { background: var(--card); box-shadow: inset 3px 0 0 var(--accent); }
  td.rank { width: 3em; color: var(--sub); font-variant-numeric: tabular-nums; }
  td.num { width: 11em; font-variant-numeric: tabular-nums; white-space: nowrap; }
  td.num b { font-size: 16px; }
  td.num small { color: var(--sub); }
  td.mini { width: 110px; }
  td.mini svg { display: block; width: 94px; height: auto; }
  td.nm small { color: var(--sub); display: block; }
  .wrap { overflow-x: auto; }
  .more { display: block; margin: 16px auto 0; font: inherit; color: inherit; background: var(--card);
         border: 1px solid var(--line); border-radius: 6px; padding: 5px 14px; cursor: pointer; }
  .more[hidden] { display: none; }
</style>
</head>
<body>
<main>
<h1>開幕 TSD + アルバトロス TSD を補完するテンプレの組</h1>
<p class="lead">開幕 TSD でもアルバトロス TSD でも組めないミノ順を、追加で覚える 2 つのテンプレでどこまで網羅できるかの順位です。
前提は「T が最初に来てホールドに入り、残り 6 ミノを来た順にホールドなしで置く」。
候補は既知テンプレのうち 6 ミノ + T でできた __NCAND__ 個で、全 __NPAIR__ 組を調べています。</p>

<div class="controls">
  <span class="label">対象</span>
  <select id="target" aria-label="対象のミノ順">
    <option value="hard">ソフトドロップなしでは開幕 TSD / アルバトロス TSD を組めないミノ順</option>
    <option value="soft">ソフトドロップありでも開幕 TSD / アルバトロス TSD を組めないミノ順</option>
  </select>
</div>
<div class="controls">
  <span class="label">条件</span>
  <select id="maxsoft" aria-label="追加テンプレのソフトドロップ回数の上限">
    <option value="0">追加テンプレのソフトドロップ: なし</option>
    <option value="1">追加テンプレのソフトドロップ: 1 回まで</option>
    <option value="6">追加テンプレのソフトドロップ: 制限なし</option>
  </select>
  <label><input type="checkbox" id="mirror" checked> 追加テンプレの左右反転形も使う</label>
</div>
<div class="controls">
  <span class="label">固定</span>
  <select id="fix" aria-label="1 つ目のテンプレを固定"></select>
</div>

<div class="stats" id="stats"></div>

<h2 id="detail-title"></h2>
<div class="panel" id="detail"></div>

<h2>順位</h2>
<div class="wrap"><table>
  <thead><tr><th>順位</th><th>網羅できる対象のミノ順</th><th colspan="2">テンプレ A</th><th colspan="2">テンプレ B</th></tr></thead>
  <tbody id="rank"></tbody>
</table></div>
<button class="more" id="more" hidden></button>
</main>
<script>
const DATA = __DATA__;
const COLORS = {I:"#35b8d6", O:"#e6b422", T:"#9b4fd0", S:"#4caf50", Z:"#e0483e", J:"#3a66d0", L:"#ef8a24"};
const C = 12, PAGE = 50;
const $ = id => document.getElementById(id);
const {orders, candidates} = DATA;
const N = orders.length;

// ミノ順 i を左右反転 (S<->Z, L<->J) したミノ順の番号
const SWAP = {S: "Z", Z: "S", L: "J", J: "L"};
const index = new Map(orders.map((o, i) => [o, i]));
const mirrorOf = orders.map(o => index.get([...o].map(c => SWAP[c] || c).join("")));

function boardSvg(field) {
  const lines = field.split("/"), h = Math.max(5, lines.length);
  let s = `<svg viewBox="0 0 ${10 * C} ${h * C}" role="img" aria-label="テンプレの形">`;
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

const fix = $("fix");
fix.innerHTML = `<option value="">テンプレを固定しない (全ての組から探す)</option>` +
  candidates.map((c, i) => `<option value="${i}">A を固定: ${c.name}</option>`).join("");

let ranking = [], targets = [], cover = [], selected = null, limit = PAGE;

// 現在の対象・条件で、各候補が網羅する対象ミノ順 (0/1 の配列) を作り、全ペアを順位付けする
function compute() {
  const targetFlags = DATA.targets[$("target").value];
  const maxSoft = Number($("maxsoft").value), useMirror = $("mirror").checked;
  targets = [];
  for (let i = 0; i < N; i++) if (targetFlags[i] === "1") targets.push(i);
  const ok = (c, i) => c.cov[i] !== "-" && Number(c.cov[i]) <= maxSoft;
  cover = candidates.map(c => {
    const bits = new Uint8Array(targets.length);
    let n = 0;
    targets.forEach((i, k) => {
      // 反転形でミノ順 i を組める <=> 元の形で反転したミノ順を組める
      if (ok(c, i) || (useMirror && ok(c, mirrorOf[i]))) { bits[k] = 1; n++; }
    });
    return {bits, n};
  });
  ranking = [];
  const fixed = fix.value === "" ? null : Number(fix.value);
  for (let a = 0; a < candidates.length; a++) {
    if (fixed !== null && a !== fixed) continue;
    for (let b = fixed !== null ? 0 : a + 1; b < candidates.length; b++) {
      if (a === b) continue;
      const x = cover[a].bits, y = cover[b].bits;
      let n = 0;
      for (let k = 0; k < x.length; k++) n += x[k] | y[k];
      ranking.push({a, b, n});
    }
  }
  // 同数なら、単体での網羅数の合計が小さい (= 重なりが少ない) 組を先にする
  ranking.sort((p, q) => q.n - p.n || (cover[p.a].n + cover[p.b].n) - (cover[q.a].n + cover[q.b].n));
  selected = ranking[0] || null;
  limit = PAGE;
  draw();
}

const pct = n => targets.length ? Math.round(n / targets.length * 100) : 0;

function drawDetail() {
  const p = selected;
  if (!p) { $("detail").innerHTML = ""; return; }
  const A = candidates[p.a], B = candidates[p.b], x = cover[p.a].bits, y = cover[p.b].bits;
  let onlyA = 0, onlyB = 0, both = 0;
  const cells = targets.map((i, k) => {
    const cls = x[k] && y[k] ? "ab" : x[k] ? "a" : y[k] ? "b" : "";
    if (cls === "ab") both++; else if (cls === "a") onlyA++; else if (cls === "b") onlyB++;
    return `<span class="${cls}">${orders[i]}</span>`;
  }).join("");
  const none = targets.length - p.n, w = n => `width:${targets.length ? n / targets.length * 100 : 0}%`;
  const rank = ranking.indexOf(p) + 1;
  $("detail-title").textContent = `選択中の組 (${rank} 位)`;
  const tpl = (c, n, color) => `<div class="tpl"><div class="nm"><i style="background:var(--${color})"></i>${c.name}</div>` +
    boardSvg(c.field) + `<div class="sub">単体で ${n} / ${targets.length} 通り</div></div>`;
  $("detail").innerHTML = `<div class="pairhead">${tpl(A, cover[p.a].n, "a")}${tpl(B, cover[p.b].n, "b")}` +
    `<div class="summary"><b>${p.n} / ${targets.length}</b> <span>通りを網羅 (${pct(p.n)}%)</span>` +
    `<div class="bar"><div style="${w(onlyA)};background:var(--a)"></div><div style="${w(both)};background:var(--both)"></div>` +
    `<div style="${w(onlyB)};background:var(--b)"></div></div>` +
    `<div class="legend"><span><i style="background:var(--a)"></i>A のみ ${onlyA}</span>` +
    `<span><i style="background:var(--both)"></i>両方 ${both}</span>` +
    `<span><i style="background:var(--b)"></i>B のみ ${onlyB}</span>` +
    `<span><i style="background:var(--chip)"></i>どちらでも組めない ${none}</span></div></div></div>` +
    `<div class="cover">${cells}</div>`;
}

function draw() {
  const best = ranking[0];
  const ties = best ? ranking.filter(p => p.n === best.n).length : 0;
  $("stats").innerHTML = [
    [targets.length, "対象のミノ順"],
    [best ? `${best.n} / ${targets.length}` : "-", "最良の組が網羅する数"],
    [best ? targets.length - best.n : "-", "最良の組でも残る数"],
    [ties, "同率 1 位の組"],
  ].map(([v, l]) => `<div class="stat"><b>${v}</b><span>${l}</span></div>`).join("");
  drawDetail();
  let rank = 0, prev = null;
  $("rank").innerHTML = ranking.slice(0, limit).map((p, i) => {
    if (p.n !== prev) { rank = i + 1; prev = p.n; }
    const A = candidates[p.a], B = candidates[p.b];
    return `<tr data-i="${i}"${p === selected ? ' class="sel"' : ""}><td class="rank">${rank}</td>` +
      `<td class="num"><b>${p.n}</b> / ${targets.length} <small>(${pct(p.n)}%)</small></td>` +
      `<td class="mini">${boardSvg(A.field)}</td><td class="nm">${A.name}<small>単体 ${cover[p.a].n}</small></td>` +
      `<td class="mini">${boardSvg(B.field)}</td><td class="nm">${B.name}<small>単体 ${cover[p.b].n}</small></td></tr>`;
  }).join("");
  $("more").hidden = ranking.length <= limit;
  $("more").textContent = `さらに表示 (残り ${ranking.length - limit} 組)`;
}

for (const id of ["target", "maxsoft", "mirror", "fix"]) $(id).addEventListener("change", compute);
$("rank").addEventListener("click", e => {
  const tr = e.target.closest && e.target.closest("tr[data-i]");
  if (!tr) return;
  selected = ranking[Number(tr.dataset.i)];
  draw();
  $("detail-title").scrollIntoView({behavior: "smooth", block: "start"});
});
$("more").addEventListener("click", () => { limit += PAGE; draw(); });
compute();
</script>
</body>
</html>
"""


def build_data() -> dict:
    with CANDIDATES_CSV.open(newline="", encoding="utf-8") as f:
        candidates = list(csv.DictReader(f))
    soft: dict[str, dict[str, str]] = {c["id"]: {} for c in candidates}
    with COVERAGE_CSV.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            soft[r["id"]][r["order"]] = r["soft_drops"]
    _, targets = baseline()
    return {
        "orders": ORDERS,
        # ミノ順ごとに、対象なら "1"
        "targets": {k: "".join("1" if o in v else "0" for o in ORDERS) for k, v in targets.items()},
        # cov: ミノ順ごとに、ソフトドロップ回数 (組めなければ "-")。テンプレの向きそのままの場合
        "candidates": [
            {
                "id": c["id"],
                "name": c["name"],
                "field": c["field"],
                "cov": "".join(soft[c["id"]].get(o, "-") for o in ORDERS),
            }
            for c in candidates
        ],
    }


def main() -> None:
    data = build_data()
    n = len(data["candidates"])
    html = (
        HTML_TEMPLATE.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        .replace("__NCAND__", str(n))
        .replace("__NPAIR__", str(n * (n - 1) // 2))
    )
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"wrote {HTML_PATH.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
