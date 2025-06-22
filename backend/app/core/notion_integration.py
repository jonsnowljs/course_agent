import requests
from typing import List, Dict, Any

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

class NotionAPIError(Exception):
    pass

def fetch_all_pages(notion_token: str) -> List[Dict[str, Any]]:
    """
    Fetch all pages accessible by the user from the Notion API.
    Returns a list of page objects.
    """
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    pages = []
    has_more = True
    next_cursor = None
    while has_more:
        payload = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor
        resp = requests.post(f"{NOTION_API_URL}/search", headers=headers, json=payload)
        if resp.status_code != 200:
            raise NotionAPIError(f"Failed to fetch pages: {resp.text}")
        data = resp.json()
        for result in data.get("results", []):
            if result["object"] == "page":
                pages.append(result)
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")
    return pages

def fetch_page_content(notion_token: str, page_id: str) -> str:
    """
    Fetch the plain text content of a Notion page by recursively retrieving its blocks.
    """
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    blocks = []
    has_more = True
    next_cursor = None
    while has_more:
        url = f"{NOTION_API_URL}/blocks/{page_id}/children?page_size=100"
        if next_cursor:
            url += f"&start_cursor={next_cursor}"
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            raise NotionAPIError(f"Failed to fetch page content: {resp.text}")
        data = resp.json()
        blocks.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")
    # Extract text from blocks
    texts = []
    for block in blocks:
        if block["type"] in ("paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item", "to_do", "quote", "callout"):
            rich_text = block[block["type"]].get("rich_text", [])
            for rt in rich_text:
                if rt["type"] == "text":
                    texts.append(rt["text"]["content"])  # Only plain text for now
    return "\n".join(texts) 
