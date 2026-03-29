"""
IPL 2026 Data Fetcher
Scrapes points table from ESPNcricinfo (free, no API key needed)
and today's matches from cricbuzz via web scraping.
Runs daily via GitHub Actions.
"""

import json
import os
import re
import urllib.request
from datetime import datetime, timezone

# ── Team name → abbreviation ──────────────────────────────────────────────────
TEAM_MAP = {
    "sunrisers hyderabad": "SRH", "sunrisers": "SRH",
    "royal challengers bengaluru": "RCB", "royal challengers bangalore": "RCB",
    "royal challengers": "RCB",
    "mumbai indians": "MI",
    "kolkata knight riders": "KKR",
    "chennai super kings": "CSK",
    "gujarat titans": "GT",
    "delhi capitals": "DC",
    "rajasthan royals": "RR",
    "punjab kings": "PBKS", "kings xi punjab": "PBKS",
    "lucknow super giants": "LSG",
}

ALL_TEAMS = ["RCB", "MI", "KKR", "CSK", "GT", "DC", "RR", "PBKS", "LSG", "SRH"]

SRH_SCHEDULE = [
    {"match": 1,  "vs": "RCB",  "venue": "M. Chinnaswamy Stadium, Bengaluru", "date": "2026-03-28", "time": "7:30 PM IST"},
    {"match": 6,  "vs": "KKR",  "venue": "Eden Gardens, Kolkata",             "date": "2026-04-02", "time": "7:30 PM IST"},
    {"match": 10, "vs": "LSG",  "venue": "Rajiv Gandhi Int'l Stadium, Hyd",   "date": "2026-04-05", "time": "3:30 PM IST"},
    {"match": 17, "vs": "PBKS", "venue": "New Chandigarh",                    "date": "2026-04-11", "time": "3:30 PM IST"},
    {"match": 21, "vs": "RR",   "venue": "Hyderabad",                         "date": "2026-04-13", "time": "7:30 PM IST"},
    {"match": 27, "vs": "CSK",  "venue": "Hyderabad",                         "date": "2026-04-18", "time": "7:30 PM IST"},
    {"match": 31, "vs": "DC",   "venue": "Hyderabad",                         "date": "2026-04-21", "time": "7:30 PM IST"},
    {"match": 36, "vs": "RR",   "venue": "Jaipur (away)",                     "date": "2026-04-25", "time": "7:30 PM IST"},
    {"match": 41, "vs": "MI",   "venue": "Wankhede, Mumbai (away)",           "date": "2026-04-29", "time": "7:30 PM IST"},
    {"match": 0,  "vs": "KKR",  "venue": "Hyderabad",                         "date": "2026-05-03", "time": "3:30 PM IST"},
    {"match": 0,  "vs": "PBKS", "venue": "Hyderabad",                         "date": "2026-05-06", "time": "7:30 PM IST"},
    {"match": 0,  "vs": "GT",   "venue": "Ahmedabad (away)",                  "date": "2026-05-12", "time": "7:30 PM IST"},
    {"match": 0,  "vs": "CSK",  "venue": "Chennai (away)",                    "date": "2026-05-18", "time": "7:30 PM IST"},
    {"match": 0,  "vs": "RCB",  "venue": "Hyderabad",                         "date": "2026-05-22", "time": "7:30 PM IST"},
]

