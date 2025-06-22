import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

@pytest.fixture
def notion_token():
    return "fake-notion-token"

@patch("app.core.notion_integration.fetch_all_pages")
@patch("app.core.notion_integration.fetch_page_content")
@patch("app.core.qdrant_service.store_document")
def test_sync_notion_pages_success(mock_store, mock_content, mock_pages, notion_token):
    mock_pages.return_value = [
        {"id": "page1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "Test Page"}]}}},
        {"id": "page2", "properties": {"Name": {"type": "title", "title": [{"plain_text": "Empty Page"}]}}},
    ]
    mock_content.side_effect = ["Some content", ""]
    mock_store.return_value = None
    response = client.post(
        "/notion/sync",
        json={"notion_token": notion_token},
        headers={"Authorization": "Bearer test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["synced_pages"] == 1
    assert any("Synced: Test Page" in d for d in data["details"])
    assert any("Skipped empty page: Empty Page" in d for d in data["details"])

@patch("app.core.notion_integration.fetch_all_pages")
def test_sync_notion_pages_error(mock_pages, notion_token):
    mock_pages.side_effect = Exception("Notion error")
    response = client.post(
        "/notion/sync",
        json={"notion_token": notion_token},
        headers={"Authorization": "Bearer test"},
    )
    assert response.status_code == 400
    assert "Notion error" in response.text 
