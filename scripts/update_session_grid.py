#!/usr/bin/env python3
"""
update_session_grid.py

Reads session data from the Policy Camp sessions Google Sheet and updates
session-grid.html with a card grid grouped by time slot.

Usage:
  python3 scripts/update_session_grid.py
"""

import json
import os
import re
import sys
import logging
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)

SHEET_ID  = "1v_aSTs9qBR4ZpcOOK5SKnqrgzenZbYJAf1_lSgbRAbU"
KEY_FILE  = Path(__file__).parent.parent / "policy-camp-wesbite-4269360b43fb.json"
HTML_FILE = Path(__file__).parent.parent / "session-grid.html"


def get_sessions():
    creds = service_account.Credentials.from_service_account_file(
        KEY_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=creds)
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID, range="A1:Z100"
    ).execute()
    rows = result.get("values", [])

    # Row 0 has slot labels in columns B onwards
    slot_labels = [c.strip() for c in rows[0][1:] if c.strip()]

    # Build sessions: list of {slot_index, title, owner, location}
    sessions_by_slot = {i: [] for i in range(len(slot_labels))}

    i = 1
    while i < len(rows):
        row = rows[i]
        if not row or row[0].strip().lower() != "title":
            i += 1
            continue

        title_row    = rows[i]     if i     < len(rows) else []
        owner_row    = rows[i + 1] if i + 1 < len(rows) else []
        location_row = rows[i + 2] if i + 2 < len(rows) else []

        location = location_row[1].strip() if len(location_row) > 1 else ""

        for col_idx, slot_idx in enumerate(range(len(slot_labels))):
            col = col_idx + 1
            title = title_row[col].strip()    if col < len(title_row)    else ""
            owner = owner_row[col].strip()    if col < len(owner_row)    else ""
            if title:
                sessions_by_slot[slot_idx].append({
                    "title":    title,
                    "owner":    owner,
                    "location": location,
                })

        i += 4  # skip title, owner, location, blank row

    return slot_labels, sessions_by_slot


def build_html(slot_labels, sessions_by_slot):
    parts = ["\n"]
    for idx, label in enumerate(slot_labels):
        sessions = sessions_by_slot.get(idx, [])
        cards = "\n".join(
            f'''                <div class="session-card">
                    <div class="session-location">{s["location"]}</div>
                    <h3 class="session-title">{s["title"]}</h3>
                    <div class="session-owner">{s["owner"]}</div>
                </div>'''
            for s in sessions
        )
        parts.append(
            f'''        <div class="session-slot">
            <h2 class="slot-header">{label}</h2>
            <div class="slot-cards">
{cards}
            </div>
        </div>'''
        )
    parts.append("        ")
    return "\n".join(parts)


def inject(html, content):
    pattern = r"(<!-- BEGIN:SESSIONS -->)(.*?)(<!-- END:SESSIONS -->)"
    return re.sub(pattern, rf"\g<1>{content}\g<3>", html, flags=re.DOTALL)


def send_failure_email(error_msg):
    brevo_key = os.getenv("BREVO_API_KEY")
    if not brevo_key:
        return
    payload = json.dumps({
        "sender":      {"name": "Policy Camp Scripts", "email": "dave@bowsy.co.uk"},
        "to":          [{"email": "cholten99@gmail.com", "name": "Dave"}],
        "subject":     "Policy Camp Session Grid Update Failed",
        "htmlContent": f"<html><body><h2>Session Grid Update Failed</h2><pre>{error_msg}</pre></body></html>",
    }).encode()
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=payload,
        headers={"api-key": brevo_key, "Content-Type": "application/json"},
    )
    urllib.request.urlopen(req)


def main():
    try:
        slot_labels, sessions_by_slot = get_sessions()
        total = sum(len(v) for v in sessions_by_slot.values())
        log.info(f"Found {total} sessions across {len(slot_labels)} slots")

        html = HTML_FILE.read_text()
        html = inject(html, build_html(slot_labels, sessions_by_slot))
        HTML_FILE.write_text(html)
        log.info(f"Updated {HTML_FILE}")

    except Exception as e:
        log.error(f"Script error: {e}")
        try:
            send_failure_email(str(e))
        except Exception as mail_err:
            log.error(f"Failed to send alert email: {mail_err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
