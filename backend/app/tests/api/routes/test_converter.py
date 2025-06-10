import pytest
from fastapi.testclient import TestClient
from app.main import app
import io
import zipfile

client = TestClient(app)

# Sample SRT content for testing
SAMPLE_SRT = """1
00:00:01,000 --> 00:00:04,000
Hello, this is the first subtitle.

2
00:00:05,000 --> 00:00:08,000
This is the second subtitle
with multiple lines.

3
00:00:09,000 --> 00:00:12,000
And this is the third one!
"""

EXPECTED_TXT = """Hello, this is the first subtitle.
This is the second subtitle with multiple lines.
And this is the third one!"""

@pytest.fixture
def srt_file():
    """Create a sample SRT file for testing."""
    return io.StringIO(SAMPLE_SRT)

@pytest.fixture
def multiple_srt_files():
    """Create multiple sample SRT files for testing."""
    files = [
        ("files", ("test1.srt", SAMPLE_SRT.encode(), "text/plain")),
        ("files", ("test2.srt", SAMPLE_SRT.encode(), "text/plain"))
    ]
    return files

def test_convert_single_file_success(srt_file):
    """Test successful conversion of a single SRT file."""
    files = {"file": ("test.srt", srt_file.getvalue().encode(), "text/plain")}
    response = client.post("/api/v1/convert/srt-to-txt/single", files=files)
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert response.headers["content-disposition"] == 'attachment; filename="test.txt"'
    
    # Compare content (ignoring whitespace at the end of lines)
    received_lines = response.content.decode().strip().split('\n')
    expected_lines = EXPECTED_TXT.strip().split('\n')
    assert received_lines == expected_lines

def test_convert_single_file_wrong_extension():
    """Test error handling when uploading a non-SRT file."""
    files = {"file": ("test.txt", b"Some content", "text/plain")}
    response = client.post("/api/v1/convert/srt-to-txt/single", files=files)
    
    assert response.status_code == 200  # FastAPI returns 200 with error message
    assert response.json() == {"error": "File must be an SRT file"}

def test_convert_batch_success(multiple_srt_files):
    """Test successful batch conversion of multiple SRT files."""
    response = client.post("/api/v1/convert/srt-to-txt/batch", files=multiple_srt_files)
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"] == 'attachment; filename="converted_files.zip"'
    
    # Check ZIP contents
    zip_data = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_data) as zip_file:
        # Verify number of files
        assert len(zip_file.namelist()) == 2
        
        # Verify content of each file
        for filename in zip_file.namelist():
            assert filename.endswith('.txt')
            content = zip_file.read(filename).decode('utf-8').strip()
            expected_lines = EXPECTED_TXT.strip().split('\n')
            received_lines = content.split('\n')
            assert received_lines == expected_lines

def test_convert_batch_wrong_extension():
    """Test error handling when uploading non-SRT files in batch."""
    files = [
        ("files", ("test1.txt", b"Some content", "text/plain")),
        ("files", ("test2.txt", b"More content", "text/plain"))
    ]
    response = client.post("/api/v1/convert/srt-to-txt/batch", files=files)
    
    assert response.status_code == 200  # FastAPI returns 200 with error message
    assert response.json() == {"error": "All files must be SRT files"}

def test_convert_single_file_empty():
    """Test handling of empty SRT file."""
    files = {"file": ("test.srt", b"", "text/plain")}
    response = client.post("/api/v1/convert/srt-to-txt/single", files=files)
    
    assert response.status_code == 200
    assert response.content.decode().strip() == ""

def test_convert_single_file_special_characters():
    """Test handling of special characters in SRT file."""
    srt_content = """1
00:00:01,000 --> 00:00:04,000
Hello, こんにちは, 你好!

2
00:00:05,000 --> 00:00:08,000
Special chars: áéíóú ñ
"""
    files = {"file": ("test.srt", srt_content.encode('utf-8'), "text/plain")}
    response = client.post("/api/v1/convert/srt-to-txt/single", files=files)
    
    assert response.status_code == 200
    content = response.content.decode('utf-8').strip()
    expected = "Hello, こんにちは, 你好!\nSpecial chars: áéíóú ñ"
    assert content == expected

def test_convert_single_file_malformed_srt():
    """Test handling of malformed SRT file."""
    malformed_srt = """Not a proper SRT format
This is just plain text
Without timestamps or numbers"""
    
    files = {"file": ("test.srt", malformed_srt.encode(), "text/plain")}
    response = client.post("/api/v1/convert/srt-to-txt/single", files=files)
    
    assert response.status_code == 200
    content = response.content.decode().strip()
    expected = "Not a proper SRT format This is just plain text Without timestamps or numbers"
    assert content == expected

def test_convert_batch_single_file():
    """Test batch conversion with single file."""
    files = [("files", ("test1.srt", SAMPLE_SRT.encode(), "text/plain"))]
    response = client.post("/api/v1/convert/srt-to-txt/batch", files=files)
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    
    zip_data = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_data) as zip_file:
        assert len(zip_file.namelist()) == 1
        content = zip_file.read(zip_file.namelist()[0]).decode('utf-8').strip()
        expected_lines = EXPECTED_TXT.strip().split('\n')
        received_lines = content.split('\n')
        assert received_lines == expected_lines 
