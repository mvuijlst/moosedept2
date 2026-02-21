"""
Parse 2019gekeken.html through 2026gekeken.html and produce a JSON file
with the same structure as SimklBackup.json.

Note: IDs (simkl, imdb, tmdb, etc.), poster, and runtime are not available
in the HTML source and will be omitted from the output ids object.
"""

import json
import re
import html
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

# ── title corrections ─────────────────────────────────────────────────────────
# Fixes typos, capitalisation and duplicate alias titles recorded in the HTML.
# Applied to both shows and movies before any aggregation.

TITLE_CORRECTIONS: dict[str, str] = {
    # Typos / wrong characters
    "Kobra Kai":                                "Cobra Kai",
    "Rust Vallery Restorers":                   "Rust Valley Restorers",
    "The Mandalorean":                          "The Mandalorian",
    "Star Trek; Strange New Worlds":            "Star Trek: Strange New Worlds",
    "the End of the Fucking World":             "The End of the F***ing World",
    "Eurovision: The Story of Fire Sage":       "Eurovision Song Contest: The Story of Fire Saga",
    "Thork Ragnarok":                           "Thor: Ragnarok",
    "Rick & Morty":                             "Rick and Morty",
    # Case/punctuation normalisation
    "Masterchef":                               "MasterChef",
    "WHAT / IF, Part I":                        "What/If",
    "Doctor Who 2005":                          "Doctor Who",
    # Season subtitle variants → canonical show title
    # (the HTML records the season subtitle as the show name;
    #  they are already tracked under the correct season number)
    "Slasher, Solstice":                        "Slasher",
    "Archer Dreamland":                         "Archer",
    "Archer: Danger Island":                    "Archer",
    "Archer: 1999":                             "Archer",
    "American Horror Story: Cult":              "American Horror Story",
    "American Horror Story: 1984":              "American Horror Story",
    "Hell's Kitchen Las Vegas":                 "Hell's Kitchen",
    "Hell\u2019s Kitchen Las Vegas":            "Hell's Kitchen",
    "The Terror: Infamy":                       "The Terror",
}

# ── known premiere years ──────────────────────────────────────────────────────
# The HTML `jaar` column records the production year of a specific season/episode,
# which often differs from the show's premiere year that Simkl indexes.
# Override with the actual premiere year where the HTML is known to be wrong.

KNOWN_YEARS: dict[str, int] = {
    "24":                                   2001,
    "Arrested Development":                 2003,
    "Cobra Kai":                            2018,
    "Columbo":                              1971,
    "Doctor Who":                           2005,
    "Last Week Tonight":                    2014,
    "Lucifer":                              2016,
    "Rick and Morty":                       2013,
    "Sex Education":                        2019,
    "South Park":                           1997,
    "SpongeBob SquarePants":                1999,
    "The Crown":                            2016,
    "The Magicians":                        2015,
    "The Terror":                           2018,
    "Twilight Zone":                        1959,
    "WandaVision":                          2021,
    # Movies
    "Thor: Ragnarok":                       2017,
    "Justice League (Snyder Cut)":          2021,
    "Encanto":                              2021,
}

CONTENT_DIR = Path(__file__).parent / "content" / "gekeken"
OUTPUT_FILE = Path(__file__).parent / "content" / "gekeken" / "gekeken_backup.json"

CONTENT_DIR = Path(__file__).parent / "content" / "gekeken"
OUTPUT_FILE = Path(__file__).parent / "content" / "gekeken" / "gekeken_backup.json"

# ── date parsing ──────────────────────────────────────────────────────────────

def parse_date(raw: str) -> str | None:
    """Return an ISO-8601 UTC string from various date strings in the HTML."""
    raw = raw.strip()
    if not raw or raw == "\xa0":
        return None

    # Formats seen in the files:
    #   "2026-01-01 Thu 01:52"
    #   "2019-01-01 Tue"
    #   "2019-01-01 Tue 13:00"
    #   "2019-01-01"

    # Try with weekday + time
    for fmt in (
        "%Y-%m-%d %a %H:%M",
        "%Y-%m-%d %a",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            pass

    return None


# ── episode key parsing ────────────────────────────────────────────────────────

EP_RE = re.compile(r"s(\d+)e(\d+)", re.IGNORECASE)

def parse_episode(ep_str: str):
    """Return (season_number, episode_number) or None for films."""
    m = EP_RE.fullmatch(ep_str.strip())
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


# ── HTML table parsing ─────────────────────────────────────────────────────────

TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL | re.IGNORECASE)
TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)

