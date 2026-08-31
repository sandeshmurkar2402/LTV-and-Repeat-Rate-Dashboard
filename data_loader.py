"""Handles authenticated reads from the Google Sheet and refresh/caching policy."""
import os
from datetime import datetime, timedelta

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

SHEET_ID = "11OZX1WdE_uuCqvuJ3lCE48OFhl8lPpxH_OuFqQcMNbc"
REPEAT_RATE_WORKSHEET = "Repeat_Rate_data"
LTV_WORKSHEET = "LTV"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

CRED_PATH = os.path.join(os.path.dirname(__file__), "cred1.json")
AUTO_REFRESH_HOUR = 10  # daily auto-refresh boundary, 10:00 local time


def _get_client():
    try:
        has_secret = "gcp_service_account" in st.secrets
    except Exception:
        has_secret = False

    if has_secret:
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=SCOPES
        )
    else:
        creds = Credentials.from_service_account_file(CRED_PATH, scopes=SCOPES)
    return gspread.authorize(creds)


def _daily_cache_bucket() -> str:
    """Returns a string that changes exactly once per day, at AUTO_REFRESH_HOUR."""
    now = datetime.now()
    boundary = now.replace(hour=AUTO_REFRESH_HOUR, minute=0, second=0, microsecond=0)
    bucket_date = now.date() if now >= boundary else (now.date() - timedelta(days=1))
    return bucket_date.isoformat()


def next_refresh_time() -> datetime:
    now = datetime.now()
    boundary = now.replace(hour=AUTO_REFRESH_HOUR, minute=0, second=0, microsecond=0)
    return boundary if now < boundary else boundary + timedelta(days=1)


@st.cache_data(show_spinner="Pulling latest data from Google Sheets...")
def _fetch_raw(cache_bucket: str):
    gc = _get_client()
    sh = gc.open_by_key(SHEET_ID)
    repeat_values = sh.worksheet(REPEAT_RATE_WORKSHEET).get_all_values()
    ltv_values = sh.worksheet(LTV_WORKSHEET).get_all_values()
    fetched_at = datetime.now()
    return repeat_values, ltv_values, fetched_at


def get_data(force_refresh: bool = False):
    """Returns (repeat_rate_raw_values, ltv_raw_values, fetched_at).

    Data is refetched when the user hits the manual refresh button, or
    automatically once per day after AUTO_REFRESH_HOUR.
    """
    if force_refresh:
        _fetch_raw.clear()
    return _fetch_raw(_daily_cache_bucket())
