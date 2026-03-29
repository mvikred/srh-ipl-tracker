"""
IPL 2026 Data Fetcher
Scrapes points table from Wikipedia's IPL 2026 page (plain HTML, reliably updated).
No API key needed. Runs daily via GitHub Actions.
"""

import json
import os
import re
import urllib.request
from datetime import datetime, timezone

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

ALL_FIXTURES = [
    {"match": 1,  "t1": "RCB",  "t2": "SRH",  "date": "2026-03-28", "venue": "Bengaluru",     "time": "7:30 PM IST", "result": "RCB won by 6 wkts"},
    {"match": 2,  "t1": "MI",   "t2": "KKR",  "date": "2026-03-29", "venue": "Mumbai",         "time": "7:30 PM IST", "result": ""},
    {"match": 3,  "t1": "RR",   "t2": "CSK",  "date": "2026-03-30", "venue": "Guwahati",       "time": "7:30 PM IST", "result": ""},
    {"match": 4,  "t1": "PBKS", "t2": "GT",   "date": "2026-03-31", "venue": "New Chandigarh", "time": "7:30 PM IST", "result": ""},
    {"match": 5,  "t1": "LSG",  "t2": "DC",   "date": "2026-04-01", "venue": "Lucknow",        "time": "7:30 PM IST", "result": ""},
    {"match": 6,  "t1": "KKR",  "t2": "SRH",  "date": "2026-04-02", "venue": "Kolkata",        "time": "7:30 PM IST", "result": ""},
    {"match": 7,  "t1": "CSK",  "t2": "PBKS", "date": "2026-04-03", "venue": "Chennai",        "time": "7:30 PM IST", "result": ""},
    {"match": 8,  "t1": "DC",   "t2": "MI",   "date": "2026-04-04", "venue": "Delhi",          "time": "3:30 PM IST", "result": ""},
    {"match": 9,  "t1": "GT",   "t2": "RR",   "date": "2026-04-04", "venue": "Ahmedabad",      "time": "7:30 PM IST", "result": ""},
    {"match": 10, "t1": "SRH",  "t2": "LSG",  "date": "2026-04-05", "venue": "Hyderabad",      "time": "3:30 PM IST", "result": ""},
    {"match": 11, "t1": "RCB",  "t2": "CSK",  "date": "2026-04-06", "venue": "Bengaluru",      "time": "7:30 PM IST", "result": ""},
    {"match": 12, "t1": "KKR",  "t2": "PBKS", "date": "2026-04-07", "venue": "Kolkata",        "time": "7:30 PM IST", "result": ""},
    {"match": 13, "t1": "RR",   "t2": "MI",   "date": "2026-04-07", "venue": "Guwahati",       "time": "3:30 PM IST", "result": ""},
    {"match": 14, "t1": "DC",   "t2": "GT",   "date": "2026-04-08", "venue": "Delhi",          "time": "7:30 PM IST", "result": ""},
    {"match": 15, "t1": "KKR",  "t2": "LSG",  "date": "2026-04-09", "venue": "Kolkata",        "time": "7:30 PM IST", "result": ""},
    {"match": 16, "t1": "RR",   "t2": "RCB",  "date": "2026-04-10", "venue": "Jaipur",         "time": "7:30 PM IST", "result": ""},
    {"match": 17, "t1": "PBKS", "t2": "SRH",  "date": "2026-04-11", "venue": "New Chandigarh", "time": "3:30 PM IST", "result": ""},
    {"match": 18, "t1": "CSK",  "t2": "DC",   "date": "2026-04-11", "venue": "Chennai",        "time": "7:30 PM IST", "result": ""},
    {"match": 19, "t1": "LSG",  "t2": "GT",   "date": "2026-04-12", "venue": "Lucknow",        "time": "3:30 PM IST", "result": ""},
    {"match": 20, "t1": "MI",   "t2": "RCB",  "date": "2026-04-12", "venue": "Mumbai",         "time": "7:30 PM IST", "result": ""},
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
        "User-Agent": "Mozilla/5.0 (compatible; IPLTracker/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("utf-8", errors="ignore")


def strip_tags(text):
    """Remove HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", text).strip()


def scrape_wikipedia():
    """
    Scrape IPL 2026 points table from Wikipedia.
    Wikipedia uses plain server-rendered HTML tables — reliable and no JS needed.
    """
    url = "https://en.wikipedia.org/wiki/2026_Indian_Premier_League"
    print(f"  Fetching Wikipedia: {url}")
    try:
        html = fetch_url(url)

        # Find the points table section — look for table containing 'Pts' header
        # Wikipedia tables have class="wikitable"
        # We extract all wikitables and find the one with team standings
        tables = re.findall(r"<table[^>]*wikitable[^>]*>(.*?)</table>", html, re.DOTALL | re.IGNORECASE)
        print(f"  Found {len(tables)} wikitables")

        for i, table in enumerate(tables):
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.DOTALL | re.IGNORECASE)
            if not rows:
                continue

            # Check if this table has the right headers
            header_text = strip_tags(rows[0]).lower() if rows else ""
            # Points table headers: Pld/M, W, L, Pts, NRR
            if not ("pts" in header_text or "points" in header_text):
                continue
            if not ("nrr" in header_text or "net run" in header_text):
                continue

            print(f"  Found points table at index {i}, header: {header_text[:80]}")

            result = []
            for row in rows[1:]:  # skip header row
                cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.DOTALL | re.IGNORECASE)
                if len(cells) < 5:
                    continue
                vals = [strip_tags(c) for c in cells]
                print(f"    Row values: {vals}")

                # First cell is team name (may have extra text/links)
                team_raw = vals[0]
                abbr = to_abbr(team_raw)
                if not abbr or abbr not in ALL_TEAMS:
                    continue

                try:
                    # Wikipedia column order: Team | Pld | W | L | T | NR | Pts | NRR | ...
                    # But may vary — find Pts and NRR by position
                    pld = int(re.search(r"\d+", vals[1]).group()) if re.search(r"\d+", vals[1]) else 0
                    won = int(re.search(r"\d+", vals[2]).group()) if re.search(r"\d+", vals[2]) else 0
                    lost= int(re.search(r"\d+", vals[3]).group()) if re.search(r"\d+", vals[3]) else 0
                    # Skip tied (vals[4]) and NR (vals[5]) if present
                    # Find pts — look for a cell that's a round number (0,2,4...)
                    pts_val = 0
                    nrr_val = "0.000"
                    for j, v in enumerate(vals[4:], 4):
                        if re.match(r"^\d+$", v.strip()):
                            pts_val = int(v.strip())
                        if re.match(r"^[+-]?\d+\.\d+$", v.strip()):
                            nrr_f = float(v.strip())
                            nrr_val = f"{nrr_f:+.3f}" if nrr_f != 0 else "0.000"

                    result.append({
                        "team":    abbr,
                        "matches": pld,
                        "wins":    won,
                        "losses":  lost,
                        "points":  pts_val,
                        "nrr":     nrr_val,
                        "form":    [],
                    })
                except Exception as e:
                    print(f"    ⚠ Row parse error: {e} — {vals}")
                    continue

            if result:
                result.sort(key=lambda x: (x["points"], float(x["nrr"].replace("+","") or 0)), reverse=True)
                print(f"  ✓ Wikipedia: {len(result)} teams parsed")
                return result

        print("  ⚠ No valid points table found in Wikipedia page")
        return []

    except Exception as e:
        print(f"  ✗ Wikipedia scrape failed: {e}")
        return []


def ensure_all_teams(table):
    present = {r["team"] for r in table}
    for t in ALL_TEAMS:
        if t not in present:
            table.append({"team": t, "matches": 0, "wins": 0, "losses": 0,
                          "points": 0, "nrr": "0.000", "form": []})
    return table


def get_today_fixtures(today_str):
    matches = []
    for f in ALL_FIXTURES:
        if f["date"] != today_str:
            continue
        is_past = f.get("result", "") != ""
        matches.append({
            "teams":        [f["t1"], f["t2"]],
            "venue":        f["venue"],
            "status":       f["result"] if is_past else f["time"],
            "matchStarted": is_past,
            "matchEnded":   is_past,
            "score":        [],
        })
    return matches


def get_next_srh_match(today_str):
    for m in SRH_SCHEDULE:
        if m["date"] >= today_str:
            return m
    return None


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"\n{'='*50}\nIPL 2026 Tracker — {today}\n{'='*50}")

    table = scrape_wikipedia()
    if not table:
        print("  ⚠ Scrape failed — using blank table")
    table = ensure_all_teams(table)

    srh_row = next((r for r in table if r["team"] == "SRH"),
                   {"team":"SRH","matches":0,"wins":0,"losses":0,"points":0,"nrr":"0.000","form":[]})
    srh_pos = next((i+1 for i,r in enumerate(table) if r["team"]=="SRH"), None)

    today_matches = get_today_fixtures(today)
    next_match    = get_next_srh_match(today)

    payload = {
        "updated_at":   datetime.now(timezone.utc).isoformat(),
        "updated_date": today,
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
    print(f"  Top 3: {[f\"{r['team']} {r['points']}pts\" for r in table[:3]]}")


if __name__ == "__main__":
    main()
