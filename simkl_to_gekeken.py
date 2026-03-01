#!/usr/bin/env python3
"""
simkl_to_gekeken.py
-------------------
Two-way sync between content/gekeken/{YEAR}gekeken.html and Simkl.

  Pull (default)
      Downloads watch history for YEAR from Simkl and appends any entries
      that are not yet in the HTML file.

  Push  (--push-to-simkl)
      Reads the HTML file and uploads any entries that are missing from
      Simkl to /sync/history, so both sides end up in sync.

  Both directions can be combined:
      python simkl_to_gekeken.py --push-to-simkl

  Sync dates  (--sync-dates)
      Reads all *gekeken.html files (or just --year's file) and, for every
      entry already in Simkl whose watched_at timestamp differs from the HTML,
      removes it from Simkl history and re-adds it with the correct time.
      Use this to fix bulk-imported entries that all share the same wrong
      timestamp.

First-run authentication
    The script uses Simkl's PIN flow (designed for CLI tools):
    1. It prints a short code and a URL.
    2. You visit the URL, log in, and enter the code.
    3. The script receives an access_token and saves it to .simkl_token.json.

Configuration
    Create .simkl_config.json next to this script with at least:
        { "client_id": "YOUR_SIMKL_CLIENT_ID" }
    Or set environment variables SIMKL_CLIENT_ID (and optionally SIMKL_TOKEN).
    Get a client_id at https://simkl.com/settings/developer/new/

Usage
    python simkl_to_gekeken.py [--year YEAR] [--push-to-simkl] [--sync-dates] [--dry-run]
"""

import argparse
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# ── constants ─────────────────────────────────────────────────────────────────

API_BASE  = "https://api.simkl.com"
TMDB_BASE = "https://api.themoviedb.org/3"

SCRIPT_DIR   = Path(__file__).parent
CONFIG_FILE  = SCRIPT_DIR / ".simkl_config.json"
TOKEN_FILE   = SCRIPT_DIR / ".simkl_token.json"
CONTENT_DIR  = SCRIPT_DIR / "content" / "gekeken"

# ── credentials ───────────────────────────────────────────────────────────────

def load_config() -> dict:
    cfg: dict = {}
    if CONFIG_FILE.exists():
        cfg.update(json.loads(CONFIG_FILE.read_text("utf-8")))
    # Environment variables override the file
    if os.environ.get("SIMKL_CLIENT_ID"):
        cfg["client_id"] = os.environ["SIMKL_CLIENT_ID"]
    if os.environ.get("SIMKL_TOKEN"):
        cfg["access_token"] = os.environ["SIMKL_TOKEN"]
    # Fall back to saved token file
    if "access_token" not in cfg and TOKEN_FILE.exists():
        td = json.loads(TOKEN_FILE.read_text("utf-8"))
        cfg["access_token"] = td.get("access_token", "")
    return cfg


def save_token(token: str) -> None:
    TOKEN_FILE.write_text(json.dumps({"access_token": token}, indent=2), "utf-8")
    print(f"Access token saved to {TOKEN_FILE}")


def prompt_client_id() -> str:
    print("\nNo Simkl client_id found.")
    print("Create a free app at https://simkl.com/settings/developer/new/ to get one.")
    return input("Enter your Simkl client_id: ").strip()


