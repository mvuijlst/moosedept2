#!/usr/bin/env python3
"""Update content/gelezen/{YEAR}gelezen.html from boeken.tsuk.org.

The generated yearly archive supplies the list of read books. The script then fetches
only those books' detail pages for series and publication metadata.

Usage:
    python boeken_to_gelezen.py [--year YEAR] [--dry-run]
"""

import argparse
import html
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests


SCRIPT_DIR = Path(__file__).parent
CONTENT_DIR = SCRIPT_DIR / "content" / "gelezen"
DEFAULT_BASE_URL = "https://boeken.tsuk.org/"

_TR_RE = re.compile(r"<tr\b(?P<attrs>[^>]*)>(?P<body>.*?)</tr>", re.DOTALL | re.IGNORECASE)
_TD_RE = re.compile(r"<td\b[^>]*>(.*?)</td>", re.DOTALL | re.IGNORECASE)
_SOURCE_SLUG_RE = re.compile(r'\bdata-boeken-slug=["\']([^"\']+)["\']', re.IGNORECASE)


@dataclass(frozen=True)
class Book:
    slug: str
    read_date: str
    authors: str
    series: str
    series_number: str
    title: str
    publication_year: str
    pages: str
    rating: str


@dataclass(frozen=True)
class ArchiveEntry:
    url: str
    slug: str
    read_date: str
    authors: str
    title: str
    rating: int


@dataclass(frozen=True)
class ExistingRow:
    start: int
    end: int
    raw: str
    source_slug: str
    author: str
    title: str


def log(message: str = "") -> None:
    print(message, flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--year", type=int, default=date.today().year,
        help="Reading year to update (default: current year)",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=argparse.SUPPRESS)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show changes without modifying the yearly HTML file",
    )
    return parser.parse_args()


class ArchiveParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.entries: list[ArchiveEntry] = []
        self.current: dict[str, str] | None = None
        self.in_main = False
        self.capture_title = False
        self.capture_authors = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        classes = set(values.get("class", "").split())
        if tag == "li" and "archief-item" in classes:
            self.current = {}
            return
        if self.current is None:
            return
        if tag == "time" and "archief-item__date" in classes:
            self.current["date"] = values.get("datetime", "")
        elif tag == "span" and "archief-item__main" in classes:
            self.in_main = True
        elif tag == "a" and self.in_main and "url" not in self.current:
            self.current["url"] = urljoin(self.base_url, values.get("href", ""))
            self.current["title"] = ""
            self.capture_title = True
        elif tag == "span" and "archief-item__authors" in classes:
            self.current["authors"] = ""
            self.capture_authors = True

        rating_match = re.search(r"(\d+)\s+van\s+10", values.get("aria-label", ""))
        if rating_match:
            self.current["rating"] = rating_match.group(1)

    def handle_data(self, data: str) -> None:
        if self.current is None:
            return
        if self.capture_title:
            self.current["title"] += data
        elif self.capture_authors:
            self.current["authors"] += data

    def handle_endtag(self, tag: str) -> None:
        if self.current is None:
            return
        if tag == "a" and self.capture_title:
            self.capture_title = False
        elif tag == "span" and self.capture_authors:
            self.capture_authors = False
        elif tag == "span" and self.in_main:
            self.in_main = False
        elif tag == "li":
            required = ("url", "date", "authors", "title", "rating")
            missing = [key for key in required if not self.current.get(key, "").strip()]
            if missing:
                raise ValueError(f"archive entry is missing {', '.join(missing)}")
            url = self.current["url"]
            slug = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
            self.entries.append(ArchiveEntry(
                url=url,
                slug=slug,
                read_date=self.current["date"].strip(),
                authors=self.current["authors"].strip(),
                title=self.current["title"].strip().replace("\u2019", "'"),
                rating=int(self.current["rating"]),
            ))
            self.current = None


class DetailParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.series_parts: list[str] = []
        self.publication_parts: list[str] = []
        self.capture_series = False
        self.capture_publication = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        classes = set(values.get("class", "").split())
        if tag == "p" and "book-detail__series" in classes:
            self.capture_series = True
        elif tag == "p" and "book-detail__pub" in classes:
            self.capture_publication = True

    def handle_data(self, data: str) -> None:
        if self.capture_series:
            self.series_parts.append(data)
        elif self.capture_publication:
            self.publication_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "p":
            return
        if self.capture_series:
            self.capture_series = False
        elif self.capture_publication:
            self.capture_publication = False

    @property
    def series(self) -> str:
        return " ".join("".join(self.series_parts).split())

    @property
    def publication(self) -> str:
        return " ".join("".join(self.publication_parts).split())


def star_entities(value: int | str | None) -> str:
    if value in (None, ""):
        return ""
    try:
        rating = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid rating {value!r}") from exc
    if not 0 <= rating <= 10:
        raise ValueError(f"rating {rating} is outside 0-10")
    return "&#9733;" * ((rating + 1) // 2)


def fetch_html(session: requests.Session, url: str) -> str:
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not fetch {url}: {exc}") from exc
    return response.content.decode("utf-8")


def format_authors(value: str) -> str:
    names = [name.strip() for name in re.split(r"\s*(?:,|&|\ben\b|\band\b)\s*", value)
             if name.strip()]
    formatted = []
    for name in names:
        parts = name.split()
        formatted.append(f"{parts[-1]}, {' '.join(parts[:-1])}" if len(parts) > 1 else name)
    return "; ".join(formatted)


def detail_fields(page: str) -> tuple[str, str, str, str]:
    parser = DetailParser()
    parser.feed(page)

    series = parser.series
    series_number = ""
    series_match = re.fullmatch(r"(.*?)\s+#(.+)", series)
    if series_match:
        series, series_number = series_match.group(1), series_match.group(2)

    year_match = re.search(r"\b(1\d{3}|20\d{2})\b", parser.publication)
    pages_match = re.search(r"(\d[\d., ]*)\s*blz\b", parser.publication, re.IGNORECASE)
    publication_year = year_match.group(1) if year_match else ""
    pages = re.sub(r"\D", "", pages_match.group(1)) if pages_match else ""
    return series, series_number, publication_year, pages


def load_books(base_url: str, year: int) -> list[Book]:
    session = requests.Session()
    session.headers["User-Agent"] = "moosedept-boeken-to-gelezen/1.0"
    archive_url = urljoin(base_url, f"gelezen/{year}/")
    log(f"Fetching yearly archive: {archive_url}")

    parser = ArchiveParser(base_url)
    try:
        parser.feed(fetch_html(session, archive_url))
    except ValueError as exc:
        raise RuntimeError(f"Could not parse {archive_url}: {exc}") from exc

    entries = [entry for entry in parser.entries if entry.read_date.startswith(f"{year}-")]
    log(f"Found {len(entries)} read book(s); fetching their details...")
    books: list[Book] = []
    for index, entry in enumerate(entries, start=1):
        log(f"  [{index}/{len(entries)}] {entry.title}")
        series, series_number, publication_year, pages = detail_fields(
            fetch_html(session, entry.url)
        )
        books.append(Book(
            slug=entry.slug,
            read_date=entry.read_date,
            authors=format_authors(entry.authors),
            series=series,
            series_number=series_number,
            title=entry.title,
            publication_year=publication_year,
            pages=pages,
            rating=star_entities(entry.rating),
        ))
    return books


def clean_cell(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value)).strip()


def tbody_bounds(content: str) -> tuple[int, int]:
    opening = re.search(
        r'<tbody\b[^>]*\bid=["\']booksBody["\'][^>]*>', content, re.IGNORECASE
    )
    if not opening:
        raise RuntimeError('Target file has no <tbody id="booksBody">')
    closing = re.search(r"</tbody>", content[opening.end():], re.IGNORECASE)
    if not closing:
        raise RuntimeError('Target file has no closing </tbody>')
    return opening.end(), opening.end() + closing.start()


