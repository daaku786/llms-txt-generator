#!/usr/bin/env python3
"""Generate an llms.txt file (https://llmstxt.org) from a website's XML sitemap.

Reads the sitemap (sitemap index, plain sitemap or .xml.gz), fetches each page's
<title> and meta description, groups pages by their first URL folder and writes
Markdown in the llms.txt format:

    # Site name
    > One line summary
    ## Section
    - [Page title](https://example.com/page): description

No third-party dependencies. Python 3.8+.
"""

import argparse
import concurrent.futures
import fnmatch
import gzip
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape
from html.parser import HTMLParser

__version__ = "1.0.0"
UA = f"llms-txt-generator/{__version__} (+https://github.com/daaku786/llms-txt-generator)"
SM_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def fetch_bytes(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read(20_000_000)
        charset = resp.headers.get_content_charset()
    if url.endswith(".gz") or data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return data, charset


def find_sitemap(site):
    """Try robots.txt Sitemap: lines, then /sitemap_index.xml and /sitemap.xml."""
    origin = "{0.scheme}://{0.netloc}".format(urllib.parse.urlsplit(site))
    candidates = []
    try:
        robots, _ = fetch_bytes(origin + "/robots.txt")
        for line in robots.decode("utf-8", "replace").splitlines():
            if line.lower().startswith("sitemap:"):
                candidates.append(line.split(":", 1)[1].strip())
    except Exception:
        pass
    candidates += [origin + "/sitemap_index.xml", origin + "/sitemap.xml"]
    for url in candidates:
        try:
            fetch_bytes(url)
            return url
        except Exception:
            continue
    return None


def read_sitemap(url, limit, seen=None):
    """Return page URLs from a sitemap or sitemap index (recursive)."""
    seen = seen if seen is not None else set()
    if url in seen:
        return []
    seen.add(url)
    data, _ = fetch_bytes(url)
    root = ET.fromstring(data)
    tag = root.tag.replace(SM_NS, "")
    urls = []
    if tag == "sitemapindex":
        for loc in root.iter(SM_NS + "loc"):
            if len(urls) >= limit:
                break
            try:
                urls += read_sitemap(loc.text.strip(), limit - len(urls), seen)
            except Exception as e:
                print(f"  skip {loc.text.strip()}: {e}", file=sys.stderr)
    else:
        for loc in root.iter(SM_NS + "loc"):
            urls.append(loc.text.strip())
            if len(urls) >= limit:
                break
    return urls


class PageMeta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self.og_title = ""
        self.noindex = False
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = (a.get("name") or a.get("property") or "").lower()
            content = a.get("content", "").strip()
            if name == "description" and not self.description:
                self.description = content
            elif name == "og:description" and not self.description:
                self.description = content
            elif name == "og:title":
                self.og_title = content
            elif name == "robots" and "noindex" in content.lower():
                self.noindex = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def page_info(url):
    try:
        data, charset = fetch_bytes(url)
        p = PageMeta()
        p.feed(data.decode(charset or "utf-8", "replace"))
        title = re.sub(r"\s+", " ", unescape(p.og_title or p.title)).strip()
        desc = re.sub(r"\s+", " ", unescape(p.description)).strip()
        return {"url": url, "title": title, "description": desc, "noindex": p.noindex, "error": None}
    except Exception as e:
        return {"url": url, "title": "", "description": "", "noindex": False, "error": str(e)}


def clean_title(title, site_name):
    """Drop a trailing ' | Site Name' / ' - Site Name' suffix."""
    if site_name:
        title = re.sub(r"\s*[|\-–—:]\s*" + re.escape(site_name) + r"\s*$", "", title, flags=re.I)
    return title.strip()


def section_for(url):
    path = urllib.parse.urlsplit(url).path.strip("/")
    if not path:
        return "Main"
    first = path.split("/")[0]
    if "/" not in path:
        return "Pages"
    return first.replace("-", " ").replace("_", " ").title()


def build_llms_txt(site_name, summary, pages, details=None, optional_sections=()):
    sections = {}
    for p in pages:
        sections.setdefault(section_for(p["url"]), []).append(p)
    order = ["Main", "Pages"] + sorted(s for s in sections if s not in ("Main", "Pages"))
    out = [f"# {site_name}", ""]
    if summary:
        out += [f"> {summary}", ""]
    if details:
        out += [details.strip(), ""]
    main = [s for s in order if s in sections and s not in optional_sections]
    optional = [s for s in order if s in sections and s in optional_sections]
    for name in main + optional:
        heading = "Optional" if name in optional_sections and len(optional) == 1 else name
        if name in optional_sections and len(optional) > 1:
            heading = f"Optional: {name}"
        out.append(f"## {heading}")
        out.append("")
        for p in sections[name]:
            title = p["title"] or urllib.parse.urlsplit(p["url"]).path or p["url"]
            line = f"- [{title}]({p['url']})"
            if p["description"]:
                line += f": {p['description']}"
            out.append(line)
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate llms.txt from a website's sitemap.")
    ap.add_argument("site", help="site URL, e.g. https://example.com")
    ap.add_argument("--sitemap", help="sitemap URL (default: auto detect from robots.txt)")
    ap.add_argument("--name", help="site name for the H1 (default: home page title)")
    ap.add_argument("--summary", help="one line summary (default: home page meta description)")
    ap.add_argument("--max-pages", type=int, default=200, help="max pages to include (default 200)")
    ap.add_argument("--exclude", action="append", default=[],
                    help="glob to skip, repeatable, e.g. --exclude '*/tag/*'")
    ap.add_argument("--optional", action="append", default=[],
                    help="section name to move under '## Optional', repeatable, e.g. --optional Blog")
    ap.add_argument("--workers", type=int, default=8, help="parallel requests (default 8)")
    ap.add_argument("-o", "--output", default="llms.txt", help="output file (default llms.txt, '-' for stdout)")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args(argv)

    site = args.site if "://" in args.site else "https://" + args.site
    sitemap = args.sitemap or find_sitemap(site)
    if not sitemap:
        print("No sitemap found. Pass one with --sitemap.", file=sys.stderr)
        return 1
    print(f"Sitemap: {sitemap}", file=sys.stderr)

    default_excludes = ["*/tag/*", "*/author/*", "*/page/[0-9]*", "*/feed/*", "*/wp-json/*"]
    excludes = default_excludes + args.exclude
    urls = [u for u in read_sitemap(sitemap, max(args.max_pages * 3, 5000))
            if not urllib.parse.urlsplit(u).query and not any(fnmatch.fnmatch(u, pat) for pat in excludes)]
    urls = list(dict.fromkeys(urls))
    # shallow URLs (home, main pages, hubs) first, so they are never cut by --max-pages
    urls.sort(key=lambda u: urllib.parse.urlsplit(u).path.strip("/").count("/"))
    urls = urls[: args.max_pages]
    print(f"Fetching {len(urls)} pages...", file=sys.stderr)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        pages = list(pool.map(page_info, urls))

    errors = [p for p in pages if p["error"]]
    noindex = [p for p in pages if p["noindex"]]
    pages = [p for p in pages if not p["error"] and not p["noindex"]]

    home = page_info(site.rstrip("/") + "/")
    site_name = args.name or clean_title(home["title"].split("|")[0].split(" - ")[0], "") or urllib.parse.urlsplit(site).netloc
    summary = args.summary if args.summary is not None else home["description"]
    for p in pages:
        p["title"] = clean_title(p["title"], site_name)

    text = build_llms_txt(site_name, summary, pages, optional_sections=set(args.optional))
    if args.output == "-":
        sys.stdout.write(text)
    else:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Wrote {args.output}: {len(pages)} pages", file=sys.stderr)
    if noindex:
        print(f"Skipped {len(noindex)} noindex pages", file=sys.stderr)
    if errors:
        print(f"Skipped {len(errors)} pages that failed to load", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
