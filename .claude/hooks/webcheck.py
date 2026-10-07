"""Web quality checks: CSS colour contrast (WCAG 2.2 AA) and page weight (Core Web Vitals hygiene)."""
import os, re
from html.parser import HTMLParser

NAMED = {"black": "#000000", "white": "#ffffff", "red": "#ff0000", "green": "#008000", "blue": "#0000ff",
         "gray": "#808080", "grey": "#808080", "silver": "#c0c0c0", "yellow": "#ffff00", "orange": "#ffa500",
         "navy": "#000080", "teal": "#008080", "purple": "#800080", "maroon": "#800000", "lightgray": "#d3d3d3",
         "lightgrey": "#d3d3d3", "darkgray": "#a9a9a9", "whitesmoke": "#f5f5f5", "gold": "#ffd700", "pink": "#ffc0cb"}
IMG_MAX_KB = int(os.environ.get("CLAUDE_IMG_MAX_KB", "300"))
PAGE_MAX_KB = int(os.environ.get("CLAUDE_PAGE_MAX_KB", "2000"))


def rgb(value, variables):
    v = value.strip().lower()
    for _ in range(5):
        m = re.fullmatch(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^)]+))?\)", v)
        if not m:
            break
        v = variables.get(m.group(1), m.group(2) or "").strip().lower()
    v = NAMED.get(v, v)
    m = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", v)
    if m:
        h = m.group(1)
        h = "".join(c * 2 for c in h) if len(h) == 3 else h
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = re.fullmatch(r"rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)\s*(?:[,/]\s*([\d.]+%?))?\s*\)", v)
    if m and (m.group(4) is None or m.group(4) in ("1", "100%")):
        return tuple(int(m.group(i)) for i in (1, 2, 3))
    return None  # gradients, transparency, currentColor: can't judge statically


def luminance(c):
    def ch(x):
        x /= 255
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def contrast(css):
    """Problems for rules that set both text colour and background with contrast below 4.5:1."""
    text = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    variables = dict(re.findall(r"(--[\w-]+)\s*:\s*([^;}]+)", text))
    out = []
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
        sel, body = m.group(1).strip(), m.group(2)
        decl = dict((k.strip().lower(), v.strip()) for k, v in re.findall(r"([\w-]+)\s*:\s*([^;]+)", body))
        fg = decl.get("color")
        bg = decl.get("background-color") or decl.get("background")
        if not (fg and bg):
            continue
        a, b = rgb(fg, variables), rgb(bg.split()[0] if bg.startswith("#") else bg, variables)
        if a and b:
            r = ratio(a, b)
            large = re.search(r"\bh[1-3]\b", sel) is not None
            need = 3.0 if large else 4.5
            if r < need:
                line = css.count("\n", 0, m.start()) + 1
                out.append((line, f"`{sel[:40]}` text contrast {r:.1f}:1 (needs {need}:1, WCAG 2.2 AA)"))
    return out


class Res(HTMLParser):
    def __init__(self):
        super().__init__()
        self.res = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("img", "script", "source", "video", "audio") and a.get("src"):
            self.res.append((self.getpos()[0], tag, a["src"]))
        if tag == "link" and a.get("href") and "stylesheet" in (a.get("rel") or ""):
            self.res.append((self.getpos()[0], tag, a["href"]))


def page_weight(path, html):
    p = Res()
    p.feed(html)
    out, total = [], os.path.getsize(path)
    for line, tag, src in p.res:
        if re.match(r"[a-z]+:|//", src):
            continue
        f = os.path.normpath(os.path.join(os.path.dirname(path), src.split("?")[0].split("#")[0]))
        if not os.path.isfile(f):
            continue
        kb = os.path.getsize(f) // 1024
        total += kb * 1024
        if tag in ("img", "source") and kb > IMG_MAX_KB and not f.endswith(".svg"):
            out.append((line, f"image {src} is {kb} KB (max {IMG_MAX_KB}); compress or convert to webp/avif"))
    if total // 1024 > PAGE_MAX_KB:
        out.append((1, f"page loads {total // 1024} KB of local files (max {PAGE_MAX_KB}); slim it down"))
    return out
