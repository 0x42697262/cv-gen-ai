"""Filter and rank downloaded job feeds against job-hunt.yml.

Usage: python3 -I rank.py <job-hunt.yml> <work-history.yml> <feeds_dir> <out.json>
Prints a ranked table and writes every kept posting with its flags to out.json.
"""
import datetime as dt, glob, html, json, os, re, sys

import yaml

NOW = dt.datetime.now(dt.timezone.utc)
DEV = re.compile(r"engineer|developer|full[- ]?stack|back[- ]?end|front[- ]?end|programmer|software", re.I)
NOT_DEV = re.compile(r"\bsales\b|account manager|recruit|marketing|designer|data entry|devrel|\bintern\b|expert –|research expert|phd", re.I)
SENIOR = re.compile(r"\bsenior\b|\bsr\.?\b|\blead\b|\bstaff\b|\bprincipal\b|\barchitect\b|\bhead of\b|\bdirector\b|\bvp\b|founding", re.I)
YEARS = re.compile(r"(\d+)\s*\+?\s*(?:-|–|to)?\s*\d*\s*\+?\s*years?", re.I)

# Flags worth showing the user; each is (name, pattern)
FLAGS = [
    ("discloses-other-jobs", r"disclose (?:any )?(?:existing|ongoing|other)|exclusiv|no other employment|not (?:hold|have) (?:any )?other (?:job|employment)|full[- ]time commitment to us only"),
    ("background-check", r"background (?:check|verification)|\bBGV\b"),
    ("linkedin-update", r"reflect this engagement on (?:their|your) linkedin|update (?:your )?linkedin"),
    ("video-required", r"\bloom\b|video introduction|record a video"),
    ("assessment", r"technical assessment|coding test|homework|take-home"),
    ("travel", r"travel up to|willingness to travel"),
    ("crypto-pay", r"\b(?:eth|usdt|token|crypto)\b.*(?:pay|locked)|locked for \d+ months"),
    ("per-task-gig", r"paid per task|output-based|per task that meets"),
    ("fee", r"(?:processing|placement|application|visa) fee"),
    ("low-budget", r"don't have large budgets|not looking for a big payday"),
    ("onsite-or-hybrid", r"\bonsite\b|\bon-site\b|\bhybrid\b"),
    ("night-shift", r"night ?shift|graveyard"),
]

# Business hours by time-zone hint: (pattern, UTC offset of the employer's 9-to-5)
TZ_HINTS = [
    (r"\bPST\b|\bPDT\b|pacific", -8), (r"\bMST\b|mountain time", -7), (r"\bCST\b|central time", -6),
    (r"\bEST\b|\bEDT\b|eastern time|US Eastern", -5), (r"US (?:time ?zone|hours|business hours)", -6),
    (r"\bAEST\b|\bAEDT\b|sydney|melbourne", 10), (r"\bGMT\b|\bBST\b|UK hours|london", 0),
    (r"\bCET\b|\bCEST\b|berlin|europe(?:an)? hours", 1), (r"\bSGT\b|singapore", 8), (r"\bJST\b|tokyo", 9),
]


def hours_set(start, end):
    s, e = int(start[:2]), int(end[:2])
    return {h % 24 for h in range(s, s + ((e - s) % 24 or 24))}


def clash(text, busy, my_off):
    """Hours of a 9-to-5 at the posting's hinted time zone that land inside the user's busy window."""
    for pat, off in TZ_HINTS:
        if re.search(pat, text, re.I):
            theirs = {(h - off + my_off) % 24 for h in range(9, 17)}
            return pat.split("|")[0].strip("\\b"), len(theirs & busy)
    return None, None


