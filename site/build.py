"""Builds the static site for motanalysis.massmontagna.com from README.md and reports/figures/.

README.md is the only source of the page's words: edit it, then re-run this and commit site/dist/,
which Cloudflare Pages serves as it is (no build step there).

    python site/build.py
"""
import html
import re
import shutil
from pathlib import Path

import mistune

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
OUT = SITE / "dist"
URL = "https://motanalysis.massmontagna.com/"
REPO = "https://github.com/massmontagna/MOT-Data-Analysis"

body = mistune.html((ROOT / "README.md").read_text())

# The README's title becomes the page header; its link to this site is dropped from the page itself.
title_html, body = re.match(r"\s*<h1>(.*?)</h1>\s*(.*)", body, re.S).groups()
body = re.sub(rf'^<p>[^\n]*{re.escape(URL.rstrip("/"))}[^\n]*</p>\s*', "", body)
title = html.unescape(re.sub(r"<[^>]+>", "", title_html))
description = html.unescape(re.sub(r"<[^>]+>", "", re.search(r"<p>(.*?)</p>", body, re.S)[1]))

# Charts are served next to the page; every other relative link points at the file on GitHub.
body, figures = re.subn(r'src="reports/figures/', 'src="figures/', body)
assert figures == 8, f"expected 8 charts in README.md, found {figures}"
body = re.sub(r'href="(?!https?:|#|mailto:)([^"]+)"',
              lambda m: f'href="{REPO}/{"tree" if m[1].endswith("/") else "blob"}/main/{m[1]}"', body)
body = body.replace("<table>", '<div class="table"><table>').replace("</table>", "</table></div>")
assert not re.search(r'(?:href|src)="(?!https?:|#|mailto:|figures/)', body), "a relative link was left unconverted"

page = (SITE / "template.html").read_text().format(
    title=html.escape(title), description=html.escape(description, quote=True), url=URL, repo=REPO, content=body)

shutil.rmtree(OUT, ignore_errors=True)
shutil.copytree(ROOT / "reports" / "figures", OUT / "figures")
(OUT / "index.html").write_text(page)
print(f"Built {OUT / 'index.html'} with {figures} charts")
