import os
import requests
from urllib.parse import urlencode
from app.core.config import settings

NOTION_OAUTH_AUTHORIZE_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_OAUTH_TOKEN_URL = "https://api.notion.com/v1/oauth/token"

CLIENT_ID = os.getenv("NOTION_CLIENT_ID", getattr(settings, "NOTION_CLIENT_ID", None))
CLIENT_SECRET = os.getenv("NOTION_CLIENT_SECRET", getattr(settings, "NOTION_CLIENT_SECRET", None))
REDIRECT_URI = os.getenv("NOTION_REDIRECT_URI", getattr(settings, "NOTION_REDIRECT_URI", None))


def get_authorization_url(state: str) -> str:
    params = {
        "owner": "user",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "state": state,
    }
    return f"{NOTION_OAUTH_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code_for_token(code: str) -> str:
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    auth = (CLIENT_ID, CLIENT_SECRET)
    headers = {"Content-Type": "application/json"}
    resp = requests.post(NOTION_OAUTH_TOKEN_URL, json=data, auth=auth, headers=headers)
    if resp.status_code != 200:
        raise Exception(f"Failed to exchange code for token: {resp.text}")
    return resp.json()["access_token"] 