def pin_authenticate(client_id: str) -> str:
    """Run PIN device-code flow and return access_token."""
    print("\nStarting Simkl PIN authentication...")
    resp = requests.post(
        f"{API_BASE}/oauth/pin",
        json={"client_id": client_id},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    user_code   = data["user_code"]
    verify_url  = data.get("verification_url", "https://simkl.com/pin/")
    expires_in  = int(data.get("expires_in", 300))
    interval    = int(data.get("interval", 5))

    print(f"\n  Go to:  {verify_url}")
    print(f"  Code:   {user_code}\n")
    print(f"Waiting for you to authorise (timeout {expires_in}s)...", flush=True)

    deadline = time.monotonic() + expires_in
    while time.monotonic() < deadline:
        time.sleep(interval)
        check = requests.get(
            f"{API_BASE}/oauth/pin/{user_code}",
            params={"client_id": client_id},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if check.status_code == 200:
            token = check.json().get("access_token")
            if token:
                print("Authorisation successful!")
                save_token(token)
                return token
        # 400 = pending; anything else is an error
        elif check.status_code not in (400, 404):
            check.raise_for_status()

    raise RuntimeError("PIN authentication timed out — please run the script again.")


def get_headers(client_id: str, access_token: str) -> dict:
    return {
        "Content-Type": "application/json",
        "simkl-api-key": client_id,
        "Authorization": f"Bearer {access_token}",
    }


# ── Simkl API helpers ─────────────────────────────────────────────────────────

def fetch_all_items(headers: dict, item_type: str) -> list:
    """
    GET /sync/all-items/{item_type}?extended=full&episode_watched_at=yes
    The API returns {"movies": [...]} or {"shows": [...]}.
    Returns the inner list.
    """
    url = f"{API_BASE}/sync/all-items/{item_type}"
    params = {
        "extended": "full",
        "episode_watched_at": "yes",
    }
    resp = requests.get(url, headers=headers, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return []
    # Response is {"movies": [...]} or {"shows": [...]}
    if isinstance(data, dict):
        return data.get(item_type, []) or []
    if isinstance(data, list):
        return data
    return []


def fetch_episode_titles_from_tmdb(tmdb_id: str, api_key: str,
                                    show_name: str) -> dict:
    """
    Fetch all episode titles for *show_name* from TMDB.
    Returns {(season_number, episode_number): title_string}.
    """
    result: dict = {}
    try:
        r = requests.get(
            f"{TMDB_BASE}/tv/{tmdb_id}",
            params={"api_key": api_key, "language": "en-US"},
            timeout=20,
        )
        if r.status_code != 200:
            print(f"    Warning: TMDB returned HTTP {r.status_code} for {show_name!r}")
            return {}
        seasons = r.json().get("seasons", [])
    except requests.RequestException as exc:
        print(f"    Warning: TMDB request failed for {show_name!r}: {exc}")
        return {}

    for season in seasons:
        s_num = season.get("season_number", 0)
        if s_num == 0:          # skip specials
            continue
        try:
            rs = requests.get(
                f"{TMDB_BASE}/tv/{tmdb_id}/season/{s_num}",
                params={"api_key": api_key, "language": "en-US"},
                timeout=20,
            )
            if rs.status_code != 200:
                continue
            for ep in rs.json().get("episodes", []):
                e_num = ep.get("episode_number")
                title = ep.get("name") or ""
                if e_num is not None:
                    result[(s_num, e_num)] = title
        except requests.RequestException:
            continue

    return result


def fetch_episode_titles(client_id: str, simkl_id: int, show_name: str,
                         tmdb_id: str | None = None,
                         tmdb_api_key: str | None = None) -> dict:
    """
    Returns {(season, episode_number): title_string}, or {} if unavailable.
    Tries the Simkl endpoint first; falls back to TMDB when a key is provided.
    """
    url = f"{API_BASE}/tv/{simkl_id}/episodes"
    try:
        resp = requests.get(
            url,
            headers={"simkl-api-key": client_id, "Content-Type": "application/json"},
            params={"extended": "full"},
            timeout=30,
        )
        if resp.status_code == 200:
            raw = resp.json()
            if isinstance(raw, list) and raw:
                result: dict = {}
                for ep in raw:
                    if not isinstance(ep, dict):
                        continue
                    s = ep.get("season", 1)
                    n = ep.get("episode") or ep.get("number")
                    t = ep.get("title") or ep.get("name") or ""
                    if n is not None:
                        result[(s, n)] = t
                return result
    except requests.RequestException as exc:
        print(f"    Warning: HTTP error fetching episodes for {show_name!r}: {exc}")

    # Simkl endpoint broken — fall back to TMDB if a key was provided
    if tmdb_id and tmdb_api_key:
        return fetch_episode_titles_from_tmdb(tmdb_id, tmdb_api_key, show_name)

    return {}


def search_simkl_id(client_id: str, title: str, year: int | str,
                    media_type: str) -> int | None:
    """
    Search Simkl for *title* and return its simkl ID, or None if not found.
    media_type: "movie" | "show"  (maps to /search/movie or /search/tv)
    """
    endpoint = "movie" if media_type == "movie" else "tv"
    resp = requests.get(
        f"{API_BASE}/search/{endpoint}",
        headers={"simkl-api-key": client_id, "Content-Type": "application/json"},
        params={"q": title, "extended": "full", "limit": 5},
        timeout=20,
    )
    if resp.status_code != 200:
        return None
    results = resp.json()
    if not isinstance(results, list) or not results:
        return None
    # Pick the first result whose title and year match; fall back to first.
    year_int = int(year) if year else 0
    for item in results:
        t = item.get("title", "")
        y = item.get("year", 0)
        if t.lower() == title.lower() and (not year_int or y == year_int):
            return item.get("ids", {}).get("simkl")
    return results[0].get("ids", {}).get("simkl")


def html_date_to_iso(raw: str) -> str | None:
    """Convert HTML date strings like '2026-01-01 Thu 01:52' to ISO-8601 UTC."""
    raw = raw.strip()
    if not raw or raw == "\xa0":
        return None
    for fmt in ("%Y-%m-%d %a %H:%M", "%Y-%m-%d %a", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            pass
    return None


def parse_html_rows(content: str) -> list[dict]:
    """Return all data rows from the HTML table as dicts."""
    rows = []
    for tr in _TR_RE.finditer(_get_tbody(content)):
        cells = [_clean(c.group(1)) for c in _TD_RE.finditer(tr.group(1))]
        if len(cells) < 6:
            continue
        try:
            int(cells[0])  # skip header-like rows
        except ValueError:
            continue
        rows.append({
            "num":   cells[0],
            "date":  cells[1],
            "type":  cells[2].lower(),
            "naam":  cells[3],
            "jaar":  cells[4],
            "ep":    cells[5],
            "titel": cells[6] if len(cells) > 6 else "",
        })
    return rows


def build_simkl_known_set(movies_raw: list, shows_raw: list) -> set:
    """
    Build a set of keys for ALL items in the Simkl watchlist (not year-filtered).
    - films:  ("film",  title_lower)
    - series: ("serie", title_lower, "s01e02")
    """
    known: set = set()
    for item in movies_raw:
        mov = item.get("movie", {})
        known.add(("film", mov.get("title", "").lower()))
    for item in shows_raw:
        show = item.get("show", {})
        title_low = show.get("title", "").lower()
        for season in item.get("seasons", []):
            s = season.get("number", 1)
            for ep in season.get("episodes", []):
                e = ep.get("number")
                if e is not None:
                    known.add(("serie", title_low, f"s{s:02d}e{e:02d}"))
    return known


_EP_RE = re.compile(r"s(\d+)e(\d+)", re.IGNORECASE)


def push_html_entries_to_simkl(headers: dict, client_id: str,
                                entries: list[dict], dry_run: bool) -> None:
    """
    Upload *entries* (HTML rows missing from Simkl) to /sync/history.
    Each entry is a dict as returned by parse_html_rows().
    """
    if not entries:
        print("\n[push] Nothing to push to Simkl.")
        return

    print(f"\n[push] {len(entries)} entry/entries to upload to Simkl:")
    for e in entries:
        ep_display = e["ep"] if e["ep"] and e["ep"] != "\xa0" else "-"
        print(f"  {e['date']:<24}  {e['type']:<5}  {e['naam']}  {ep_display}")

    if dry_run:
        print("[dry-run] Skipping actual upload.")
        return

    # ── build movies payload ──────────────────────────────────────────────────
    movie_entries = [e for e in entries if e["type"] == "film"]
    show_entries  = [e for e in entries if e["type"] == "serie"]

    movies_payload: list[dict] = []
    id_cache: dict[tuple, int | None] = {}  # (media_type, title_lower) → simkl_id

    for e in movie_entries:
        title = e["naam"]
        jaar  = e["jaar"]
        watched_at = html_date_to_iso(e["date"])
        if not watched_at:
            print(f"  Warning: could not parse date for {title!r}, skipping.")
            continue
        key = ("movie", title.lower())
        if key not in id_cache:
            print(f"  Searching Simkl for movie {title!r}...")
            id_cache[key] = search_simkl_id(client_id, title, jaar, "movie")
        simkl_id = id_cache[key]
        obj: dict = {"title": title, "watched_at": watched_at}
        try:
            obj["year"] = int(jaar)
        except (ValueError, TypeError):
            pass
        if simkl_id:
            obj["ids"] = {"simkl": simkl_id}
        else:
            print(f"  Warning: no Simkl ID found for movie {title!r}, sending title only.")
        movies_payload.append(obj)

    # ── build shows payload ───────────────────────────────────────────────────
    # Group episodes by show name
    shows_map: dict[str, dict] = {}  # title → {"jaar": ..., "id": ..., "seasons": {s: {e: iso}}}

    for e in show_entries:
        title = e["naam"]
        jaar  = e["jaar"]
        ep_str = e["ep"] if e["ep"] and e["ep"] != "\xa0" else ""
        watched_at = html_date_to_iso(e["date"])
        if not watched_at or not ep_str:
            print(f"  Warning: skipping {title!r} {ep_str!r} (missing date/ep).")
            continue
        m = _EP_RE.fullmatch(ep_str.strip())
        if not m:
            print(f"  Warning: unrecognised episode format {ep_str!r} for {title!r}, skipping.")
            continue
        s_num, e_num = int(m.group(1)), int(m.group(2))

        if title not in shows_map:
            key = ("show", title.lower())
            if key not in id_cache:
                print(f"  Searching Simkl for show {title!r}...")
                id_cache[key] = search_simkl_id(client_id, title, jaar, "show")
            shows_map[title] = {"jaar": jaar, "id": id_cache[key], "seasons": {}}

        seasons = shows_map[title]["seasons"]
        if s_num not in seasons:
            seasons[s_num] = {}
        seasons[s_num][e_num] = watched_at

    shows_payload: list[dict] = []
    for title, info in shows_map.items():
        obj = {"title": title}
        try:
            obj["year"] = int(info["jaar"])
        except (ValueError, TypeError):
            pass
        if info["id"]:
            obj["ids"] = {"simkl": info["id"]}
        else:
            print(f"  Warning: no Simkl ID found for show {title!r}, sending title only.")
        season_list = []
        for s_num, episodes in sorted(info["seasons"].items()):
            ep_list = [{"number": e_num, "watched_at": wat}
                       for e_num, wat in sorted(episodes.items())]
            season_list.append({"number": s_num, "episodes": ep_list})
        obj["seasons"] = season_list
        shows_payload.append(obj)

    # ── POST ──────────────────────────────────────────────────────────────────
    payload: dict = {}
    if movies_payload:
        payload["movies"] = movies_payload
    if shows_payload:
        payload["shows"] = shows_payload

    if not payload:
        print("[push] Nothing uploadable (all entries lacked parseable dates).")
        return

    print(f"\n[push] Uploading {len(movies_payload)} movie(s) and "
          f"{len(shows_payload)} show(s) to Simkl...")
    resp = requests.post(
        f"{API_BASE}/sync/history",
        headers=headers,
        json=payload,
        timeout=60,
    )
    if resp.status_code in (200, 201):
        result = resp.json()
        added = result.get("added", {})
        print(f"[push] Simkl accepted: "
              f"{added.get('movies', 0)} movie(s), "
              f"{added.get('episodes', 0)} episode(s).")
        not_found = result.get("not_found", {})
        if any(not_found.get(k) for k in ("movies", "shows")):
            print(f"[push] Not found by Simkl: {not_found}")
    else:
        print(f"[push] Error {resp.status_code}: {resp.text[:300]}")


# ── sync-dates: update Simkl timestamps to match the HTML ────────────────────

def _to_minute(iso: str) -> str:
    """Truncate an ISO-8601 UTC string to minute precision: '2026-01-01T13:42'."""
    return iso[:16]  # 'YYYY-MM-DDTHH:MM'


def build_html_date_map(html_files: list[Path]) -> tuple[dict, dict]:
    """
    Parse all given HTML files and return:
      show_map : {title_lower: {"naam": str, "jaar": str,
                                "episodes": {(s, e): iso_str}}}
      movie_map: {title_lower: {"naam": str, "jaar": str, "watched_at": iso_str}}
    When a title appears in multiple files the last entry per episode wins.
    """
    show_map:  dict = {}
    movie_map: dict = {}

    for path in html_files:
        content = path.read_text("utf-8")
        for row in parse_html_rows(content):
            iso = html_date_to_iso(row["date"])
            if not iso:
                continue
            naam   = row["naam"]
            naam_l = naam.lower()
            jaar   = row["jaar"]
            if row["type"] == "film":
                movie_map[naam_l] = {"naam": naam, "jaar": jaar, "watched_at": iso}
            elif row["type"] == "serie":
                ep_str = row["ep"]
                if not ep_str or ep_str == "\xa0":
                    continue
                m = _EP_RE.fullmatch(ep_str.strip())
                if not m:
                    continue
                s_num, e_num = int(m.group(1)), int(m.group(2))
                if naam_l not in show_map:
                    show_map[naam_l] = {"naam": naam, "jaar": jaar, "episodes": {}}
                show_map[naam_l]["episodes"][(s_num, e_num)] = iso

    return show_map, movie_map


def sync_dates_to_simkl(headers: dict,
                        movies_raw: list, shows_raw: list,
                        html_files: list[Path], dry_run: bool) -> None:
    """
    Compare Simkl watched_at timestamps against the HTML source of truth.
    Remove + re-add any entry whose timestamp differs (to the minute).
    """
    print("\n[sync-dates] Building HTML timestamp map...")
    show_map, movie_map = build_html_date_map(html_files)
    n_eps = sum(len(v["episodes"]) for v in show_map.values())
    print(f"  HTML: {n_eps} episode(s) across {len(show_map)} show(s), "
          f"{len(movie_map)} movie(s)")

    remove_movies:  list[dict] = []
    restore_movies: list[dict] = []
    remove_shows:   dict[str, dict] = {}  # title_lower -> {obj, seasons}
    restore_shows:  dict[str, dict] = {}  # title_lower -> {obj, seasons}

    # ── movies ────────────────────────────────────────────────────────────────
    for item in movies_raw:
        mov     = item.get("movie", {})
        title   = mov.get("title", "")
        title_l = title.lower()
        if title_l not in movie_map:
            continue
        simkl_at = item.get("last_watched_at") or ""
        html_at  = movie_map[title_l]["watched_at"]
        if not simkl_at or _to_minute(simkl_at) == _to_minute(html_at):
            continue
        ids  = mov.get("ids", {})
        jaar = movie_map[title_l]["jaar"]
        obj: dict = {"title": title, "ids": ids}
        try:
            obj["year"] = int(jaar)
        except (ValueError, TypeError):
            pass
        remove_movies.append(obj)
        restore_obj = dict(obj)
        restore_obj["watched_at"] = html_at
        restore_movies.append(restore_obj)
        print(f"  [movie] {title}: {simkl_at} -> {html_at}")

    # ── shows ─────────────────────────────────────────────────────────────────
    for item in shows_raw:
        show    = item.get("show", {})
        title   = show.get("title", "")
        title_l = title.lower()
        if title_l not in show_map:
            continue
        html_eps = show_map[title_l]["episodes"]
        ids  = show.get("ids", {})
        jaar = show.get("year", "")
        base_obj: dict = {"title": title, "ids": ids}
        try:
            base_obj["year"] = int(jaar)
        except (ValueError, TypeError):
            pass

        for season in item.get("seasons", []):
            s_num = season.get("number", 1)
            for ep in season.get("episodes", []):
                e_num    = ep.get("number")
                simkl_at = ep.get("watched_at") or ""
                html_at  = html_eps.get((s_num, e_num))
                if html_at is None or not simkl_at:
                    continue
                if _to_minute(simkl_at) == _to_minute(html_at):
                    continue
                print(f"  [serie] {title} s{s_num:02d}e{e_num:02d}: "
                      f"{simkl_at} -> {html_at}")
                if title_l not in remove_shows:
                    remove_shows[title_l]  = {"obj": base_obj, "seasons": {}}
                    restore_shows[title_l] = {"obj": base_obj, "seasons": {}}
                remove_shows[title_l]["seasons"].setdefault(s_num, []).append(
                    {"number": e_num})
                restore_shows[title_l]["seasons"].setdefault(s_num, {})[e_num] = html_at

    total_movie_fixes = len(remove_movies)
    total_ep_fixes = sum(
        sum(len(eps) for eps in info["seasons"].values())
        for info in remove_shows.values()
    )
    print(f"\n[sync-dates] Timestamps to fix: "
          f"{total_movie_fixes} movie(s), {total_ep_fixes} episode(s).")

    if total_movie_fixes == 0 and total_ep_fixes == 0:
        print("[sync-dates] Everything is already in sync.")
        return

    if dry_run:
        print("[dry-run] No changes made.")
        return

    # ── helpers ───────────────────────────────────────────────────────────────
    def _post(endpoint: str, payload: dict, label: str) -> None:
        resp = requests.post(f"{API_BASE}{endpoint}", headers=headers,
                             json=payload, timeout=60)
        if resp.status_code in (200, 201, 204):
            data = resp.json() if resp.content else {}
            print(f"  {label}: OK {data}")
        else:
            print(f"  {label}: ERROR {resp.status_code} {resp.text[:200]}")

    def _build_show_remove(title_l: str) -> list[dict]:
        info = remove_shows[title_l]
        obj = dict(info["obj"])
        obj["seasons"] = [
            {"number": s, "episodes": eps}
            for s, eps in sorted(info["seasons"].items())
        ]
        return [obj]

    def _build_show_restore(title_l: str) -> list[dict]:
        info = restore_shows[title_l]
        obj = dict(info["obj"])
        obj["seasons"] = [
            {"number": s,
             "episodes": [{"number": e, "watched_at": wat}
                          for e, wat in sorted(eps.items())]}
            for s, eps in sorted(info["seasons"].items())
        ]
        return [obj]

    # ── apply fixes ───────────────────────────────────────────────────────────
    if remove_movies:
        _post("/sync/history/remove", {"movies": remove_movies},
              f"remove {len(remove_movies)} movie(s)")
        _post("/sync/history", {"movies": restore_movies},
              f"restore {len(restore_movies)} movie(s) with HTML dates")

    for title_l in remove_shows:
        show_title = remove_shows[title_l]["obj"]["title"]
        n = sum(len(v) for v in remove_shows[title_l]["seasons"].values())
        _post("/sync/history/remove", {"shows": _build_show_remove(title_l)},
              f"remove {n} ep(s) of {show_title!r}")
        _post("/sync/history", {"shows": _build_show_restore(title_l)},
              f"restore {n} ep(s) of {show_title!r} with HTML dates")

    print("[sync-dates] Done.")


# ── date helpers ──────────────────────────────────────────────────────────────

def iso_to_html_date(iso: str) -> str:
    """
    Convert '2026-01-01T01:52:00Z' → '2026-01-01 Thu 01:52'
    (same format used in the existing HTML table).
    """
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return dt.strftime("%Y-%m-%d %a %H:%M")


def iso_date_part(iso: str) -> str:
    """Return just the YYYY-MM-DD part of an ISO string."""
    return iso[:10]


# ── HTML table helpers ────────────────────────────────────────────────────────

_TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL | re.IGNORECASE)
_TR_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)


def _clean(cell: str) -> str:
    text = re.sub(r"<[^>]+>", "", cell)
    return html.unescape(text).strip()


def _get_tbody(content: str) -> str:
    m = re.search(r"<tbody[^>]*>(.*)", content, re.DOTALL | re.IGNORECASE)
    if m:
        chunk = m.group(1)
        end = re.search(r"</tbody>", chunk, re.IGNORECASE)
        return chunk[: end.start()] if end else chunk
    return content


def get_max_row_number(content: str) -> int:
    """Return the highest integer in the first <td> of any data row."""
    max_n = 0
    for tr in _TR_RE.finditer(_get_tbody(content)):
        cells = [_clean(c.group(1)) for c in _TD_RE.finditer(tr.group(1))]
        if cells:
            try:
                n = int(cells[0])
                max_n = max(max_n, n)
            except ValueError:
                pass
    return max_n


def get_existing_episodes_from_files(paths: list[Path]) -> set:
    """
    Scan all given HTML files and return a unified deduplication key set:
      series : ("serie", title_lower, ep_lower)   e.g. ("serie", "plur1bus", "s01e01")
      movies : ("film",  title_lower)              title alone -- same film is the same
                                                    regardless of the date Simkl stored
    Checking all years prevents re-adding entries that already live in a
    previous year's file (e.g. PLUR1BUS s01e01 in 2025gekeken.html).
    """
    keys: set = set()
    for path in paths:
        content = path.read_text("utf-8")
        for tr in _TR_RE.finditer(_get_tbody(content)):
            cells = [_clean(c.group(1)) for c in _TD_RE.finditer(tr.group(1))]
            if len(cells) < 6:
                continue
            _, _date, typ, naam, _, ep = cells[:6]
            if typ.lower() == "serie":
                keys.add(("serie", naam.lower(), ep.lower()))
            elif typ.lower() == "film":
                keys.add(("film", naam.lower()))
    return keys


def make_row(num: int, date_str: str, item_type: str,
             name: str, year: int | str, ep: str, titel: str) -> str:
    """Return a complete <tr>…</tr> block."""
    ep_cell    = ep              if ep    else "&#xa0;"
    titel_cell = html.escape(titel) if titel else "&#xa0;"
    name_cell  = html.escape(name)
    return (
        f"\n<tr>\n"
        f"<td>{num}</td>\n"
        f"<td>{date_str}</td>\n"
        f"<td>{item_type}</td>\n"
        f"<td>{name_cell}</td>\n"
        f"<td>{year}</td>\n"
        f"<td>{ep_cell}</td>\n"
        f"<td>{titel_cell}</td>\n"
        f"<td>&#xa0;</td>\n"
        f"</tr>\n"
    )


def insert_rows_into_html(content: str, rows_html: str) -> str:
    """Insert rows_html just before </tbody> (or </table> if no tbody)."""
    if re.search(r"</tbody>", content, re.IGNORECASE):
        return re.sub(r"</tbody>", rows_html + "\n</tbody>", content,
                      count=1, flags=re.IGNORECASE)
    if re.search(r"</table>", content, re.IGNORECASE):
        return re.sub(r"</table>", rows_html + "\n</table>", content,
                      count=1, flags=re.IGNORECASE)
    return content + rows_html


# ── main logic ────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--year", type=int, default=2026,
                   help="Year to sync (default: 2026)")
    p.add_argument("--push-to-simkl", action="store_true",
                   help="Also upload HTML-only entries to Simkl /sync/history")
    p.add_argument("--sync-dates", action="store_true",
                   help="Update Simkl watched_at timestamps to match the HTML files")
    p.add_argument("--all-years", action="store_true",
                   help="With --sync-dates: scan all *gekeken.html files, not just --year")
    p.add_argument("--dry-run", action="store_true",
                   help="Print what would be added/uploaded without modifying anything")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    year = args.year
    html_file = CONTENT_DIR / f"{year}gekeken.html"

    if not html_file.exists():
        sys.exit(f"Error: {html_file} does not exist. Create it first.")

    # ── credentials ──────────────────────────────────────────────────────────
    cfg = load_config()
    client_id = cfg.get("client_id", "")
    if not client_id:
        client_id = prompt_client_id()
        # Save for next time
        CONFIG_FILE.write_text(json.dumps({"client_id": client_id}, indent=2), "utf-8")

    access_token = cfg.get("access_token", "")
    if not access_token:
        access_token = pin_authenticate(client_id)

    tmdb_api_key: str = (
        cfg.get("tmdb_api_key", "")
        or os.environ.get("TMDB_API_KEY", "")
    )
    if not tmdb_api_key:
        print("Note: no tmdb_api_key in .simkl_config.json — episode titles will be empty.")
        print("      Get a free key at https://www.themoviedb.org/settings/api and add")
        print("        \"tmdb_api_key\": \"YOUR_KEY\"  to .simkl_config.json")

    headers = get_headers(client_id, access_token)

    # ── fetch from Simkl ─────────────────────────────────────────────────────
    date_from = f"{year}-01-01T00:00:00Z"
    date_until = f"{year + 1}-01-01T00:00:00Z"

    print(f"\nFetching all movies from Simkl (filtering to {year} locally)...")
    movies_raw = fetch_all_items(headers, "movies")
    print(f"  -> {len(movies_raw)} movie(s) in watchlist")

    print(f"Fetching all shows from Simkl (filtering to {year} locally)...")
    shows_raw = fetch_all_items(headers, "shows")
    print(f"  -> {len(shows_raw)} show(s) in watchlist")

    # ── push HTML-only entries to Simkl (--push-to-simkl) ────────────────────
    if args.push_to_simkl:
        html_content_for_push = html_file.read_text("utf-8")
        all_html_rows = parse_html_rows(html_content_for_push)
        # Keep only rows whose watch-date falls in the target year
        html_rows_this_year = [
            r for r in all_html_rows
            if r["date"].startswith(str(year))
        ]
        simkl_known = build_simkl_known_set(movies_raw, shows_raw)

        html_only: list[dict] = []
        for r in html_rows_this_year:
            if r["type"] == "film":
                key = ("film", r["naam"].lower())
            elif r["type"] == "serie":
                ep_norm = r["ep"].strip().lower() if r["ep"] and r["ep"] != "\xa0" else ""
                key = ("serie", r["naam"].lower(), ep_norm)
            else:
                continue
            if key not in simkl_known:
                html_only.append(r)

        print(f"\n[push] HTML entries for {year} not yet in Simkl: {len(html_only)}")
        push_html_entries_to_simkl(headers, client_id, html_only, args.dry_run)

    # ── sync-dates: fix Simkl timestamps to match the HTML ───────────────────
    if args.sync_dates:
        if args.all_years:
            html_files_to_check = sorted(CONTENT_DIR.glob("*gekeken.html"))
        else:
            html_files_to_check = [html_file]
        print(f"\n[sync-dates] Checking {len(html_files_to_check)} file(s):")
        for f in html_files_to_check:
            print(f"  {f.name}")
        sync_dates_to_simkl(headers, movies_raw, shows_raw,
                            html_files_to_check, args.dry_run)

    # ── build flat list of (watched_at_iso, display_date, type, name, year, ep, titel) ──

    entry_list: list[tuple] = []

    # Movies
    for item in movies_raw:
        mov = item.get("movie", {})
        name = mov.get("title", "")
        mov_year = mov.get("year", "")
        # Simkl returns last_watched_at for movies
        watched_at = item.get("last_watched_at") or item.get("watched_at") or ""
        if not watched_at:
            continue
        # Guard: only include this year
        if not (date_from <= watched_at < date_until):
            continue
        # One-time rule: skip movies bulk-imported on 2026-02-20 with wrong dates
        if watched_at.startswith("2026-02-20"):
            continue
        entry_list.append((
            watched_at,
            iso_to_html_date(watched_at),
            "film",
            name,
            mov_year,
            "",   # no episode
            "",   # no episode title
        ))

    # Shows
    ep_title_cache: dict[int, dict] = {}  # simkl_id → {(s, e): title}

    for item in shows_raw:
        show = item.get("show", {})
        name = show.get("title", "")
        show_year = show.get("year", "")
        ids        = show.get("ids", {})
        simkl_id: int | None = ids.get("simkl")
        tmdb_id_show: str | None = ids.get("tmdb")

        for season in item.get("seasons", []):
            s_num = season.get("number", 1)
            for ep in season.get("episodes", []):
                e_num = ep.get("number")
                watched_at = ep.get("watched_at") or ""
                if not watched_at or e_num is None:
                    continue
                if not (date_from <= watched_at < date_until):
                    continue

                ep_str = f"s{s_num:02d}e{e_num:02d}"

                # Fetch episode titles on first encounter for this show
                if simkl_id is not None and simkl_id not in ep_title_cache:
                    print(f"  Fetching episode list for {name!r}...")
                    ep_title_cache[simkl_id] = fetch_episode_titles(
                        client_id, simkl_id, name,
                        tmdb_id=tmdb_id_show,
                        tmdb_api_key=tmdb_api_key,
                    )

                titel = ""
                if simkl_id is not None:
                    titel = ep_title_cache.get(simkl_id, {}).get((s_num, e_num), "")

                entry_list.append((
                    watched_at,
                    iso_to_html_date(watched_at),
                    "serie",
                    name,
                    show_year,
                    ep_str,
                    titel,
                ))

    # Sort chronologically
    entry_list.sort(key=lambda x: x[0])
    print(f"\nTotal entries fetched from Simkl for {year}: {len(entry_list)}")

    if not entry_list:
        print("Nothing to add.")
        return

    # ── load existing HTML and deduplicate (all years) ────────────────────────
    html_content = html_file.read_text("utf-8")
    all_html_files = sorted(CONTENT_DIR.glob("*gekeken.html"))
    existing = get_existing_episodes_from_files(all_html_files)

    new_entries = []
    for entry in entry_list:
        watched_at, dt_str, itype, name, yr, ep_str, titel = entry
        if itype == "serie":
            key = ("serie", name.lower(), ep_str.lower())
        else:
            key = ("film", name.lower())
        if key not in existing:
            new_entries.append(entry)

    print(f"New entries not yet in {html_file.name}: {len(new_entries)}")

    if not new_entries:
        print("Nothing new to add -- the file is already up to date.")
        return

    # ── build HTML rows ───────────────────────────────────────────────────────
    start_num = get_max_row_number(html_content) + 1
    rows_html = ""
    for i, entry in enumerate(new_entries):
        _, dt_str, itype, name, yr, ep_str, titel = entry
        rows_html += make_row(start_num + i, dt_str, itype, name, yr, ep_str, titel)

    # ── preview ───────────────────────────────────────────────────────────────
    print(f"\nRows to be added (numbered {start_num}-{start_num + len(new_entries) - 1}):")
    for i, entry in enumerate(new_entries):
        _, dt_str, itype, name, yr, ep_str, titel = entry
        ep_display = ep_str or "-"
        titel_display = f"  {titel}" if titel else ""
        print(f"  {start_num + i:4d}  {dt_str}  {itype:<5}  {name}  {ep_display}{titel_display}")

    if args.dry_run:
        print("\n[dry-run] File NOT modified.")
        return

    # ── write ─────────────────────────────────────────────────────────────────
    updated = insert_rows_into_html(html_content, rows_html)
    html_file.write_text(updated, "utf-8")
    print(f"\nDone! {len(new_entries)} row(s) added to {html_file}")


if __name__ == "__main__":
    main()