# All IPL 2026 phase 1+2 fixtures (static, for today's tab fallback)
ALL_FIXTURES = [
    {"match": 1,  "t1": "RCB",  "t2": "SRH",  "date": "2026-03-28", "venue": "Bengaluru",      "time": "7:30 PM IST"},
    {"match": 2,  "t1": "MI",   "t2": "KKR",  "date": "2026-03-29", "venue": "Mumbai",          "time": "7:30 PM IST"},
    {"match": 3,  "t1": "RR",   "t2": "CSK",  "date": "2026-03-30", "venue": "Guwahati",        "time": "7:30 PM IST"},
    {"match": 4,  "t1": "PBKS", "t2": "GT",   "date": "2026-03-31", "venue": "New Chandigarh",  "time": "7:30 PM IST"},
    {"match": 5,  "t1": "LSG",  "t2": "DC",   "date": "2026-04-01", "venue": "Lucknow",         "time": "7:30 PM IST"},
    {"match": 6,  "t1": "KKR",  "t2": "SRH",  "date": "2026-04-02", "venue": "Kolkata",         "time": "7:30 PM IST"},
    {"match": 7,  "t1": "CSK",  "t2": "PBKS", "date": "2026-04-03", "venue": "TBD",             "time": "7:30 PM IST"},
    {"match": 8,  "t1": "DC",   "t2": "MI",   "date": "2026-04-04", "venue": "Delhi",           "time": "3:30 PM IST"},
    {"match": 9,  "t1": "GT",   "t2": "RR",   "date": "2026-04-04", "venue": "TBD",             "time": "7:30 PM IST"},
    {"match": 10, "t1": "SRH",  "t2": "LSG",  "date": "2026-04-05", "venue": "Hyderabad",       "time": "3:30 PM IST"},
    {"match": 11, "t1": "RCB",  "t2": "CSK",  "date": "2026-04-06", "venue": "Bengaluru",       "time": "7:30 PM IST"},
    {"match": 12, "t1": "KKR",  "t2": "PBKS", "date": "2026-04-07", "venue": "Kolkata",         "time": "7:30 PM IST"},
    {"match": 13, "t1": "RR",   "t2": "MI",   "date": "2026-04-07", "venue": "Guwahati",        "time": "3:30 PM IST"},
    {"match": 14, "t1": "DC",   "t2": "GT",   "date": "2026-04-08", "venue": "Delhi",           "time": "7:30 PM IST"},
    {"match": 15, "t1": "KKR",  "t2": "LSG",  "date": "2026-04-09", "venue": "Kolkata",         "time": "7:30 PM IST"},
    {"match": 16, "t1": "RR",   "t2": "RCB",  "date": "2026-04-10", "venue": "Jaipur",          "time": "7:30 PM IST"},
    {"match": 17, "t1": "PBKS", "t2": "SRH",  "date": "2026-04-11", "venue": "New Chandigarh",  "time": "3:30 PM IST"},
    {"match": 18, "t1": "CSK",  "t2": "DC",   "date": "2026-04-11", "venue": "Chennai",         "time": "7:30 PM IST"},
    {"match": 19, "t1": "LSG",  "t2": "GT",   "date": "2026-04-12", "venue": "Lucknow",         "time": "3:30 PM IST"},
    {"match": 20, "t1": "MI",   "t2": "RCB",  "date": "2026-04-12", "venue": "Mumbai",          "time": "7:30 PM IST"},
]


def to_abbr(raw_name):
    if not raw_name:
        return None
    clean = raw_name.strip().lower()
    if clean in TEAM_MAP:
        return TEAM_MAP[clean]
    for key, abbr in TEAM_MAP.items():
        if key in clean:
            return abbr
    return raw_name.strip()


def fetch_url(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; IPLTracker/1.0)"
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", errors="ignore")


def scrape_espncricinfo_table():
    """
    Scrape IPL 2026 points table from ESPNcricinfo.
    The page embeds JSON data in a __NEXT_DATA__ script tag.
    """
    url = "https://www.espncricinfo.com/series/ipl-2026-1510719/points-table-standings"
    print(f"  Fetching: {url}")
    try:
        html = fetch_url(url)

        # ESPNcricinfo embeds data as JSON in __NEXT_DATA__
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        if not match:
            print("  ⚠ __NEXT_DATA__ not found in ESPNcricinfo page")
            return []

        data = json.loads(match.group(1))

        # Navigate the JSON tree to find the standings
        # Path varies — search recursively for a list containing team standings
        raw_text = json.dumps(data)

        # Look for NRR pattern to find the right section
        # ESPNcricinfo uses "nrr", "teamName", "pts" fields
        tables = re.findall(
            r'\{"teamName":"([^"]+)","teamId":\d+[^}]*?"played":(\d+)[^}]*?"won":(\d+)[^}]*?"lost":(\d+)[^}]*?"tied":(\d+)[^}]*?"noResult":(\d+)[^}]*?"pts":(\d+)[^}]*?"nrr":([-\d.]+)',
            raw_text
        )

        if tables:
            print(f"  ✓ Found {len(tables)} teams via regex")
            result = []
            for t in tables:
                name, played, won, lost, tied, nr, pts, nrr = t
                abbr = to_abbr(name)
                nrr_f = float(nrr)
                result.append({
                    "team":    abbr,
                    "matches": int(played),
                    "wins":    int(won),
                    "losses":  int(lost),
                    "points":  int(pts),
                    "nrr":     f"{nrr_f:+.3f}" if nrr_f != 0 else "0.000",
                    "form":    [],
                })
            result.sort(key=lambda x: (x["points"], float(x["nrr"].replace("+","") or 0)), reverse=True)
            return result

        print("  ⚠ Could not parse standings from ESPNcricinfo JSON")
        return []

    except Exception as e:
        print(f"  ✗ ESPNcricinfo scrape failed: {e}")
        return []


