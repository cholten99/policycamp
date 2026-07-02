#!/usr/bin/env python3
"""
sync_applicants_to_kit.py

Reads email addresses from the Policy Camp applicant Google Sheet
and subscribes them to the Policy Camp Kit account.

Usage:
  python3 scripts/sync_applicants_to_kit.py            # adds subscribers (default)
  python3 scripts/sync_applicants_to_kit.py --dry-run  # log only, no changes
"""

import base64
import json
import os
import sys
import argparse
import logging
import urllib.request
from pathlib import Path

import requests
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger(__name__)

SHEET_ID      = "1EwDe0JsYBO-uTS_S0nEouWHQPNogphWDOzGMqgO7arE"
KIT_BASE      = "https://api.convertkit.com/v3"
KIT_FORM_ID   = "9321882"  # Abbey landing page


def get_opted_in_emails():
    creds = service_account.Credentials.from_service_account_info(
        json.loads(base64.b64decode(os.environ["POLICYCAMP_SA_JSON"])),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=creds)
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range="B2:P10000"
    ).execute()
    rows = result.get("values", [])
    emails = []
    for row in rows:
        email = row[0].strip() if len(row) > 0 else ""
        newsletter = row[14].strip() if len(row) > 14 else ""  # column P is index 14 (B=0)
        if email and newsletter.lower() == "yes":
            emails.append(email)
    return emails


def add_subscriber(email, api_key, dry_run):
    if dry_run:
        log.info(f"[DRY RUN] Would add: {email}")
        return True

    resp = requests.post(
        f"{KIT_BASE}/forms/{KIT_FORM_ID}/subscribe",
        headers={"Content-Type": "application/json"},
        json={"api_key": api_key, "email": email},
        timeout=10
    )
    if resp.status_code in (200, 201):
        log.info(f"Added: {email}")
        return True
    else:
        log.warning(f"Failed ({resp.status_code}) for {email}: {resp.text}")
        return False


def send_failure_email(error_msg, brevo_key):
    html = f"""<html><body>
<h2>Policy Camp Kit Sync Failed</h2>
<pre>{error_msg}</pre>
</body></html>"""
    payload = json.dumps({
        "sender":      {"name": "Policy Camp Scripts", "email": "dave@bowsy.co.uk"},
        "to":          [{"email": "cholten99@gmail.com", "name": "Dave"}],
        "subject":     "Policy Camp Kit Sync Failed",
        "htmlContent": html,
    }).encode()
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=payload,
        headers={"api-key": brevo_key, "Content-Type": "application/json"},
    )
    urllib.request.urlopen(req)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Log what would happen without adding subscribers")
    args = parser.parse_args()
    dry_run = args.dry_run

    api_key    = os.getenv("KIT_API_KEY")
    brevo_key  = os.getenv("BREVO_API_KEY")
    if not api_key:
        log.error("KIT_API_KEY not set in .env")
        sys.exit(1)

    if dry_run:
        log.info("=== DRY RUN — no changes will be made ===")
    else:
        log.info("=== LIVE RUN — subscribers will be added to Kit ===")

    try:
        emails = get_opted_in_emails()
        log.info(f"Found {len(emails)} opted-in email addresses in sheet")

        ok = fail = 0
        for email in emails:
            if add_subscriber(email, api_key, dry_run):
                ok += 1
            else:
                fail += 1

        log.info(f"Done — {ok} {'would be added' if dry_run else 'added'}, {fail} failed")

        if fail and brevo_key:
            send_failure_email(f"{fail} subscriber(s) failed to add — check logs for details.", brevo_key)

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