def clean(cell: str) -> str:
    """Strip tags and decode HTML entities."""
    text = re.sub(r"<[^>]+>", "", cell)
    return html.unescape(text).strip()


def extract_data_rows(content: str) -> str:
    """
    Return the chunk of HTML containing the data <tr> rows.
    Handles three layouts found across the files:
      A) <tbody>...</tbody>      (2022-2024, 2026)
      B) <tbody> with no </tbody> (2025)
      C) No <tbody>, rows straight in <table> (2019-2021)
    In case C and the </tbody>-less B we fall back to pulling everything
    inside the last <table>...</table> block and strip the first <tr> (header).
    """
    # Case A: well-formed tbody
    m = re.search(r"<tbody[^>]*>(.*?)</tbody>", content, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1)

    # Case B / C: find the last <table>...</table> or everything after <tbody>
    # Try opening <tbody> without closing tag
    m2 = re.search(r"<tbody[^>]*>(.*)", content, re.DOTALL | re.IGNORECASE)
    if m2:
        chunk = m2.group(1)
        # Chop at </table> if present
        end = re.search(r"</table>", chunk, re.IGNORECASE)
        if end:
            chunk = chunk[:end.start()]
        return chunk

    # No tbody at all — find <table ...> opening tag, then take everything until </table>
    m3 = re.search(r"<table[^>]*>", content, re.IGNORECASE)
    if not m3:
        return ""
    table_content = content[m3.end():]
    end3 = re.search(r"</table>", table_content, re.IGNORECASE)
    if end3:
        table_content = table_content[:end3.start()]
    # Drop the first <tr>...</tr> which is the header
    first_tr = re.search(r"<tr[^>]*>.*?</tr>", table_content, re.DOTALL | re.IGNORECASE)
    if first_tr:
        table_content = table_content[first_tr.end():]
    return table_content


def parse_file(path: Path) -> list[dict]:
    """Return a list of row dicts from a single HTML file."""
    content = path.read_text(encoding="utf-8")
    section = extract_data_rows(content)

    rows = []
    for tr_match in TR_RE.finditer(section):
        cells = [clean(m.group(1)) for m in TD_RE.finditer(tr_match.group(1))]
        if len(cells) < 6:
            continue
        # columns: #, datum, type, naam, jaar, ep, titel, ★
        row = {
            "num":   cells[0],
            "date":  cells[1] if len(cells) > 1 else "",
            "type":  cells[2].lower() if len(cells) > 2 else "",
            "naam":  cells[3] if len(cells) > 3 else "",
            "jaar":  cells[4] if len(cells) > 4 else "",
            "ep":    cells[5] if len(cells) > 5 else "",
            "titel": cells[6] if len(cells) > 6 else "",
            "star":  cells[7] if len(cells) > 7 else "",
        }
        rows.append(row)
    return rows


# ── aggregate into shows / movies ─────────────────────────────────────────────

