#!/usr/bin/env python3
"""Validate an HTML file against the essentials of the HTML standard (exit 1 with problems listed).

  htmlcheck.py file.html [--fragment]
Full documents need doctype, lang, charset, viewport, title, one <main>, one <h1>; fragments/templates
(no <html> tag) are only checked for the element-level rules.
"""
import re, sys
from html.parser import HTMLParser


class Check(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.problems, self.ids, self.tags = [], {}, []
        self.doctype = self.lang = self.charset = self.viewport = self.title = False
        self.h1 = self.main = 0
        self.last_h = 0
        self.labels_for, self.inputs = set(), []
        self.in_label = 0
        self.stack = []

    def handle_decl(self, decl):
        if decl.lower().startswith("doctype html"):
            self.doctype = True

    def add(self, msg):
        self.problems.append(f"line {self.getpos()[0]}: {msg}")

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        self.tags.append(tag)
        if tag not in ("br", "img", "input", "meta", "link", "hr", "source", "area", "col", "embed", "wbr", "track", "base"):
            self.stack.append(tag)
        if tag == "a" and self.stack.count("a") > 1:
            self.add("<a> nested inside <a>")
        if tag == "html" and a.get("lang"):
            self.lang = True
        if tag == "meta" and ("charset" in a or a.get("http-equiv", "").lower() == "content-type"):
            self.charset = True
        if tag == "meta" and a.get("name") == "viewport":
            self.viewport = True
        if tag == "title":
            self.title = True
        if tag == "main":
            self.main += 1
        if re.fullmatch(r"h[1-6]", tag):
            level = int(tag[1])
            self.h1 += level == 1
            if self.last_h and level > self.last_h + 1:
                self.add(f"heading jumps from h{self.last_h} to h{level}")
            self.last_h = level
        if a.get("id"):
            if a["id"] in self.ids:
                self.add(f'duplicate id="{a["id"]}"')
            self.ids[a["id"]] = 1
        if tag == "img" and "alt" not in a:
            self.add(f'<img src="{a.get("src", "")[:40]}"> has no alt')
        if tag == "img" and not ("width" in a and "height" in a):
            self.add(f'<img src="{a.get("src", "")[:40]}"> missing width/height (causes layout shift)')
        if "style" in a:
            self.add(f"inline style on <{tag}>; move it to CSS")
        if any(k.startswith("on") for k in a):
            self.add(f"inline event handler on <{tag}>; attach it in JS")
        if tag == "a" and a.get("target") == "_blank" and "noopener" not in a.get("rel", ""):
            self.add('target="_blank" link without rel="noopener noreferrer"')
        if tag in ("div", "span") and ("onclick" in a or a.get("role") == "button") and tag != "button":
            self.add(f"clickable <{tag}>; use <button> or <a href>")
        if tag == "label":
            self.in_label += 1
            if a.get("for"):
                self.labels_for.add(a["for"])
        if tag in ("input", "select", "textarea") and a.get("type") not in ("hidden", "submit", "button", "reset", "image"):
            if not (self.in_label or a.get("aria-label") or a.get("aria-labelledby") or a.get("title")):
                self.inputs.append((self.getpos()[0], a.get("id"), tag))
        if tag == "script" and a.get("src") and "defer" not in a and "async" not in a and a.get("type") != "module" and "head" in self.stack:
            self.add(f'render-blocking <script src="{a["src"][:40]}"> in <head>; add defer')

    def handle_endtag(self, tag):
        if tag == "label":
            self.in_label = max(0, self.in_label - 1)
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass


def check(text):
    c = Check()
    c.feed(text)
    full = "html" in c.tags
    if full:
        for ok, msg in ((c.doctype, "missing <!doctype html>"), (c.lang, '<html> missing lang="..."'),
                        (c.charset, 'missing <meta charset="utf-8">'), (c.viewport, "missing viewport meta tag"),
                        (c.title, "missing <title>")):
            if not ok:
                c.problems.append(msg)
        if c.main != 1:
            c.problems.append(f"expected exactly one <main>, found {c.main}")
        if c.h1 != 1:
            c.problems.append(f"expected exactly one <h1>, found {c.h1}")
    for line, el_id, tag in c.inputs:
        if not el_id or el_id not in c.labels_for:
            c.problems.append(f"line {line}: <{tag}> has no label")
    return c.problems


if __name__ == "__main__":
    probs = check(open(sys.argv[1], encoding="utf-8", errors="replace").read())
    print("\n".join(probs) or "HTML OK")
    sys.exit(1 if probs else 0)
