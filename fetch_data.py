"""
IPL 2026 Data Fetcher — runs daily via GitHub Actions
Fetches points table + today's matches from cricketdata.org
"""

import requests
import json
import os
from datetime import datetime, timezone

API_KEY = os.environ.get("CRICKET_API_KEY", "")
BASE    = "https://api.cricapi.com/v1"
IPL_SERIES_ID = "d5a498c8-7596-4b93-8ab0-e0efc3345312"

# Comprehensive name → abbreviation map
TEAM_MAP = {
    "sunrisers hyderabad": "SRH", "sunrisers": "SRH", "srh": "SRH",
    "royal challengers bengaluru": "RCB", "royal challengers bangalore": "RCB",
    "royal challengers": "RCB", "rcb": "RCB",
    "mumbai indians": "MI", "mumbai": "MI", "mi": "MI",
    "kolkata knight riders": "KKR", "kolkata": "KKR", "kkr": "KKR",
    "chennai super kings": "CSK", "chennai": "CSK", "csk": "CSK",
    "gujarat titans": "GT", "gujarat": "GT", "gt": "GT",
    "delhi capitals": "DC", "delhi": "DC", "dc": "DC",
    "rajasthan royals": "RR", "rajasthan": "RR", "rr": "RR",
    "punjab kings": "PBKS", "punjab": "PBKS", "pbks": "PBKS", "kings xi punjab": "PBKS",
    "lucknow super giants": "LSG", "lucknow": "LSG", "lsg": "LSG",
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


def to_abbr(raw_name):
    if not raw_name:
        return None
    clean = raw_name.strip().lower()
    if clean in TEAM_MAP:
        return TEAM_MAP[clean]
    for key, abbr in TEAM_MAP.items():
        if key in clean:
            return abbr
    print(f"  ⚠ Unknown team: '{raw_name}'")
    return raw_name.strip()

ipl_id = find_ipl_2026_series_id()
if not ipl_id:
    print("  ❌ Could not find IPL 2026 series ID")
    ipl_id = ""

def find_ipl_2026_series_id():
    """Search the series list to find the correct IPL 2026 series ID."""
    url = f"{BASE}/series?apikey={API_KEY}&offset=0"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        series_list = data.get("data", [])
        print(f"  [find_series] Total series returned: {len(series_list)}")
        for s in series_list:
            name = (s.get("name") or "").lower()
            start = s.get("startDate") or s.get("startdate") or ""
            print(f"    → {s.get('id')} | {s.get('name')} | {start}")
            if "indian premier league" in name and "2026" in name:
                print(f"  ✅ Found IPL 2026: {s.get('id')}")
                return s.get("id")
            if "ipl" in name and "2026" in name:
                print(f"  ✅ Found IPL 2026 (ipl): {s.get('id')}")
                return s.get("id")
        # Fallback: find by start date in 2026
        for s in series_list:
            start = s.get("startDate") or s.get("startdate") or ""
            name  = (s.get("name") or "").lower()
            if start.startswith("2026") and ("premier league" in name or "ipl" in name):
                print(f"  ✅ Found by date: {s.get('id')} | {s.get('name')}")
                return s.get("id")
    except Exception as e:
        print(f"  [find_series] FAILED: {e}")
    return None

def normalize_points_table(raw):
    table = []
    for row in raw:
        raw_name = (row.get("teamName") or row.get("team") or
                    row.get("name") or row.get("teamname") or "")
        abbr = to_abbr(raw_name)
        if not abbr:
            continue

        nrr_raw = row.get("nrr") or row.get("netRunRate") or row.get("net_run_rate") or 0
        try:
            nrr_f   = float(nrr_raw)
            nrr_str = f"{nrr_f:+.3f}" if nrr_f != 0 else "0.000"
        except Exception:
            nrr_str = "0.000"

        form_raw = row.get("form") or row.get("lastFive") or []
        if isinstance(form_raw, str):
            form_raw = list(form_raw)

        table.append({
            "team":    abbr,
            "matches": int(row.get("played") or row.get("matches") or row.get("matchesPlayed") or 0),
            "wins":    int(row.get("wins") or row.get("won") or 0),
            "losses":  int(row.get("losses") or row.get("lost") or 0),
            "points":  int(row.get("pts") or row.get("points") or row.get("pt") or 0),
            "nrr":     nrr_str,
            "form":    form_raw,
        })

    table.sort(key=lambda x: (x["points"], float(x["nrr"].replace("+", "") or 0)), reverse=True)

    # Ensure all 10 teams appear
    present = {r["team"] for r in table}
    for t in ALL_TEAMS:
        if t not in present:
            table.append({"team": t, "matches": 0, "wins": 0, "losses": 0,
                          "points": 0, "nrr": "0.000", "form": []})
    return table


def normalize_matches(match_list, today_str):
    today_matches = []
    for m in match_list:
        match_date = (m.get("date") or m.get("dateTimeGMT") or "")[:10]
        if match_date != today_str:
            continue
        teams_raw   = m.get("teams") or []
        teams_clean = [to_abbr(t) or t for t in teams_raw]
        today_matches.append({
            "name":         m.get("name", ""),
            "teams":        teams_clean,
            "venue":        m.get("venue", ""),
            "status":       m.get("status", ""),
            "score":        m.get("score", []),
            "matchStarted": m.get("matchStarted", False),
            "matchEnded":   m.get("matchEnded", False),
        })
    return today_matches


def get_next_srh_match(today_str):
    for m in SRH_SCHEDULE:
        if m["date"] >= today_str:
            return m
    return None


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"\n{'='*50}\nFetching IPL 2026 data — {today}\n{'='*50}")

    raw_table = get_series_points_table()
    if raw_table:
        points_table = normalize_points_table(raw_table)
        print(f"  ✓ Points table: {len(points_table)} teams")
    else:
        print("  ⚠ Blank points table")
        points_table = [{"team": t, "matches": 0, "wins": 0, "losses": 0,
                         "points": 0, "nrr": "0.000", "form": []} for t in ALL_TEAMS]

    srh_row = next((r for r in points_table if r["team"] == "SRH"),
                   {"team": "SRH", "matches": 0, "wins": 0, "losses": 0, "points": 0, "nrr": "0.000", "form": []})
    srh_pos = next((i + 1 for i, r in enumerate(points_table) if r["team"] == "SRH"), None)

    series_data   = get_series_info()
    today_matches = normalize_matches(series_data.get("matchList", []), today)
    print(f"  ✓ Today matches: {len(today_matches)}")

    next_match = get_next_srh_match(today)

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
        "points_table":  points_table,
        "today_matches": today_matches,
        "srh_schedule":  SRH_SCHEDULE,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/ipl.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"\n  ✅ data/ipl.json written")
    print(f"  SRH → #{srh_pos}, {srh_row['points']} pts, NRR {srh_row['nrr']}")


if __name__ == "__main__":
    main()