def ts(v):
    if v in (None, ""):
        return None
    s = str(v)
    try:
        if s.isdigit():
            return dt.datetime.fromtimestamp(int(s), dt.timezone.utc)
        if "," in s:
            return dt.datetime.strptime(s.strip(), "%a, %d %b %Y %H:%M:%S %z")
        d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def strip(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


def records(feeds):
    for f in glob.glob(os.path.join(feeds, "himalayas_*.json")):
        try:
            for j in json.load(open(f)).get("jobs", []):
                yield dict(src="himalayas", company=j["companyName"], title=j["title"], url=j["guid"],
                           date=ts(j.get("pubDate")), loc=", ".join(j.get("locationRestrictions") or []) or "Worldwide",
                           smin=j.get("minSalary"), smax=j.get("maxSalary"), period=j.get("salaryPeriod"),
                           cur=j.get("currency"), seniority=" ".join(j.get("seniority") or []),
                           text=strip(j.get("description")))
        except (ValueError, KeyError):
            continue
    for f in glob.glob(os.path.join(feeds, "jobicy_*.json")):
        try:
            for j in json.load(open(f)).get("jobs", []):
                yield dict(src="jobicy", company=j["companyName"], title=html.unescape(j["jobTitle"]), url=j["url"],
                           date=ts(j.get("pubDate")), loc=j.get("jobGeo", ""), smin=j.get("salaryMin"),
                           smax=j.get("salaryMax"), period=j.get("salaryPeriod"), cur=j.get("salaryCurrency"),
                           seniority=j.get("jobLevel", ""), text=strip(j.get("jobDescription")))
        except (ValueError, KeyError):
            continue
    p = os.path.join(feeds, "remotive.json")
    if os.path.exists(p):
        try:
            for j in json.load(open(p))["jobs"]:
                yield dict(src="remotive", company=j["company_name"], title=j["title"], url=j["url"],
                           date=ts(j["publication_date"]), loc=j.get("candidate_required_location", ""),
                           smin=None, smax=None, period=None, cur=None, seniority="",
                           text=strip(j.get("description")) + " salary: " + (j.get("salary") or ""))
        except (ValueError, KeyError):
            pass
    p = os.path.join(feeds, "remoteok.json")
    if os.path.exists(p):
        try:
            for j in json.load(open(p))[1:]:
                yield dict(src="remoteok", company=j.get("company", ""), title=j.get("position", ""), url=j.get("url"),
                           date=ts(j.get("date")), loc=j.get("location") or "Worldwide", smin=j.get("salary_min"),
                           smax=j.get("salary_max"), period="year", cur="USD", seniority="",
                           text=" ".join(j.get("tags") or []) + " " + strip(j.get("description")))
        except (ValueError, KeyError):
            pass
    for f in glob.glob(os.path.join(feeds, "wwr_*.rss")):
        x = open(f, encoding="utf-8", errors="replace").read()
        for it in re.findall(r"<item>(.*?)</item>", x, re.S):
            g = lambda tag: html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", (re.search(rf"<{tag}>(.*?)</{tag}>", it, re.S) or [None, ""])[1]))
            comp, _, title = g("title").partition(": ")
            yield dict(src="wwr", company=comp, title=title or comp, url=g("link").strip(), date=ts(g("pubDate")),
                       loc=g("region") or "Worldwide", smin=None, smax=None, period=None, cur=None, seniority="",
                       text=strip(g("description")))


def monthly_usd(v, period, cur, rates):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    if not v:
        return None
    rate = rates.get((cur or "USD").upper())
    if rate is None:
        return None
    p = (period or "year").lower()
    v = v * 160 if "hour" in p else v if "month" in p else v / 12
    return round(v * rate)


CUR = r"(AUD|USD|PHP|Php|EUR|GBP|SGD|CAD|₱|\$|€|£)"
NUM = r"(\d[\d,]*(?:\.\d+)?)\s?(k)?(?!\s?(?:m\b|mm\b|b\b|bn\b|million|billion|\+?\s?raised|\+ (?:users|customers|companies)))"
PER = r"\s*(?:USD|AUD|PHP)?\s*(?:/|per|a)?\s*(month|monthly|mo\b|hour|hr\b|year|yr\b|annum|annual)?"
SYM = {"₱": "PHP", "$": "USD", "€": "EUR", "£": "GBP"}


def _num(x, k):
    return float(x.replace(",", "")) * (1000 if k else 1) if x else None


def _per(per, lo, cur):
    per = (per or "").lower()
    if per:
        return per
    if lo is not None and lo < 200:
        return "hour"
    return "month" if cur == "PHP" or (lo or 0) < 20000 else "year"


def text_pay(text, rates, home_only=False):
    """Find stated pay in a description: '$7-$10 USD/Hour', 'AUD 3,000 - 4,000 / month', '50,000 to 60,000 Php'."""
    m = re.search(CUR + r"\s?" + NUM + r"(?:\s?(?:-|–|to)\s?" + CUR + r"?\s?" + NUM + r")?" + PER, text, re.I)
    if m and _num(m.group(2), m.group(3)) and _num(m.group(2), m.group(3)) >= 5:
        cur = SYM.get(m.group(1), m.group(1).upper())
        lo, hi = _num(m.group(2), m.group(3)), _num(m.group(5), m.group(6))
        per = _per(m.group(7), lo, cur)
        return monthly_usd(lo, per, cur, rates), monthly_usd(hi or lo, per, cur, rates)
    m = re.search(NUM + r"(?:\s?(?:-|–|to)\s?" + NUM + r")?\s?" + CUR + PER, text, re.I)
    if m and _num(m.group(1), m.group(2)):
        cur = SYM.get(m.group(5), m.group(5).upper())
        lo, hi = _num(m.group(1), m.group(2)), _num(m.group(3), m.group(4))
        per = _per(m.group(6), lo, cur)
        return monthly_usd(lo, per, cur, rates), monthly_usd(hi or lo, per, cur, rates)
    if home_only:  # local postings often write 'Monthly Rate: 40,000' with no currency
        m = re.search(r"(?:monthly (?:rate|salary)|salary(?: range)?|basic pay)\D{0,15}(\d{2,3},\d{3})(?:\s?(?:-|to)\s?(\d{2,3},\d{3}))?", text, re.I)
        if m:
            lo, hi = _num(m.group(1), None), _num(m.group(2), None)
            return monthly_usd(lo, "month", "PHP", rates), monthly_usd(hi or lo, "month", "PHP", rates)
    return None, None


def main():
    cfg = yaml.safe_load(open(sys.argv[1]))
    wh = yaml.safe_load(open(sys.argv[2])) if os.path.exists(sys.argv[2]) else {}
    feeds, out = sys.argv[3], sys.argv[4]
    rates = {k.upper(): v for k, v in cfg["usd_per"].items()}
    busy = hours_set(*cfg["busy_hours"].split("-"))
    my_off = cfg["timezone_utc_offset"]
    cutoff = NOW - dt.timedelta(days=cfg["max_age_days"])
    current = [re.sub(r"\s*\(.*\)", "", j["employer"]).lower() for j in wh.get("jobs", []) if str(j.get("end")) == "present"]
    excluded = {e["name"].lower(): e["why"] for e in cfg.get("exclude_companies", [])}
    agencies = {a.lower() for a in cfg.get("known_agencies", [])}
    regions = re.compile("|".join(map(re.escape, cfg["accepted_regions"])), re.I)
    stack = [s.lower() for s in cfg["stack"]]

    kept, dropped = {}, {"not-dev": 0, "old": 0, "region": 0, "stack": 0, "below-floor": 0, "excluded": 0}
    for r in records(feeds):
        title, comp = r["title"] or "", (r["company"] or "").strip()
        if not DEV.search(title) or NOT_DEV.search(title):
            dropped["not-dev"] += 1; continue
        if r["date"] and r["date"] < cutoff:
            dropped["old"] += 1; continue
        if not (regions.search(r["loc"]) or r["loc"].strip() == ""):
            dropped["region"] += 1; continue
        lc = comp.lower()
        if any(c and c in lc for c in current) or any(e in lc for e in excluded):
            dropped["excluded"] += 1; continue
        body = f"{title} {r['text']}"
        low = body.lower()
        hits = [s for s in stack if re.search(r"\b" + re.escape(s), low)]
        if len(hits) < cfg["min_stack_hits"]:
            dropped["stack"] += 1; continue
        lo, hi = monthly_usd(r["smin"], r["period"], r["cur"], rates), monthly_usd(r["smax"], r["period"], r["cur"], rates)
        pay_src = "listed" if (lo or hi) else None
        if not (lo or hi):
            lo, hi = text_pay(r["text"], rates, home_only=r["loc"].strip().lower() == cfg["home_country"].lower())
            pay_src = "guessed from text, verify" if (lo or hi) else None
        if (hi or lo) and (hi or lo) < cfg["pay_floor_usd_month"]:
            dropped["below-floor"] += 1; continue
        yrs = [int(m.group(1)) for m in YEARS.finditer(r["text"]) if int(m.group(1)) < 20]
        need = min(yrs) if yrs else None
        senior = bool(SENIOR.search(title) or re.search(r"senior|lead|director", r["seniority"] or "", re.I))
        tz, clash_h = clash(body, busy, my_off)
        flags = [n for n, p in FLAGS if re.search(p, body, re.I)]
        if lc in agencies or re.search(r"\bour client\b|on behalf of (?:our|a) client", low):
            flags.append("agency")
        stretch = senior or (need is not None and need > cfg["years_experience"] + 0.5)
        score = len(hits) * 2 + (6 if lo or hi else 0) + (-6 if stretch else 0) + (-4 if (clash_h or 0) >= 4 else 0)
        score -= 3 * sum(f in flags for f in ("discloses-other-jobs", "low-budget", "crypto-pay", "per-task-gig", "fee"))
        if r["date"]:
            score += max(0, 5 - (NOW - r["date"]).days // 7)
        key = (lc, title.lower())
        rec = dict(score=score, company=comp, title=title, url=r["url"], source=r["src"],
                   posted=r["date"].date().isoformat() if r["date"] else None, location=r["loc"][:80],
                   pay_usd_month=[lo, hi] if (lo or hi) else None, pay_source=pay_src, years_asked=need, stretch=stretch, senior=senior,
                   hours_hint=tz, hours_clash=clash_h, flags=flags, stack_hits=hits)
        if key not in kept or score > kept[key]["score"]:
            kept[key] = rec
    rows = sorted(kept.values(), key=lambda x: -x["score"])
    json.dump(rows, open(out, "w"), indent=1)
    print(f"kept {len(rows)}; dropped {dropped}")
    for x in rows[:60]:
        pay = (f"${x['pay_usd_month'][0] or '?'}-{x['pay_usd_month'][1] or '?'}" + ("~" if x["pay_source"] != "listed" else "")) if x["pay_usd_month"] else "pay ?"
        clash_s = f"clash {x['hours_clash']}h" if x["hours_clash"] else ""
        print(f"{x['score']:>3} {x['posted'] or '?':10} {'STRETCH ' if x['stretch'] else '        '}"
              f"{x['company'][:24]:24} {x['title'][:46]:46} {pay:12} {clash_s:9} {','.join(x['flags'])}")


if __name__ == "__main__":
    main()
