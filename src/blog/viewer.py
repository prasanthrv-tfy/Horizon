"""Generate a self-contained HTML viewer for blog posts in artifacts/blog-posts/."""

import json
from pathlib import Path
from typing import Optional


def generate_results_html(output_dir: Path, model: Optional[str] = None) -> Path:
    """Scan output_dir for profile subdirs, embed all posts, write results.html."""
    output_dir.mkdir(parents=True, exist_ok=True)
    posts = []
    for profile_dir in sorted(output_dir.iterdir()):
        if not profile_dir.is_dir():
            continue
        manifest_path = profile_dir / "posts.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest:
            md_path = profile_dir / entry["filename"]
            markdown_body = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
            posts.append({
                "title": entry.get("title", ""),
                "profile": entry.get("profile", profile_dir.name),
                "score": entry.get("score", 0),
                "tags": entry.get("tags", []),
                "url": entry.get("url", ""),
                "language": entry.get("language", "en"),
                "inclusion_path": entry.get("inclusion_path"),
                "dimensions": entry.get("dimensions", {}),
                "markdown": markdown_body,
            })

    if not posts:
        html_path = output_dir / "results.html"
        html_path.write_text(_empty_html(), encoding="utf-8")
        return html_path

    posts_json = json.dumps(posts, ensure_ascii=False)
    profiles = sorted({p["profile"] for p in posts})
    model_label = model or "unknown model"
    html = _render_html(posts_json, profiles, model_label)
    html_path = output_dir / "results.html"
    html_path.write_text(html, encoding="utf-8")
    return html_path


def _empty_html() -> str:
    return "<!DOCTYPE html><html><body><p>No blog posts found.</p></body></html>"


