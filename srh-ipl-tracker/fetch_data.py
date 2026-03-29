"""
IPL 2026 Data Fetcher
Runs daily via GitHub Actions.
Fetches live match scores + points table from cricketdata.org API
and writes to data/ipl.json — which the dashboard HTML reads.
"""

import requests
import json
import os
from datetime import datetime, timezone

API_KEY = os.environ.get("CRICKET_API_KEY", "")
BASE    = "https://api.cricapi.com/v1"

# IPL 2026 series ID on cricketdata.org — update if needed after signup
IPL_SERIES_ID = "d5a498c8-7596-4b93-8ab0-e0efc3345312"

HEADERS = {"Content-Type": "application/json"}

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

TEAMS = ["RCB", "MI", "KKR", "CSK", "GT", "DC", "RR", "PBKS", "LSG", "SRH"]


def get_series_points_table():
    """Fetch points table from cricketdata.org series standings endpoint."""
    url = f"{BASE}/series_points?apikey={API_KEY}&id={IPL_SERIES_ID}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "success":
            return data.get("data", [])
    except Exception as e:
        print(f"Points table fetch failed: {e}")
    return []


def get_current_matches():
    """Fetch live and recent matches for the IPL series."""
    url = f"{BASE}/series_info?apikey={API_KEY}&id={IPL_SERIES_ID}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "success":
            return data.get("data", {})
    except Exception as e:
        print(f"Match fetch failed: {e}")
    return {}


def get_next_srh_match(today_str):
    """Return the next upcoming SRH match from the hardcoded schedule."""
    for m in SRH_SCHEDULE:
        if m["date"] >= today_str:
            return m
    return None


def build_fallback_table():
    """Return blank pre-season table if API is unavailable."""
    return [
        {"team": t, "matches": 0, "wins": 0, "losses": 0,
         "points": 0, "nrr": "0.000", "form": []}
        for t in TEAMS
    ]


def normalize_points_table(raw):
    """
    Normalize cricketdata.org response into our standard format.
    The API shape may vary — this tries common field names.
    """
    table = []
    for row in raw:
        team_name = (row.get("teamName") or row.get("team") or "").upper()
        # Map full names to abbreviations
        abbr_map = {
            "ROYAL CHALLENGERS BENGALURU": "RCB",
            "ROYAL CHALLENGERS BANGALORE": "RCB",
            "MUMBAI INDIANS": "MI",
            "KOLKATA KNIGHT RIDERS": "KKR",
            "CHENNAI SUPER KINGS": "CSK",
            "GUJARAT TITANS": "GT",
            "DELHI CAPITALS": "DC",
            "RAJASTHAN ROYALS": "RR",
            "PUNJAB KINGS": "PBKS",
            "LUCKNOW SUPER GIANTS": "LSG",
            "SUNRISERS HYDERABAD": "SRH",
        }
        abbr = abbr_map.get(team_name, team_name[:4])
        nrr_raw = row.get("nrr") or row.get("netRunRate") or 0
        try:
            nrr_float = float(nrr_raw)
            nrr_str = f"{nrr_float:+.3f}" if nrr_float != 0 else "0.000"
        except Exception:
            nrr_str = "0.000"

        table.append({
            "team":    abbr,
            "matches": int(row.get("played") or row.get("matches") or 0),
            "wins":    int(row.get("wins") or row.get("won") or 0),
            "losses":  int(row.get("losses") or row.get("lost") or 0),
            "points":  int(row.get("pts") or row.get("points") or 0),
            "nrr":     nrr_str,
            "form":    row.get("form") or [],
        })
    # Sort by points desc, then nrr desc
    table.sort(key=lambda x: (x["points"], x["nrr"]), reverse=True)
    return table


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"Fetching IPL 2026 data for {today}...")

    # 1. Points table
    raw_table = get_series_points_table()
    if raw_table:
        points_table = normalize_points_table(raw_table)
        print(f"  ✓ Points table: {len(points_table)} teams")
    else:
        points_table = build_fallback_table()
        print("  ⚠ Using fallback blank table (API unavailable or pre-season)")

    # 2. SRH stats from table
    srh_row = next((r for r in points_table if r["team"] == "SRH"), {
        "team": "SRH", "matches": 0, "wins": 0, "losses": 0,
        "points": 0, "nrr": "0.000", "form": []
    })
    srh_position = next(
        (i + 1 for i, r in enumerate(points_table) if r["team"] == "SRH"), None
    )

    # 3. Next SRH match
    next_match = get_next_srh_match(today)

    # 4. Live / today matches (series info)
    series_info = get_current_matches()
    match_list = series_info.get("matchList", [])
    today_matches = [
        m for m in match_list
        if m.get("date", "").startswith(today) or m.get("matchStarted") is True
    ]

    # 5. Build output payload
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_date": today,
        "srh": {
            "position": srh_position,
            "points": srh_row["points"],
            "matches": srh_row["matches"],
            "wins": srh_row["wins"],
            "losses": srh_row["losses"],
            "nrr": srh_row["nrr"],
            "form": srh_row["form"],
            "captain": "Ishan Kishan (interim) · Pat Cummins (injured)",
            "next_match": next_match,
        },
        "points_table": points_table,
        "today_matches": today_matches,
        "srh_schedule": SRH_SCHEDULE,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/ipl.json", "w") as f:
        json.dump(payload, f, indent=2)

    print(f"  ✓ Written to data/ipl.json")
    print(f"  SRH: Pos={srh_position}, Pts={srh_row['points']}, NRR={srh_row['nrr']}")


if __name__ == "__main__":
    main()