def scrape_iplt20_table():
    """
    Fallback: scrape points table from iplt20.com
    """
    url = "https://www.iplt20.com/points-table/men"
    print(f"  Fallback fetch: {url}")
    try:
        html = fetch_url(url)

        # iplt20.com embeds standings in JSON script blocks
        # Look for team data pattern
        matches = re.findall(
            r'"teamName"\s*:\s*"([^"]+)"[^}]*?"matchPlayed"\s*:\s*(\d+)[^}]*?"matchWon"\s*:\s*(\d+)[^}]*?"matchLost"\s*:\s*(\d+)[^}]*?"points"\s*:\s*(\d+)[^}]*?"nrr"\s*:\s*"?([-+\d.]+)"?',
            html, re.DOTALL
        )

        if matches:
            print(f"  ✓ iplt20 fallback: {len(matches)} teams")
            result = []
            for m in matches:
                name, played, won, lost, pts, nrr = m
                abbr  = to_abbr(name)
                nrr_f = float(nrr)
                result.append({
                    "team":    abbr,
                    "matches": int(played),
                    "wins":    int(won),
                    "losses":  int(lost),
                    "points":  int(pts),
                    "nrr":     f"{nrr_f:+.3f}" if nrr_f != 0 else "0.000",
                    "form":    [],
                })
            result.sort(key=lambda x: (x["points"], float(x["nrr"].replace("+","") or 0)), reverse=True)
            return result

    except Exception as e:
        print(f"  ✗ iplt20 fallback failed: {e}")
    return []


def ensure_all_teams(table):
    """Make sure all 10 teams appear in the table."""
    present = {r["team"] for r in table}
    for t in ALL_TEAMS:
        if t not in present:
            table.append({"team": t, "matches": 0, "wins": 0, "losses": 0,
                          "points": 0, "nrr": "0.000", "form": []})
    return table


def get_today_fixtures(today_str):
    """Return today's fixtures from the hardcoded list."""
    return [
        {
            "teams":        [f["t1"], f["t2"]],
            "venue":        f["venue"],
            "status":       f"Match #{f['match']} · {f['time']}",
            "matchStarted": False,
            "matchEnded":   False,
            "score":        [],
        }
        for f in ALL_FIXTURES
        if f["date"] == today_str
    ]


def get_next_srh_match(today_str):
    for m in SRH_SCHEDULE:
        if m["date"] >= today_str:
            return m
    return None


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"\n{'='*50}\nIPL 2026 Tracker — {today}\n{'='*50}")

    # Try ESPNcricinfo first, fall back to iplt20.com
    table = scrape_espncricinfo_table()
    if not table:
        table = scrape_iplt20_table()
    if not table:
        print("  ⚠ All scrapes failed — using blank table")
    table = ensure_all_teams(table)

    srh_row = next((r for r in table if r["team"] == "SRH"),
                   {"team":"SRH","matches":0,"wins":0,"losses":0,"points":0,"nrr":"0.000","form":[]})
    srh_pos = next((i+1 for i,r in enumerate(table) if r["team"]=="SRH"), None)

    today_matches = get_today_fixtures(today)
    next_match    = get_next_srh_match(today)

    payload = {
        "updated_at":    datetime.now(timezone.utc).isoformat(),
        "updated_date":  today,
        "srh": {
            "position":   srh_pos,
            "points":     srh_row["points"],
            "matches":    srh_row["matches"],
            "wins":       srh_row["wins"],
            "losses":     srh_row["losses"],
            "nrr":        srh_row["nrr"],
            "form":       srh_row["form"],
            "captain":    "Ishan Kishan (interim) · Pat Cummins (injured)",
            "next_match": next_match,
        },
        "points_table":  table,
        "today_matches": today_matches,
        "srh_schedule":  SRH_SCHEDULE,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/ipl.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"\n  ✅ data/ipl.json written")
    print(f"  SRH → #{srh_pos}, {srh_row['points']} pts, NRR {srh_row['nrr']}")
    for r in table[:5]:
        print(f"    {r['team']}: {r['points']} pts, NRR {r['nrr']}, M {r['matches']}")


if __name__ == "__main__":
    main()