def _render_html(posts_json: str, profiles: list[str], model_label: str) -> str:
    profile_options = '<option value="all">All profiles</option>\n'
    for p in profiles:
        profile_options += f'        <option value="{p}">{p}</option>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Horizon Blog Posts</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; height: 100vh; display: flex; flex-direction: column; background: #f5f5f5; color: #1a1a1a; }}
  #header {{ background: #1a1a2e; color: #e0e0e0; padding: 10px 16px; display: flex; align-items: center; gap: 12px; flex-shrink: 0; border-bottom: 2px solid #16213e; }}
  #header h1 {{ font-size: 15px; font-weight: 600; color: #fff; }}
  #header .meta {{ font-size: 12px; color: #9090b0; margin-left: auto; }}
  #main {{ display: flex; flex: 1; overflow: hidden; }}
  #sidebar {{ width: 300px; background: #fff; border-right: 1px solid #e0e0e0; display: flex; flex-direction: column; flex-shrink: 0; overflow: hidden; }}
  #sidebar-controls {{ padding: 10px 12px; border-bottom: 1px solid #eee; background: #fafafa; }}
  #sidebar-controls label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #888; display: block; margin-bottom: 4px; }}
  #profile-select {{ width: 100%; padding: 5px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; background: #fff; cursor: pointer; }}
  #post-count {{ font-size: 11px; color: #999; margin-top: 6px; }}
  #post-list {{ overflow-y: auto; flex: 1; }}
  .post-item {{ padding: 10px 12px; cursor: pointer; border-bottom: 1px solid #f0f0f0; transition: background 0.1s; }}
  .post-item:hover {{ background: #f0f4ff; }}
  .post-item.active {{ background: #e8f0fe; border-left: 3px solid #4a7cf8; padding-left: 9px; }}
  .post-title {{ font-size: 13px; font-weight: 500; line-height: 1.35; color: #1a1a1a; margin-bottom: 4px; }}
  .post-meta {{ display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }}
  .badge-profile {{ font-size: 10px; background: #e8f0fe; color: #4a7cf8; border-radius: 3px; padding: 1px 5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }}
  .badge-score {{ font-size: 10px; background: #e8faf0; color: #2a9d5c; border-radius: 3px; padding: 1px 5px; font-weight: 600; }}
  .badge-lang {{ font-size: 10px; background: #f3f0ff; color: #7c4dff; border-radius: 3px; padding: 1px 5px; }}
  #content-pane {{ flex: 1; overflow-y: auto; padding: 28px 36px; background: #fff; }}
  #content-pane.empty {{ display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 15px; }}
  #post-header {{ margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #eee; }}
  #post-header h2 {{ font-size: 22px; font-weight: 700; line-height: 1.3; color: #1a1a1a; margin-bottom: 10px; }}
  #post-header-meta {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
  #post-header-meta a {{ font-size: 12px; color: #4a7cf8; text-decoration: none; }}
  #post-header-meta a:hover {{ text-decoration: underline; }}
  .tag {{ font-size: 11px; background: #f0f0f0; color: #555; border-radius: 3px; padding: 2px 7px; }}
  #post-body {{ font-size: 15px; line-height: 1.7; color: #2a2a2a; max-width: 780px; }}
  #post-body h1 {{ font-size: 22px; font-weight: 700; margin: 24px 0 12px; }}
  #post-body h2 {{ font-size: 18px; font-weight: 600; margin: 22px 0 10px; color: #1a1a2e; }}
  #post-body h3 {{ font-size: 15px; font-weight: 600; margin: 18px 0 8px; }}
  #post-body p {{ margin: 0 0 14px; }}
  #post-body ul, #post-body ol {{ margin: 0 0 14px 20px; }}
  #post-body li {{ margin-bottom: 4px; }}
  #post-body a {{ color: #4a7cf8; text-decoration: none; }}
  #post-body a:hover {{ text-decoration: underline; }}
  #post-body code {{ background: #f3f4f6; padding: 1px 5px; border-radius: 3px; font-size: 13px; font-family: "SF Mono", "Fira Code", monospace; }}
  #post-body pre {{ background: #f3f4f6; padding: 14px 16px; border-radius: 6px; overflow-x: auto; margin: 0 0 14px; }}
  #post-body pre code {{ background: none; padding: 0; }}
  #post-body blockquote {{ border-left: 3px solid #ddd; padding-left: 14px; color: #666; margin: 0 0 14px; }}
  #post-body hr {{ border: none; border-top: 1px solid #eee; margin: 20px 0; }}
  .scoring-section {{ margin-top: 14px; padding: 12px 14px; background: #f8f9fc; border: 1px solid #e8ebf4; border-radius: 6px; max-width: 780px; }}
  .scoring-section .gate-label {{ font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; color: #4a7cf8; margin-bottom: 10px; }}
  .dim-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 12px; }}
  .dim-name {{ width: 220px; flex-shrink: 0; color: #444; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .dim-bar-wrap {{ flex: 1; background: #e4e8f0; border-radius: 3px; height: 6px; overflow: hidden; }}
  .dim-bar {{ height: 100%; border-radius: 3px; background: #4a7cf8; }}
  .dim-score {{ width: 22px; text-align: right; font-weight: 600; color: #333; flex-shrink: 0; }}
</style>
</head>
<body>
<div id="header">
  <h1>Horizon Blog Posts</h1>
  <span class="meta">model: {model_label}</span>
</div>
<div id="main">
  <div id="sidebar">
    <div id="sidebar-controls">
      <label>Profile</label>
      <select id="profile-select" onchange="filterPosts()">
        {profile_options}      </select>
      <div id="post-count"></div>
    </div>
    <div id="post-list"></div>
  </div>
  <div id="content-pane">
    <p style="color:#aaa;font-size:15px;margin:auto;padding-top:80px;text-align:center;">Select a post from the sidebar</p>
  </div>
</div>
<script>
const POSTS = {posts_json};

let activeIndex = null;
let visibleIndices = [];

function filterPosts() {{
  const profile = document.getElementById('profile-select').value;
  visibleIndices = POSTS
    .map((p, i) => [p, i])
    .filter(([p]) => profile === 'all' || p.profile === profile)
    .map(([, i]) => i);
  renderList();
}}

function renderList() {{
  const list = document.getElementById('post-list');
  list.innerHTML = '';
  visibleIndices.forEach(i => {{
    const p = POSTS[i];
    const div = document.createElement('div');
    div.className = 'post-item' + (i === activeIndex ? ' active' : '');
    div.onclick = () => loadPost(i);
    div.innerHTML = `
      <div class="post-title">${{p.title}}</div>
      <div class="post-meta">
        <span class="badge-profile">${{p.profile}}</span>
        <span class="badge-score">★ ${{p.score.toFixed(1)}}</span>
        ${{p.language !== 'en' ? `<span class="badge-lang">${{p.language}}</span>` : ''}}
      </div>`;
    list.appendChild(div);
  }});
  document.getElementById('post-count').textContent = visibleIndices.length + ' post' + (visibleIndices.length !== 1 ? 's' : '');
}}

function buildScoringHtml(p) {{
  const dims = p.dimensions || {{}};
  const keys = Object.keys(dims);
  if (!keys.length && !p.inclusion_path) return '';

  let rows = keys.map(name => {{
    const d = dims[name];
    const score = d.score ?? 0;
    const pct = (score / 10) * 100;
    const label = name.replace(/_/g, ' ');
    return `<div class="dim-row">
      <span class="dim-name" title="${{name}}">${{label}}</span>
      <div class="dim-bar-wrap"><div class="dim-bar" style="width:${{pct}}%"></div></div>
      <span class="dim-score">${{score}}</span>
    </div>`;
  }}).join('');

  const gateLabel = p.inclusion_path
    ? `<div class="gate-label">Gate: ${{p.inclusion_path}}</div>`
    : '';

  return `<div class="scoring-section">${{gateLabel}}${{rows}}</div>`;
}}

function loadPost(i) {{
  activeIndex = i;
  const p = POSTS[i];
  const pane = document.getElementById('content-pane');

  const tagsHtml = p.tags.map(t => `<span class="tag">${{t}}</span>`).join('');
  const sourceLink = p.url ? `<a href="${{p.url}}" target="_blank" rel="noopener">↗ original source</a>` : '';

  pane.innerHTML = `
    <div id="post-header">
      <h2>${{p.title}}</h2>
      <div id="post-header-meta">
        <span class="badge-profile">${{p.profile}}</span>
        <span class="badge-score">★ ${{p.score.toFixed(1)}}</span>
        ${{tagsHtml}}
        ${{sourceLink}}
      </div>
      ${{buildScoringHtml(p)}}
    </div>
    <div id="post-body"></div>`;

  const bodyEl = pane.querySelector('#post-body');
  if (typeof marked !== 'undefined') {{
    bodyEl.innerHTML = marked.parse(p.markdown);
  }} else {{
    bodyEl.textContent = p.markdown;
  }}

  renderList();
  pane.scrollTop = 0;
}}

filterPosts();
if (visibleIndices.length > 0) loadPost(visibleIndices[0]);
</script>
</body>
</html>"""