def parse_existing_rows(body: str) -> list[ExistingRow]:
    rows: list[ExistingRow] = []
    for match in _TR_RE.finditer(body):
        cells = [clean_cell(cell) for cell in _TD_RE.findall(match.group("body"))]
        if len(cells) < 5:
            continue
        slug_match = _SOURCE_SLUG_RE.search(match.group("attrs"))
        rows.append(ExistingRow(
            start=match.start(),
            end=match.end(),
            raw=match.group(0),
            source_slug=html.unescape(slug_match.group(1)) if slug_match else "",
            author=cells[1],
            title=cells[4],
        ))
    return rows


def normalized(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.casefold())
    return " ".join(re.findall(r"[a-z0-9]+", folded.encode("ascii", "ignore").decode()))


def legacy_match(book: Book, row: ExistingRow) -> bool:
    if row.source_slug or normalized(book.authors) != normalized(row.author):
        return False
    wanted = normalized(book.title)
    existing = normalized(row.title)
    return wanted == existing or SequenceMatcher(None, wanted, existing).ratio() >= 0.9


def make_row(book: Book, newline: str) -> str:
    cells = (
        book.read_date,
        book.authors,
        book.series,
        book.series_number,
        book.title,
        book.publication_year,
        book.pages,
        book.rating,
    )
    lines = [f'<tr data-boeken-slug="{html.escape(book.slug, quote=True)}">']
    lines.extend(f"    <td>{html.escape(cell) if index != 7 else cell}</td>"
                 for index, cell in enumerate(cells))
    lines.append("</tr>")
    return newline.join(lines)


def updated_content(content: str, books: list[Book]) -> tuple[str, list[Book], list[Book]]:
    body_start, body_end = tbody_bounds(content)
    body = content[body_start:body_end]
    rows = parse_existing_rows(body)
    newline = "\r\n" if "\r\n" in content else "\n"

    managed = {row.source_slug: row for row in rows if row.source_slug}
    if len(managed) != sum(bool(row.source_slug) for row in rows):
        raise RuntimeError("Target file contains duplicate data-boeken-slug values")

    used_legacy: set[ExistingRow] = set()
    replacements: list[tuple[int, int, str]] = []
    additions: list[Book] = []
    updates: list[Book] = []

    for book in books:
        row = managed.get(book.slug)
        if row is None:
            row = next(
                (candidate for candidate in rows
                 if candidate not in used_legacy and legacy_match(book, candidate)),
                None,
            )
            if row is not None:
                used_legacy.add(row)

        rendered = make_row(book, newline)
        if row is None:
            additions.append(book)
        elif row.raw != rendered:
            replacements.append((row.start, row.end, rendered))
            updates.append(book)

    for start, end, replacement in sorted(replacements, reverse=True):
        body = body[:start] + replacement + body[end:]

    if additions:
        appended = (newline * 2).join(make_row(book, newline) for book in additions)
        body = body.rstrip() + newline * 2 + appended + newline

    return content[:body_start] + body + content[body_end:], updates, additions


def print_changes(label: str, books: list[Book]) -> None:
    if not books:
        return
    print(f"\n{label} ({len(books)}):")
    for book in books:
        print(f"  {book.read_date}  {book.authors:<28}  {book.title}")


def main() -> None:
    args = parse_args()
    html_file = CONTENT_DIR / f"{args.year}gelezen.html"
    if not html_file.exists():
        sys.exit(f"Error: {html_file} does not exist. Create it first.")

    try:
        books = load_books(args.base_url, args.year)
    except RuntimeError as exc:
        sys.exit(f"Error: {exc}")

    log(f"Comparing {len(books)} book(s) with {html_file.name}...")
    original = html_file.read_bytes().decode("utf-8")
    try:
        updated, changed, added = updated_content(original, books)
    except RuntimeError as exc:
        sys.exit(f"Error: {exc}")

    print_changes("Rows to update", changed)
    print_changes("Rows to add", added)
    if not changed and not added:
        print(f"{html_file.name} is already up to date.")
        return

    if args.dry_run:
        print("\n[dry-run] File NOT modified.")
        return

    html_file.write_bytes(updated.encode("utf-8"))
    print(f"\nDone! Updated {len(changed)} and added {len(added)} row(s) in {html_file}.")


if __name__ == "__main__":
    main()