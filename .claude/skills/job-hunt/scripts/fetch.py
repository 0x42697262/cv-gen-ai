"""Download public job feeds into an output folder. Read-only GETs; sends only skill keywords.

Usage: python3 -I fetch.py <job-hunt.yml> <out_dir>
"""
import json, os, sys, time, urllib.parse, urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/130.0"


def load_yaml(path):
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML is required: pip install pyyaml")
    return yaml.safe_load(open(path))


def get(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        open(dest, "wb").write(data)
        return r.status, len(data)
    except Exception as e:  # report and continue; one blocked feed must not stop the run
        return f"failed: {e.__class__.__name__}", 0


def main():
    cfg = load_yaml(sys.argv[1])
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    country = urllib.parse.quote(cfg["home_country"])
    jobs = []
    for kw in cfg["keywords"]:
        q = urllib.parse.quote_plus(kw)
        for page in (1, 2, 3):
            jobs.append((f"https://himalayas.app/jobs/api/search?q={q}&country={country}&page={page}",
                         f"himalayas_{q}_{page}.json"))
    for geo in ("apac", "anywhere"):
        for ind in ("dev", "engineering"):
            jobs.append((f"https://jobicy.com/api/v2/remote-jobs?count=100&geo={geo}&industry={ind}",
                         f"jobicy_{geo}_{ind}.json"))
    jobs += [
        ("https://remotive.com/api/remote-jobs?category=software-dev", "remotive.json"),
        ("https://remoteok.com/api", "remoteok.json"),
        ("https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss", "wwr_fullstack.rss"),
        ("https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss", "wwr_backend.rss"),
        ("https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss", "wwr_frontend.rss"),
    ]
    report = []
    for url, name in jobs:
        status, size = get(url, os.path.join(out, name))
        report.append({"source": urllib.parse.urlparse(url).netloc, "file": name, "status": status, "bytes": size})
        time.sleep(0.5)
    json.dump(report, open(os.path.join(out, "_fetch_report.json"), "w"), indent=1)
    blocked = sorted({r["source"] for r in report if r["status"] != 200})
    print(f"{sum(r['status'] == 200 for r in report)}/{len(report)} feeds fetched")
    if blocked:
        print("blocked or failed (domain only):", ", ".join(blocked))


if __name__ == "__main__":
    main()
