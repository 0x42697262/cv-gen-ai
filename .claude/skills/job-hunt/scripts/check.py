"""Company checks for /job-hunt. Read-only GETs; never sends user data.

  python3 -I check.py board <ashby|greenhouse|greenhouse-eu|lever|workable> <slug> [title words...]
      Is the role still on the company's own job board? Prints matches with direct apply links.
  python3 -I check.py page <url> [<url> ...]
      Status, page title, emails, job-board links. A blocked page prints its domain only.
"""
import json, re, sys, urllib.parse, urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/130.0"
NOISE = re.compile(r"\.(png|jpe?g|webp|svg|gif|js|css)$|sentry|example\.|wixpress|@\dx|^(you|your|name|member|user|email)@", re.I)
ATS = re.compile(r"https?://[^\"'\s<>]*(?:ashbyhq|greenhouse|lever\.co|workable|breezy|recruitee|teamtailor|bamboohr|careers-page|manatal|smartrecruiters|personio|jobs\.)[^\"'\s<>]*", re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.status, r.read().decode("utf-8", "replace")


def board(kind, slug, words):
    words = [w.lower() for w in words]
    urls = {
        "ashby": f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
        "greenhouse": f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
        "greenhouse-eu": f"https://job-boards.eu.greenhouse.io/{slug}",
        "lever": f"https://api.lever.co/v0/postings/{slug}?mode=json",
        "workable": f"https://apply.workable.com/api/v1/widget/accounts/{slug}",
    }
    try:
        status, body = fetch(urls[kind])
    except Exception as e:
        print(f"blocked or missing: {urllib.parse.urlparse(urls[kind]).netloc} ({e.__class__.__name__})")
        return
    rows = []
    if kind == "greenhouse-eu":
        for m in re.finditer(r'"title":"([^"]+)".{0,400}?"absolute_url":"([^"]+)"', body):
            rows.append((m.group(1), "", m.group(2)))
    else:
        d = json.loads(body)
        items = d.get("jobs", d) if isinstance(d, dict) else d
        for j in items:
            t = j.get("title") or j.get("text") or ""
            locs = [j.get("location") or ""] + [s.get("location", "") for s in j.get("secondaryLocations", []) or []]
            if isinstance(j.get("location"), dict):
                locs = [j["location"].get("name", "")]
            if isinstance(j.get("categories"), dict):
                locs = [j["categories"].get("location", "")]
            link = j.get("applyUrl") or j.get("absolute_url") or j.get("hostedUrl") or j.get("shortlink") or j.get("url") or ""
            rows.append((t, ", ".join(filter(None, map(str, locs))), link))
    seen, n = set(), 0
    for t, loc, link in rows:
        if (t, link) in seen or (words and not all(w in t.lower() for w in words)):
            continue
        seen.add((t, link)); n += 1
        print(f"OPEN | {t} | {loc[:120]} | {link}")
    print(f"{n} match(es) among {len(rows)} jobs on {kind}:{slug}" + ("" if n else " -> role probably closed"))


def page(urls):
    for u in urls:
        host = urllib.parse.urlparse(u).netloc
        try:
            status, body = fetch(u)
        except Exception as e:
            print(f"{host} | blocked or failed ({e.__class__.__name__})")
            continue
        title = re.sub(r"\s+", " ", (re.search(r"<title[^>]*>([^<]{0,120})", body, re.I) or [None, ""])[1]).strip()
        if re.search(r"just a moment|security checkpoint|attention required|captcha", title + body[:3000], re.I):
            print(f"{host} | blocked by a bot check")
            continue
        emails = sorted({e for e in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", body) if not NOISE.search(e)})
        ats = sorted({a for a in ATS.findall(body) if not re.search(r"\.(png|jpe?g|svg|css|js|woff2?)(\?|$)|amazonaws|/static/", a, re.I)})[:6]
        print(f"{u} | {status} | title: {title}")
        if emails:
            print(f"  emails ({len(emails)}): {', '.join(emails[:15])}{' ...' if len(emails) > 15 else ''}")
        for a in ats:
            print(f"  job board: {a}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    if sys.argv[1] == "board":
        board(sys.argv[2], sys.argv[3], sys.argv[4:])
    elif sys.argv[1] == "page":
        page(sys.argv[2:])
    else:
        sys.exit(__doc__)