def slug(title: str) -> str:
    """Simple slug from title."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def correct_title(raw: str) -> str:
    """Apply known title corrections (typos, subtitle aliases, casing)."""
    return TITLE_CORRECTIONS.get(raw, raw)


def build_json(all_rows: list[dict]) -> dict:
    # Shows keyed by corrected canonical title.
    shows_map: dict[str, dict] = {}
    movies: list[dict] = []

    for row in all_rows:
        typ  = row["type"]
        naam = correct_title(row["naam"])
        ep   = row["ep"]
        date = parse_date(row["date"])

        if not naam:
            continue

        if typ == "film":
            try:
                jaar = int(row["jaar"])
            except (ValueError, TypeError):
                jaar = None
            # Apply known-year overrides for movies too
            jaar = KNOWN_YEARS.get(naam, jaar)

            movies.append({
                "added_to_watchlist_at": date,
                "last_watched_at": date,
                "user_rated_at": None,
                "user_rating": None,
                "status": "completed",
                "watched_episodes_count": 0,
                "total_episodes_count": 0,
                "not_aired_episodes_count": 0,
                "movie": {
                    "title": naam,
                    "poster": None,
                    "year": jaar,
                    "runtime": None,
                    "ids": {
                        "slug": slug(naam)
                    }
                }
            })

        elif typ == "serie":
            parsed = parse_episode(ep)
            if parsed is None:
                continue  # skip rows without a proper sXXeXX
            season_num, ep_num = parsed

            try:
                ep_year = int(row["jaar"])
            except (ValueError, TypeError):
                ep_year = None

            if naam not in shows_map:
                shows_map[naam] = {
                    "_year": ep_year,
                    "seasons": defaultdict(list),
                    "episodes_count": 0,
                }

            entry = shows_map[naam]
            entry["seasons"][season_num].append({
                "number": ep_num,
                "watched_at": date,
            })
            entry["episodes_count"] += 1
            # Keep track of the earliest episode year seen (used as fallback)
            if ep_year is not None and (entry["_year"] is None or ep_year < entry["_year"]):
                entry["_year"] = ep_year

    # ── build shows list ──────────────────────────────────────────────────────
    shows_list = []
    for naam, entry in shows_map.items():
        seasons_data = entry["seasons"]

        all_episodes = [
            (sn, ep_entry)
            for sn, eps in seasons_data.items()
            for ep_entry in eps
        ]

        def sort_key(item):
            _, ep_e = item
            return ep_e.get("watched_at") or "1970-01-01T00:00:00Z"

        all_episodes.sort(key=sort_key)
        last_sn, last_ep = all_episodes[-1]
        last_watched_at = last_ep["watched_at"]
        last_watched_str = f"S{last_sn:02d}E{last_ep['number']:02d}"

        # Deduplicate episodes within each season (keep the most recent watch)
        seasons_arr = []
        for sn in sorted(seasons_data.keys()):
            # If the same episode number appears multiple times, keep the latest
            ep_latest: dict[int, str | None] = {}
            for e in seasons_data[sn]:
                num = e["number"]
                wa  = e["watched_at"]
                if num not in ep_latest or (wa or "") > (ep_latest[num] or ""):
                    ep_latest[num] = wa
            seasons_arr.append({
                "number": sn,
                "episodes": [
                    {"number": n, "watched_at": wa}
                    for n, wa in sorted(ep_latest.items())
                ]
            })

        # Apply known-year override, fall back to earliest year seen in HTML
        show_year = KNOWN_YEARS.get(naam, entry["_year"])

        shows_list.append({
            "added_to_watchlist_at": last_watched_at,
            "last_watched_at": last_watched_at,
            "user_rated_at": None,
            "user_rating": None,
            "status": "watching",
            "last_watched": last_watched_str,
            "next_to_watch": None,
            "watched_episodes_count": sum(
                len(s["episodes"]) for s in seasons_arr
            ),
            "total_episodes_count": sum(
                len(s["episodes"]) for s in seasons_arr
            ),
            "not_aired_episodes_count": 0,
            "show": {
                "title": naam,
                "poster": None,
                "year": show_year,
                "runtime": None,
                "ids": {
                    "slug": slug(naam)
                }
            },
            "seasons": seasons_arr,
        })

    # Sort shows by last_watched_at descending
    shows_list.sort(key=lambda s: s["last_watched_at"] or "", reverse=True)

    # ── deduplicate movies ────────────────────────────────────────────────────
    # A movie watched multiple times appears as separate rows; keep only the
    # most recent watch to avoid Simkl import errors for duplicate entries.
    movies_deduped: dict[tuple, dict] = {}
    for m in movies:
        key = (m["movie"]["title"], m["movie"]["year"])
        existing = movies_deduped.get(key)
        if existing is None or (m["last_watched_at"] or "") > (existing["last_watched_at"] or ""):
            movies_deduped[key] = m
    movies_out = sorted(
        movies_deduped.values(),
        key=lambda m: m["last_watched_at"] or "",
        reverse=True,
    )

    return {"shows": shows_list, "movies": movies_out}


# ── main ───────────────────────────────────────────────────────────────────────

def main():
    years = range(2019, 2027)
    all_rows: list[dict] = []

    for year in years:
        path = CONTENT_DIR / f"{year}gekeken.html"
        if not path.exists():
            print(f"  skipping {path.name} (not found)")
            continue
        rows = parse_file(path)
        print(f"  {path.name}: {len(rows)} rows")
        all_rows.extend(rows)

    print(f"\nTotal rows: {len(all_rows)}")

    result = build_json(all_rows)
    print(f"Shows: {len(result['shows'])}")
    print(f"Movies: {len(result['movies'])}")

    OUTPUT_FILE.write_text(
        json.dumps(result, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\nWritten to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
