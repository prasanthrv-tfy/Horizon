import math
import re

import markdown as md_lib

_URL_RE = re.compile(r'(?<!["\'>])(https?://[^\s<>"\']+)')

_CSS = """
  *, *::before, *::after { box-sizing: border-box; }

  body {
    margin: 0;
    padding: 0;
    background: #fff;
    color: #1a1a1a;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 17px;
    line-height: 1.65;
  }

  article {
    max-width: 720px;
    margin: 0 auto;
    padding: 2.5rem 2rem 4rem;
  }

  h1 {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.2;
    margin: 0 0 1.5rem;
    color: #111;
  }

  h2 {
    font-size: 1.35rem;
    font-weight: 600;
    margin: 2.25rem 0 0.75rem;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid #e0e0e0;
    color: #111;
  }

  h3 {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 1.75rem 0 0.5rem;
    color: #222;
  }

  p { margin: 0 0 1rem; }

  a { color: #0066cc; text-decoration: none; }
  a:hover { text-decoration: underline; }

  code {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 0.875em;
    background: #f3f3f3;
    border-radius: 3px;
    padding: 0.15em 0.35em;
  }

  pre {
    background: #f6f6f6;
    border: 1px solid #e0e0e0;
    border-radius: 5px;
    padding: 1rem;
    overflow-x: auto;
    margin: 1rem 0;
  }
  pre code {
    background: none;
    padding: 0;
    font-size: 0.85em;
  }

  blockquote {
    margin: 1.25rem 0;
    padding: 0.5rem 1rem;
    border-left: 3px solid #ccc;
    color: #555;
    font-style: italic;
  }
  blockquote p { margin: 0; }

  ul, ol {
    margin: 0.5rem 0 1rem;
    padding-left: 1.75rem;
  }
  li { margin-bottom: 0.3rem; }

  hr {
    border: none;
    border-top: 1px solid #e0e0e0;
    margin: 2rem 0;
  }

  details {
    border: 1px solid #e0e0e0;
    border-radius: 5px;
    padding: 0.5rem 1rem;
    margin: 1rem 0;
  }
  summary {
    cursor: pointer;
    font-weight: 600;
    color: #333;
    list-style: none;
  }
  summary::-webkit-details-marker { display: none; }
  summary::before { content: "▶ "; font-size: 0.75em; }
  details[open] summary::before { content: "▼ "; }

  @media print {
    body { font-size: 11pt; }
    article { max-width: 100%; padding: 0; }
    h1 { font-size: 20pt; }
    h2 { font-size: 14pt; }
    a { color: #000; }
    a[href]::after { content: " (" attr(href) ")"; font-size: 0.8em; color: #555; }
    details { border: 1px solid #ccc; }
  }
"""


def convert_markdown(text: str) -> str:
    """Convert Markdown to rich HTML using the 'extra' extension bundle."""
    html = md_lib.markdown(text, extensions=["extra"])
    return _URL_RE.sub(r'<a href="\1">\1</a>', html)


def reading_time(text: str) -> str:
    """Estimate reading time from character count. Returns 'N min read'.

    1000 chars/min is a conservative lower-bound for technical content (typical skimming
    speed is ~1300–1500). The intentional underestimate shows longer times rather than shorter.
    """
    minutes = math.ceil(len(text) / 1000)
    return f"{max(1, minutes)} min read"


def wrap_html(post: dict) -> str:
    """Wrap a bare HTML fragment in a complete document with charset and styling."""
    title = post.get("title", "")
    body = post.get("html", "")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{_CSS}</style>
</head>
<body>
<article>
<h1>{title}</h1>
{body}
</article>
</body>
</html>"""
