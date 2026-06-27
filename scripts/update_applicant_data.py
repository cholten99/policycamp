#!/usr/bin/env python3
"""
update_applicant_data.py

Reads applicant data from the Policy Camp Google Sheet and updates
applicant-data.html with counts, lists, and word clouds per column.

Usage:
  python3 scripts/update_applicant_data.py
"""

import re
import os
import sys
import json
import logging
import urllib.request
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from wordcloud import WordCloud, STOPWORDS
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)

SHEET_ID   = "1EwDe0JsYBO-uTS_S0nEouWHQPNogphWDOzGMqgO7arE"
KEY_FILE   = Path(__file__).parent.parent / "policy-camp-wesbite-c3bda78919f9.json"
HTML_FILE  = Path(__file__).parent.parent / "applicant-data.html"
IMAGES_DIR = Path(__file__).parent.parent / "assets" / "images"

MULTIPLE_CHOICE = {"D", "E", "F", "H", "K", "L", "M", "P"}
COUNT_TABLE     = {"G"}
FREE_LIST       = {"I"}

DIETARY_ALIASES = {
    "pescetarian": "Pescatarian",
    "pescatarian": "Pescatarian",
    "vegetarian":  "Vegetarian",
    "vegan":       "Vegan",
    "halal":       "Halal",
    "gluten free": "Gluten free",
    "gluten-free": "Gluten free",
    "dairy free":  "Dairy free",
    "dairy-free":  "Dairy free",
}

NAVY = "#102231"
TEAL = "#128b84"
CREAM = "#f8f4ed"


def get_sheet_service():
    creds = service_account.Credentials.from_service_account_file(
        KEY_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    return build("sheets", "v4", credentials=creds)


def fetch_column(service, col):
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=f"{col}2:{col}10000"
    ).execute()
    rows = result.get("values", [])
    return [r[0].strip() for r in rows if r and r[0].strip()]


BLANK_RESPONSES = {
    "", "n/a", "na", "n.a", "n.a.", "none", "no", "nil", "-", "–", "—", "none.",
    "no requirements", "no dietary requirements", "no accessibility needs",
    "no accessibility requirements", "none known", "none that i know of",
    "none at this time", "nothing", "not applicable",
}


def normalize_dietary(value):
    return DIETARY_ALIASES.get(value.lower().strip(), value.strip().title())


def filter_blanks(values):
    return [v for v in values if v.lower().strip(".").strip() not in BLANK_RESPONSES]


def make_count_table(counter, scrollable=False):
    rows = "\n".join(
        f'                    <tr><td>{option}</td><td>{count}</td></tr>'
        for option, count in sorted(counter.items(), key=lambda x: -x[1])
    )
    table = f'<table class="data-table">\n{rows}\n                </table>'
    if scrollable:
        return f'\n                <div class="scrollable-widget">{table}</div>\n                '
    return f'\n                {table}\n                '


def make_free_list(values):
    items = "\n".join(
        f'                    <li>{v}</li>'
        for v in values
    )
    return f'\n                <div class="scrollable-widget"><ul class="free-list">\n{items}\n                </ul></div>\n                '


def make_word_cloud_from_frequencies(values, col):
    """Word cloud using whole entries as units — good for short repeated responses (e.g. 'how heard')."""
    normalised = [v.strip().title() for v in values]
    freqs = Counter(normalised)

    wc = WordCloud(
        width=900,
        height=450,
        background_color=CREAM,
        color_func=lambda *args, **kwargs: TEAL if hash(args[0]) % 2 == 0 else NAVY,
        prefer_horizontal=0.7,
        max_words=200,
    ).generate_from_frequencies(freqs)

    img_path = IMAGES_DIR / f"wordcloud-{col}.png"
    wc.to_file(str(img_path))
    log.info(f"Saved word cloud to {img_path}")
    return f'\n                <img src="assets/images/wordcloud-{col}.png" alt="Word cloud" class="wordcloud-img">\n                '


def make_word_cloud_from_text(values, col):
    """Word cloud using word frequency across all entries — good for free-text responses."""
    text = " ".join(values)

    wc = WordCloud(
        width=900,
        height=450,
        background_color=CREAM,
        color_func=lambda *args, **kwargs: TEAL if hash(args[0]) % 2 == 0 else NAVY,
        prefer_horizontal=0.7,
        max_words=150,
        stopwords=STOPWORDS | {"policy", "policies", "also", "us", "want", "would", "like", "one", "get"},
    ).generate(text)

    img_path = IMAGES_DIR / f"wordcloud-{col}.png"
    wc.to_file(str(img_path))
    log.info(f"Saved word cloud to {img_path}")
    return f'\n                <img src="assets/images/wordcloud-{col}.png" alt="Word cloud" class="wordcloud-img">\n                '


def inject(html, col, content):
    pattern = rf'(<!-- BEGIN:{col} -->)(.*?)(<!-- END:{col} -->)'
    replacement = rf'\g<1>{content}\g<3>'
    return re.sub(pattern, replacement, html, flags=re.DOTALL)


def send_failure_email(error_msg, brevo_key):
    html = f"""<html><body>
<h2>Policy Camp Applicant Data Update Failed</h2>
<pre>{error_msg}</pre>
</body></html>"""
    payload = json.dumps({
        "sender":      {"name": "Policy Camp Scripts", "email": "dave@bowsy.co.uk"},
        "to":          [{"email": "cholten99@gmail.com", "name": "Dave"}],
        "subject":     "Policy Camp Applicant Data Update Failed",
        "htmlContent": html,
    }).encode()
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=payload,
        headers={"api-key": brevo_key, "Content-Type": "application/json"},
    )
    urllib.request.urlopen(req)


def main():
    brevo_key = os.getenv("BREVO_API_KEY")

    try:
        service = get_sheet_service()
        html = HTML_FILE.read_text()

        for col in MULTIPLE_CHOICE:
            values = fetch_column(service, col)
            content = make_count_table(Counter(values))
            html = inject(html, col, content)
            log.info(f"Column {col}: {len(values)} responses")

        for col in COUNT_TABLE:
            values = fetch_column(service, col)
            content = make_count_table(Counter(values), scrollable=True)
            html = inject(html, col, content)
            log.info(f"Column {col}: {len(values)} responses")

        for col in FREE_LIST:
            values = filter_blanks(fetch_column(service, col))
            content = make_free_list(values)
            html = inject(html, col, content)
            log.info(f"Column {col}: {len(values)} responses after filtering")

        # J: dietary — normalize variants and show as scrollable count table
        values = filter_blanks(fetch_column(service, "J"))
        normalised = [normalize_dietary(v) for v in values]
        content = make_count_table(Counter(normalised), scrollable=True)
        html = inject(html, "J", content)
        log.info(f"Column J: {len(normalised)} dietary responses")

        # O: short repeated entries — use whole-entry frequency cloud
        values = fetch_column(service, "O")
        html = inject(html, "O", make_word_cloud_from_frequencies(values, "O"))
        log.info(f"Column O: {len(values)} responses")

        # N: unique free-text — scrollable list of all responses
        values = fetch_column(service, "N")
        html = inject(html, "N", make_free_list(values))
        log.info(f"Column N: {len(values)} responses")

        HTML_FILE.write_text(html)
        log.info(f"Updated {HTML_FILE}")

    except Exception as e:
        log.error(f"Script error: {e}")
        if brevo_key:
            try:
                send_failure_email(str(e), brevo_key)
            except Exception as mail_err:
                log.error(f"Failed to send alert email: {mail_err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
