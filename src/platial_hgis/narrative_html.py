"""D3-P5: Zero-backend standalone interactive HTML compiler for NarrativeStoryboard."""

from __future__ import annotations

import html
import json
import pathlib

from .narrative import NarrativeStoryboard


def compile_narrative_html(
    storyboard: NarrativeStoryboard,
    output_path: str | pathlib.Path | None = None,
) -> str:
    """Compile a validated NarrativeStoryboard into a zero-backend interactive HTML file."""
    data_json = json.dumps(storyboard.to_dict(), ensure_ascii=False).replace("</", "<\\/")
    title_esc = html.escape(storyboard.title)
    subtitle_esc = html.escape(storyboard.subtitle or "Evidence-Bound Spatiotemporal Narrative Map")
    notice_esc = html.escape(storyboard.provenance_notice)

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title_esc} — Platial-HGIS Narrative</title>
<style>
  :root {{
    --bg: #0f1419;
    --panel: #171f27;
    --border: #283440;
    --text: #e6edf3;
    --muted: #93a4b5;
    --accent: #38bdf8;
    --verified: #22c55e;
    --indirect: #f59e0b;
    --speculative: #a855f7;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Noto Sans SC", sans-serif;
    background: var(--bg);
    color: var(--text);
    display: grid;
    grid-template-rows: auto 1fr auto;
    min-height: 100vh;
  }}
  header {{
    padding: 14px 20px;
    border-bottom: 1px solid var(--border);
    background: #121920;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }}
  header h1 {{ margin: 0; font-size: 1.18rem; letter-spacing: 0.02em; }}
  header .sub {{ color: var(--muted); font-size: 0.85rem; margin-top: 3px; }}
  .view-switch {{ display: flex; gap: 6px; }}
  .view-switch button, .controls button {{
    background: #1e2935;
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 6px 11px;
    cursor: pointer;
    font-size: 0.84rem;
  }}
  .view-switch button.active {{
    background: var(--accent);
    color: #081018;
    border-color: var(--accent);
    font-weight: 600;
  }}
  main {{
    display: grid;
    grid-template-columns: 1.55fr 1fr;
    min-height: 0;
  }}
  @media (max-width: 900px) {{
    main {{ grid-template-columns: 1fr; }}
  }}
  #map-stage {{
    position: relative;
    background: radial-gradient(circle at 50% 45%, #162330 0%, #0d131a 100%);
    border-right: 1px solid var(--border);
    min-height: 440px;
    display: flex;
    flex-direction: column;
  }}
  #map-stage.historical {{
    background: radial-gradient(circle at 50% 45%, #3a3021 0%, #231c13 100%);
  }}
  #map-svg {{
    width: 100%;
    height: 100%;
    min-height: 420px;
    display: block;
  }}
  .hud {{
    position: absolute;
    top: 12px;
    left: 12px;
    background: rgba(15, 20, 25, 0.84);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 0.78rem;
    color: var(--muted);
    line-height: 1.45;
  }}
  .hud strong {{ color: var(--text); }}
  aside {{
    padding: 18px 20px;
    background: var(--panel);
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }}
  .badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 0.74rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }}
  .badge.verified {{ background: rgba(34,197,94,0.18); color: var(--verified); border: 1px solid var(--verified); }}
  .badge.indirect {{ background: rgba(245,158,11,0.18); color: var(--indirect); border: 1px solid var(--indirect); }}
  .badge.speculative {{ background: rgba(168,85,247,0.18); color: var(--speculative); border: 1px solid var(--speculative); }}
  .scene-meta {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; font-size: 0.82rem; color: var(--muted); }}
  .narrative-body {{ font-size: 0.96rem; line-height: 1.65; margin: 0; }}
  .card {{
    background: #121920;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 14px;
  }}
  .card h3 {{ margin: 0 0 8px 0; font-size: 0.86rem; color: var(--accent); text-transform: uppercase; letter-spacing: 0.05em; }}
  .ev-item {{
    padding: 8px 0;
    border-top: 1px solid #1e2833;
    font-size: 0.84rem;
    line-height: 1.45;
  }}
  .ev-item:first-of-type {{ border-top: none; padding-top: 0; }}
  .ev-item code {{ color: #7dd3fc; font-size: 0.78rem; }}
  .notice {{ font-size: 0.76rem; color: var(--muted); border-left: 3px solid var(--accent); padding-left: 10px; }}
  footer {{
    padding: 12px 20px;
    border-top: 1px solid var(--border);
    background: #121920;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}
  .controls {{
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }}
  #timeline-slider {{ flex: 1; min-width: 180px; accent-color: var(--accent); }}
  .scene-pills {{ display: flex; gap: 6px; flex-wrap: wrap; }}
  .pill {{
    padding: 4px 9px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: #18222c;
    color: var(--muted);
    font-size: 0.78rem;
    cursor: pointer;
  }}
  .pill.active {{ border-color: var(--accent); color: var(--text); background: #203142; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>{title_esc}</h1>
    <div class="sub">{subtitle_esc}</div>
  </div>
  <div class="view-switch" role="group" aria-label="Map View Switcher">
    <button id="btn-view-modern" class="active" onclick="setViewMode('modern')">现代地理视图 (Modern)</button>
    <button id="btn-view-historical" onclick="setViewMode('historical')">古图舆图视图 (Historical)</button>
    <button id="btn-view-affect" onclick="setViewMode('affect')">地方情感场 (Affect)</button>
  </div>
</header>

<main>
  <section id="map-stage">
    <div class="hud" id="camera-hud">Loading camera telemetry...</div>
    <svg id="map-svg" viewBox="0 0 800 500" preserveAspectRatio="xMidYMid meet"></svg>
  </section>
  <aside>
    <div class="scene-meta">
      <span id="scene-badge" class="badge verified">verified</span>
      <span id="scene-time"></span>
      <span id="scene-shift"></span>
    </div>
    <h2 id="scene-title" style="margin:0;font-size:1.25rem;"></h2>
    <div id="scene-heritage" style="font-size:0.85rem;color:#7dd3fc;"></div>
    <p id="scene-text" class="narrative-body"></p>

    <div class="card">
      <h3>史料溯源卡 (Evidence Provenance)</h3>
      <div id="evidence-list"></div>
    </div>

    <div class="card">
      <h3>运镜与地方感参数 (Camera &amp; Platial Telemetry)</h3>
      <div id="telemetry-box" style="font-size:0.82rem;color:#cbd5e1;line-height:1.6;"></div>
    </div>

    <div class="notice">{notice_esc}</div>
  </aside>
</main>

<footer>
  <div class="controls">
    <button onclick="prevScene()">◀ 上一镜</button>
    <button id="btn-play" onclick="togglePlay()">▶ 自动播放</button>
    <button onclick="nextScene()">下一镜 ▶</button>
    <input id="timeline-slider" type="range" min="0" max="0" value="0" oninput="goToScene(parseInt(this.value, 10))" />
    <span id="timeline-label" style="font-size:0.84rem;color:#93a4b5;"></span>
  </div>
  <div class="scene-pills" id="scene-pills"></div>
</footer>

<script>
const STORYBOARD = {data_json};
let currentIndex = 0;
let viewMode = "modern";
let playTimer = null;

const scenes = STORYBOARD.scenes;
const sources = STORYBOARD.sources;

// Project WGS84 lon/lat onto an 800x500 SVG coordinate space
const lons = scenes.map(s => s.camera.center[0]);
const lats = scenes.map(s => s.camera.center[1]);
const minLon = Math.min(...lons) - 1.2;
const maxLon = Math.max(...lons) + 1.2;
const minLat = Math.min(...lats) - 1.0;
const maxLat = Math.max(...lats) + 1.0;

function proj(lon, lat) {{
  const x = 70 + ((lon - minLon) / Math.max(0.1, maxLon - minLon)) * 660;
  const y = 430 - ((lat - minLat) / Math.max(0.1, maxLat - minLat)) * 360;
  return [x, y];
}}

function valenceColor(v) {{
  if (v >= 0.35) return "#22c55e";
  if (v <= -0.35) return "#f43f5e";
  return "#f59e0b";
}}

function formatYear(y) {{
  const yi = Math.round(y);
  return yi <= 0 ? `${{1 - yi}} BCE` : `${{yi}} CE`;
}}

function formatInterval(w) {{
  const s = w.earliest_start === w.latest_start
    ? formatYear(w.earliest_start)
    : `${{formatYear(w.earliest_start)}}–${{formatYear(w.latest_start)}}`;
  const e = w.earliest_end === w.latest_end
    ? formatYear(w.earliest_end)
    : `${{formatYear(w.earliest_end)}}–${{formatYear(w.latest_end)}}`;
  return s === e ? s : `${{s}} → ${{e}}`;
}}

function setViewMode(mode) {{
  viewMode = mode;
  document.getElementById("map-stage").className = mode === "historical" ? "historical" : "";
  for (const m of ["modern", "historical", "affect"]) {{
    document.getElementById("btn-view-" + m).classList.toggle("active", m === mode);
  }}
  renderMap();
}}

function renderMap() {{
  const svg = document.getElementById("map-svg");
  const active = scenes[currentIndex];
  const pts = scenes.map(s => proj(s.camera.center[0], s.camera.center[1]));
  const [ax, ay] = pts[currentIndex];

  // Camera zoom affects SVG viewBox
  const zoomFactor = Math.max(1.0, Math.min(2.6, active.camera.zoom / 6.5));
  const vbW = 800 / zoomFactor;
  const vbH = 500 / zoomFactor;
  const vbX = Math.max(0, Math.min(800 - vbW, ax - vbW / 2));
  const vbY = Math.max(0, Math.min(500 - vbH, ay - vbH / 2));
  svg.setAttribute("viewBox", `${{vbX.toFixed(1)}} ${{vbY.toFixed(1)}} ${{vbW.toFixed(1)}} ${{vbH.toFixed(1)}}`);

  const gridStroke = viewMode === "historical" ? "rgba(220,190,130,0.16)" : "rgba(148,163,184,0.12)";
  const lineStroke = viewMode === "historical" ? "#d97706" : "#38bdf8";

  let out = "";
  // Graticule / historical scroll grid
  for (let gx = 80; gx < 800; gx += 80) {{
    out += `<line x1="${{gx}}" y1="0" x2="${{gx}}" y2="500" stroke="${{gridStroke}}" stroke-width="1" />`;
  }}
  for (let gy = 60; gy < 500; gy += 60) {{
    out += `<line x1="0" y1="${{gy}}" x2="800" y2="${{gy}}" stroke="${{gridStroke}}" stroke-width="1" />`;
  }}

  // Linear heritage route polyline
  const poly = pts.map(p => `${{p[0].toFixed(1)}},${{p[1].toFixed(1)}}`).join(" ");
  out += `<polyline points="${{poly}}" fill="none" stroke="${{lineStroke}}" stroke-width="3" stroke-dasharray="${{viewMode === 'historical' ? '6,4' : 'none'}}" opacity="0.78" />`;

  // Affective halos in affect mode
  if (viewMode === "affect") {{
    scenes.forEach((s, idx) => {{
      const [px, py] = pts[idx];
      const col = valenceColor(s.valence);
      out += `<circle cx="${{px.toFixed(1)}}" cy="${{py.toFixed(1)}}" r="36" fill="${{col}}" opacity="0.22" />`;
    }});
  }}

  // Scene nodes
  scenes.forEach((s, idx) => {{
    const [px, py] = pts[idx];
    const isAct = idx === currentIndex;
    const fill = viewMode === "affect"
      ? valenceColor(s.valence)
      : (isAct ? "#facc15" : (viewMode === "historical" ? "#f5d08a" : "#38bdf8"));
    const r = isAct ? 9 : 5.5;
    if (isAct) {{
      out += `<circle cx="${{px.toFixed(1)}}" cy="${{py.toFixed(1)}}" r="17" fill="none" stroke="#facc15" stroke-width="2" opacity="0.7" />`;
    }}
    out += `<circle cx="${{px.toFixed(1)}}" cy="${{py.toFixed(1)}}" r="${{r}}" fill="${{fill}}" stroke="#0f1419" stroke-width="1.5" style="cursor:pointer" onclick="goToScene(${{idx}})" />`;
    out += `<text x="${{(px + 10).toFixed(1)}}" y="${{(py - 8).toFixed(1)}}" fill="${{isAct ? '#ffffff' : '#cbd5e1'}}" font-size="${{isAct ? 12 : 10}}" font-weight="${{isAct ? '700' : '400'}}">${{s.title}}</text>`;
  }});

  svg.innerHTML = out;
  document.getElementById("camera-hud").innerHTML =
    `<strong>Scene ${{currentIndex + 1}}/${{scenes.length}}</strong> · ${{active.map_scene_id}}<br/>` +
    `Shot: <strong>${{active.camera.shot_type}}</strong> · Zoom: ${{active.camera.zoom}} · Bearing: ${{active.camera.bearing}}° · Pitch: ${{active.camera.pitch}}°<br/>` +
    `Center: [${{active.camera.center[0].toFixed(3)}}, ${{active.camera.center[1].toFixed(3)}}] · View: ${{viewMode}}`;
}}

function renderScene() {{
  const s = scenes[currentIndex];
  const badge = document.getElementById("scene-badge");
  badge.textContent = s.evidence_level;
  badge.className = "badge " + s.evidence_level;

  document.getElementById("scene-time").textContent = formatInterval(s.when);
  document.getElementById("scene-shift").textContent = `· ${{s.temporal_shift}} / ${{s.transition}}`;
  document.getElementById("scene-title").textContent = s.title;
  document.getElementById("scene-heritage").textContent = s.heritage_element ? `遗产要素：${{s.heritage_element}}` : "";
  document.getElementById("scene-text").textContent = s.narrative_text;

  const evBox = document.getElementById("evidence-list");
  if (!s.evidence_ids || s.evidence_ids.length === 0) {{
    evBox.innerHTML = `<div class="ev-item"><em>Speculative narrative node (explicitly declared without primary citation).</em></div>`;
  }} else {{
    evBox.innerHTML = s.evidence_ids.map(eid => {{
      const ref = sources[eid] || {{ source_id: eid, label: eid }};
      const loc = ref.locator ? ` <span style="color:#93a4b5;">(${{ref.locator}})</span>` : "";
      const uri = ref.uri ? `<br/><a href="${{ref.uri}}" target="_blank" rel="noopener" style="color:#38bdf8;">${{ref.uri}}</a>` : "";
      return `<div class="ev-item"><code>${{ref.source_id}}</code> — ${{ref.label}}${{loc}}${{uri}}</div>`;
    }}).join("");
  }}

  document.getElementById("telemetry-box").innerHTML =
    `Unit ID: <code>${{s.narrative_unit_id}}</code> · Scale: ${{s.scale}} · Duration: ${{s.duration_sec}}s (${{s.pace}})<br/>` +
    `Shots: ${{s.shot_sequence.join(" → ")}}<br/>` +
    `Affect Valence: <strong>${{s.valence.toFixed(2)}}</strong> · Dominant Mood: <strong>${{s.dominant_mood}}</strong>`;

  const slider = document.getElementById("timeline-slider");
  slider.max = String(Math.max(0, scenes.length - 1));
  slider.value = String(currentIndex);
  document.getElementById("timeline-label").textContent = `${{currentIndex + 1}} / ${{scenes.length}} · ${{formatInterval(s.when)}}`;

  document.querySelectorAll(".pill").forEach((el, i) => el.classList.toggle("active", i === currentIndex));
  renderMap();
}}

function goToScene(idx) {{
  currentIndex = Math.max(0, Math.min(scenes.length - 1, idx));
  renderScene();
}}
function nextScene() {{ goToScene((currentIndex + 1) % scenes.length); }}
function prevScene() {{ goToScene((currentIndex - 1 + scenes.length) % scenes.length); }}
function togglePlay() {{
  const btn = document.getElementById("btn-play");
  if (playTimer) {{
    clearInterval(playTimer);
    playTimer = null;
    btn.textContent = "▶ 自动播放";
  }} else {{
    btn.textContent = "⏸ 暂停播放";
    playTimer = setInterval(nextScene, 3500);
  }}
}}

document.addEventListener("keydown", (e) => {{
  if (e.key === "ArrowRight") nextScene();
  if (e.key === "ArrowLeft") prevScene();
}});

// Build scene selector pills
const pills = document.getElementById("scene-pills");
scenes.forEach((s, idx) => {{
  const b = document.createElement("button");
  b.className = "pill";
  b.textContent = `${{idx + 1}}. ${{s.title}}`;
  b.onclick = () => goToScene(idx);
  pills.appendChild(b);
}});

renderScene();
</script>
</body>
</html>
"""
    if output_path is not None:
        out = pathlib.Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")
    return doc
