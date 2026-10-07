#!/usr/bin/env python3
"""Visual regression check: screenshot pages before and after a change and report what changed.

Static sites (HTML files in the repo): "before" is the last commit (HEAD), "after" is the working
tree, so no baselines need to be stored.
Apps with a dev server: list URLs in .claude/visual/pages.json, e.g.
  {"url": "http://localhost:5173", "pages": ["/", "/login", "/cart"]}
and baselines are kept in .claude/visual/baseline/ (accept new looks with `visual.py accept`).

  visual.py check     compare; exit 1 and print changed pages + diff image paths if any
  visual.py accept    store current screenshots as the new baselines (server apps)
Needs Chrome/Chromium (auto-found, or set CLAUDE_CHROME) and Pillow for pixel diffs.
"""
import glob, json, os, shutil, subprocess, sys, tempfile

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
VIS = os.path.join(ROOT, ".claude", "visual")
OUT = os.path.join(tempfile.gettempdir(), "claude-visual")
THRESHOLD = float(os.environ.get("CLAUDE_VISUAL_THRESHOLD", "0.02"))  # % of pixels
SIZE = (1280, 2000)
SKIP = {"node_modules", ".git", "dist", "build", ".venv", "venv", "coverage", ".claude"}


def chrome():
    cands = [os.environ.get("CLAUDE_CHROME", "")]
    cands += sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"), reverse=True)
    cands += [shutil.which(n) or "" for n in ("chromium", "chromium-browser", "google-chrome", "chrome")]
    cands += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]
    return next((c for c in cands if c and os.path.exists(c)), None)


def shoot(url, out_png):
    exe = chrome()
    if not exe:
        return False
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=1", f"--window-size={SIZE[0]},{SIZE[1]}",
                    "--virtual-time-budget=3000", f"--screenshot={out_png}", url],
                   capture_output=True, timeout=60)
    return os.path.exists(out_png)


def diff(a, b, out_png):
    """Percent of pixels that differ; writes a highlighted diff image."""
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return 0.0 if open(a, "rb").read() == open(b, "rb").read() else 100.0
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        ib = ib.resize(ia.size)
    d = ImageChops.difference(ia, ib).convert("L").point(lambda v: 255 if v > 24 else 0)
    changed = d.histogram()[255]
    if changed:
        red = Image.new("RGB", ia.size, (255, 0, 0))
        Image.composite(red, ia.point(lambda v: v // 2 + 64), d).save(out_png)
    return 100.0 * changed / (ia.size[0] * ia.size[1])


def html_pages(root):
    for dp, dirs, fs in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".")]
        for f in fs:
            if f.endswith((".html", ".htm")):
                yield os.path.relpath(os.path.join(dp, f), root)


def affected_pages(changed):
    """HTML pages that are themselves changed or load a changed file. None = can't tell, check all."""
    if not changed:
        return None
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from linkcheck import parse, resolve
    changed = {os.path.normpath(os.path.join(ROOT, c)) for c in changed}
    pages, used = set(), set()
    for page in html_pages(ROOT):
        full = os.path.join(ROOT, page)
        deps = {full} | {resolve(ROOT, full, link)[0] for link in parse(full).resources} - {None}
        used |= deps
        if deps & changed:
            pages.add(page)
    if changed - used:  # a changed UI file no page links directly (e.g. a JS component): check all
        return None
    return pages


def check_static(changed=None):
    """Compare HEAD vs working tree for affected HTML pages. Returns list of result tuples."""
    only = affected_pages(changed)
    head = tempfile.mkdtemp(prefix="claude-visual-head-")
    try:
        archive = subprocess.run(["git", "archive", "HEAD"], cwd=ROOT, capture_output=True, timeout=60)
        if archive.returncode:
            return []
        subprocess.run(["tar", "-x", "-C", head], input=archive.stdout, timeout=60)
        results = []
        for page in html_pages(ROOT):
            if only is not None and page not in only:
                continue
            if not os.path.exists(os.path.join(head, page)):
                continue  # new page: nothing to compare against
            name = page.replace(os.sep, "_")
            before, after = os.path.join(OUT, "before", name + ".png"), os.path.join(OUT, "after", name + ".png")
            for p in (before, after):
                if os.path.exists(p):
                    os.remove(p)
            if not (shoot("file://" + os.path.join(head, page), before) and
                    shoot("file://" + os.path.join(ROOT, page), after)):
                continue
            out = os.path.join(OUT, "diff", name + ".png")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            pct = diff(before, after, out)
            if pct > THRESHOLD:
                results.append((page, pct, out, before, after))
        return results
    finally:
        shutil.rmtree(head, ignore_errors=True)


def server_config():
    try:
        return json.load(open(os.path.join(VIS, "pages.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return None


def check_server(cfg, accept=False):
    results = []
    for page in cfg.get("pages", ["/"]):
        name = (page.strip("/") or "home").replace("/", "_")
        base = os.path.join(VIS, "baseline", name + ".png")
        now = os.path.join(OUT, "after", name + ".png")
        if os.path.exists(now):
            os.remove(now)
        if not shoot(cfg["url"].rstrip("/") + page, now):
            continue
        if accept or not os.path.exists(base):
            os.makedirs(os.path.dirname(base), exist_ok=True)
            shutil.copy(now, base)
            continue
        out = os.path.join(OUT, "diff", name + ".png")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        pct = diff(base, now, out)
        if pct > THRESHOLD:
            results.append((page, pct, out, base, now))
    return results


def report(results):
    lines = [f"{page}: {pct:.1f}% of the page changed. Diff (changes in red): {d}  before: {b}  after: {a}"
             for page, pct, d, b, a in results]
    return "\n".join(lines)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if not chrome():
        sys.exit(print("no Chrome/Chromium found; set CLAUDE_CHROME to enable visual checks") or 0)
    cfg = server_config()
    if cmd == "accept":
        if cfg:
            check_server(cfg, accept=True)
        print("baselines updated" if cfg else "static sites compare against the last commit; nothing to accept")
    else:
        res = check_server(cfg) if cfg else check_static()
        print(report(res) or "no visual changes")
        sys.exit(1 if res else 0)
