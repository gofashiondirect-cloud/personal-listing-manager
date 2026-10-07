#!/usr/bin/env python3
"""Check a project's HTML files for broken internal links, missing #anchors and redirect loops.

  linkcheck.py [root]     prints problems; exit 1 if any
Only local targets are checked (http(s), mailto, tel and javascript links are skipped).
"""
import os, re, sys
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse

SKIP = {"node_modules", ".git", "dist", "build", ".venv", "venv", "coverage", ".claude"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.refresh, self.resources = [], set(), None, []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("name"):
            self.ids.add(a["name"])
        for attr in ("href", "src"):
            if a.get(attr) and tag in ("a", "link", "script", "img", "source", "iframe", "video", "audio"):
                self.links.append((self.getpos()[0], a[attr]))
                if tag != "a":
                    self.resources.append(a[attr])  # things that change how this page looks
        if tag == "meta" and (a.get("http-equiv") or "").lower() == "refresh":
            m = re.search(r"url\s*=\s*['\"]?([^'\";]+)", a.get("content") or "", re.I)
            if m:
                self.refresh = m.group(1).strip()


def html_files(root):
    for dp, dirs, fs in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".")]
        for f in fs:
            if f.endswith((".html", ".htm")):
                yield os.path.join(dp, f)


def parse(path):
    p = Page()
    try:
        p.feed(open(path, encoding="utf-8", errors="replace").read())
    except Exception:
        pass
    return p


def resolve(root, src, link):
    u = urlparse(link)
    if u.scheme or link.startswith(("//", "#")) and not link.startswith("#"):
        return None, None
    if link.startswith("#"):
        return src, unquote(u.fragment)
    base = root if u.path.startswith("/") else os.path.dirname(src)
    target = os.path.normpath(os.path.join(base, unquote(u.path).lstrip("/")))
    if os.path.isdir(target):
        target = os.path.join(target, "index.html")
    return target, unquote(u.fragment)


def check(root):
    pages = {p: parse(p) for p in html_files(root)}
    problems = []
    for src, page in pages.items():
        rel_src = os.path.relpath(src, root)
        for line, link in page.links:
            if link.startswith(("mailto:", "tel:", "javascript:", "data:")) or "{{" in link or "${" in link:
                continue
            target, frag = resolve(root, src, link)
            if target is None:
                continue
            if not os.path.exists(target):
                problems.append(f"{rel_src}:{line} broken link -> {link}")
            elif frag and target.endswith((".html", ".htm")):
                ids = (pages.get(target) or parse(target)).ids
                if frag not in ids:
                    problems.append(f"{rel_src}:{line} missing anchor -> {link}")
    for start, page in pages.items():  # meta-refresh redirect loops
        seen, cur = [start], page
        while cur and cur.refresh:
            nxt, _ = resolve(root, seen[-1], cur.refresh)
            if not nxt:
                break
            if nxt in seen:
                problems.append("redirect loop: " + " -> ".join(os.path.relpath(p, root) for p in seen + [nxt]))
                break
            seen.append(nxt)
            cur = pages.get(nxt)
    return sorted(set(problems))


if __name__ == "__main__":
    found = check(os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "."))
    print("\n".join(found) or "no broken links")
    sys.exit(1 if found else 0)
