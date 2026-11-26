"""D3-P6: Zero-backend static HTML human-in-the-loop review workbench generator."""

from __future__ import annotations

import html
import json
import pathlib

from .provenance import ProvenanceLedger


def generate_review_html(
    ledger: ProvenanceLedger,
    *,
    title: str = "Platial-HGIS — AI vs. Human Verified Review Workbench",
    output_path: str | pathlib.Path | None = None,
) -> str:
    """Generate a lightweight offline HTML workbench for reviewing AI vs. Human Verified stamps."""
    records_json = json.dumps(
        [r.to_dict() for r in ledger.all_records()],
        ensure_ascii=False,
    ).replace("</", "<\\/")
    stats = ledger.summary_stats()
    title_esc = html.escape(title)

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title_esc}</title>
<style>
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif;
    background: #0f1419;
    color: #e6edf3;
    padding: 20px;
  }}
  header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
    border-bottom: 1px solid #283440;
    padding-bottom: 14px;
    margin-bottom: 18px;
  }}
  h1 {{ margin: 0; font-size: 1.2rem; }}
  .stats {{ font-size: 0.86rem; color: #93a4b5; }}
  .toolbar {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }}
  button {{
    background: #1e2935;
    color: #e6edf3;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 12px;
    cursor: pointer;
    font-size: 0.84rem;
  }}
  button.active {{ background: #38bdf8; color: #081018; font-weight: 600; border-color: #38bdf8; }}
  table {{ width: 100%; border-collapse: collapse; background: #171f27; border-radius: 8px; overflow: hidden; }}
  th, td {{ padding: 10px 12px; border-bottom: 1px solid #283440; text-align: left; font-size: 0.86rem; vertical-align: top; }}
  th {{ background: #121920; color: #93a4b5; font-weight: 600; }}
  .badge {{ padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; display: inline-block; }}
  .badge.hv {{ background: rgba(34,197,94,0.18); color: #22c55e; border: 1px solid #22c55e; }}
  .badge.ai {{ background: rgba(245,158,11,0.18); color: #f59e0b; border: 1px solid #f59e0b; }}
  .rev-list {{ font-size: 0.78rem; color: #93a4b5; margin-top: 4px; }}
  code {{ color: #7dd3fc; font-size: 0.78rem; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>{title_esc}</h1>
    <div class="stats" id="stats-bar">Total: {stats['total']} · Human Verified: {stats['human_verified']} · AI Pending: {stats['ai_pending']}</div>
  </div>
  <div>
    <button onclick="exportDecisions()">⬇ 导出人工核验 JSON</button>
  </div>
</header>

<div class="toolbar">
  <button id="f-all" class="active" onclick="setFilter('all')">全部 ({stats['total']})</button>
  <button id="f-hv" onclick="setFilter('hv')">✓ Human Verified ({stats['human_verified']})</button>
  <button id="f-ai" onclick="setFilter('ai')">AI 待复核 ({stats['ai_pending']})</button>
</div>

<table>
  <thead>
    <tr>
      <th>ID / 类型</th>
      <th>提取文本 &amp; 规范地名</th>
      <th>空间锚点 (Spatial Anchor)</th>
      <th>双轨状态 (AI vs. Human Verified)</th>
      <th>修订历史与 SHA-256 签章</th>
      <th>快捷核验</th>
    </tr>
  </thead>
  <tbody id="rows"></tbody>
</table>

<script>
const RECORDS = {records_json};
let filterMode = "all";

function setFilter(mode) {{
  filterMode = mode;
  for (const m of ["all", "hv", "ai"]) {{
    document.getElementById("f-" + m).classList.toggle("active", m === mode);
  }}
  render();
}}

function markChecked(idx) {{
  const reviewer = prompt("输入核验人标识 (assessment_by):", "human-reviewer");
  if (!reviewer) return;
  RECORDS[idx].verification_status = "Human Verified";
  RECORDS[idx].assessment_checked = true;
  RECORDS[idx].assessment_by = reviewer;
  render();
}}

function exportDecisions() {{
  const blob = new Blob([JSON.stringify({{ records: RECORDS }}, null, 2)], {{ type: "application/json" }});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "platial-review-decisions.json";
  a.click();
}}

function render() {{
  const tbody = document.getElementById("rows");
  const filtered = RECORDS.map((r, i) => [r, i]).filter(([r]) => {{
    const isHv = r.verification_status === "Human Verified" && r.assessment_checked;
    if (filterMode === "hv") return isHv;
    if (filterMode === "ai") return !isHv;
    return true;
  }});

  tbody.innerHTML = filtered.map(([r, i]) => {{
    const isHv = r.verification_status === "Human Verified" && r.assessment_checked;
    const badge = isHv
      ? `<span class="badge hv">✓ Human Verified</span><br/><small>by ${{r.assessment_by || ""}}</small>`
      : `<span class="badge ai">AI (${{r.source}})</span><br/><small>conf=${{(r.confidence || 0).toFixed(2)}}</small>`;
    const anchor = r.spatial_anchor
      ? `<code>${{r.spatial_anchor.canvas_id}}</code><br/>xy=(${{r.spatial_anchor.canvas_xy.join(", ")}})${{r.spatial_anchor.geotag_uri ? `<br/>URI: <code>${{r.spatial_anchor.geotag_uri}}</code>` : ""}}`
      : "—";
    const revs = (r.revisions || []).map(rv =>
      `<div>#${{rv.revision_no}} [${{rv.action}}] ${{rv.actor}}: ${{rv.summary}} <code>${{rv.stamp_sha256.slice(0,12)}}…</code></div>`
    ).join("");
    return `<tr>
      <td><code>${{r.annotation_id}}</code><br/><small>${{r.annotation_type}}</small></td>
      <td><strong>${{r.extracted_text}}</strong><br/><small>规范名: ${{r.normalized_toponym || "—"}}</small><br/><small>${{r.source_citation || ""}}</small></td>
      <td>${{anchor}}</td>
      <td>${{badge}}</td>
      <td><div class="rev-list">${{revs}}</div></td>
      <td>${{isHv ? "已签章" : `<button onclick="markChecked(${{i}})">✓ 签章核验</button>`}}</td>
    </tr>`;
  }}).join("");
}}

render();
</script>
</body>
</html>
"""
    if output_path is not None:
        out = pathlib.Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")
    return doc
