"""Check that every link in the README and docs opens.

Relative links: the file must exist, and any #anchor must match a heading in it.
Web links: only checked with --web (needs internet; the demo itself runs offline).

    python3 -m tools.check_links          # files and anchors only
    python3 -m tools.check_links --web    # also fetch every http(s) link
"""
import argparse
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import unquote, urldefrag

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [ROOT/'README.md', ROOT/'README-sim-v5.md', *sorted((ROOT/'docs').glob('*.md'))]
LINK = re.compile(r'(?<!\!)\[[^\]]*\]\(([^)\s]+)\)|(?<=\])\(\s*(<[^>]+>)\s*\)')
FENCE = re.compile(r'^```.*?^```', re.S | re.M)


def slug(heading):
    """GitHub's anchor for a heading: lowercase, drop punctuation, spaces to dashes."""
    text = re.sub(r'[`*_]|\[([^\]]*)\]\([^)]*\)', r'\1', heading).strip().lower()
    return re.sub(r'\s', '-', re.sub(r'[^\w\s-]', '', text))


def anchors(path):
    found, seen = set(), {}
    for line in FENCE.sub('', path.read_text(errors='replace')).splitlines():
        m = re.match(r'#{1,6}\s+(.*)', line)
        if m:
            base = slug(m.group(1))
            n = seen.get(base, 0)
            seen[base] = n + 1
            found.add(base if n == 0 else f'{base}-{n}')
    return found


def web_ok(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'link-check'})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status < 400, str(r.status)
    except urllib.error.HTTPError as e:
        return False, str(e.code)
    except Exception as e:  # DNS failure, timeout, offline
        return False, type(e).__name__


def find_broken(web=False):
    """Return (links checked, list of broken-link descriptions)."""
    bad, checked, cache = [], 0, {}
    for src in SOURCES:
        text = FENCE.sub('', src.read_text(errors='replace'))
        for m in LINK.finditer(text):
            target = (m.group(1) or m.group(2)).strip('<>')
            if target.startswith(('mailto:', 'tel:')):
                continue
            checked += 1
            where = f'{src.relative_to(ROOT)}: {target}'
            if target.startswith(('http://', 'https://')):
                if web:
                    cache.setdefault(target, web_ok(target))
                    ok, why = cache[target]
                    if not ok:
                        bad.append(f'{where}  ({why})')
                continue
            path, frag = urldefrag(unquote(target))
            dest = (src.parent/path).resolve() if path else src
            if not dest.exists():
                bad.append(f'{where}  (file not found)')
            elif frag and dest.suffix == '.md' and slug(frag) not in anchors(dest):
                bad.append(f'{where}  (no heading "{frag}" in {dest.relative_to(ROOT)})')
    return checked, bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--web', action='store_true', help='also fetch http(s) links')
    checked, bad = find_broken(ap.parse_args().web)
    print(f'checked {checked} links in {len(SOURCES)} files')
    for line in bad:
        print('BROKEN', line)
    print('all links open' if not bad else f'{len(bad)} broken')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
