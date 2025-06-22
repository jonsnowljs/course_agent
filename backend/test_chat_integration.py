#!/usr/bin/env python3
"""
Manual integration test for chat functionality.
Run this script to test the chat API endpoints manually.

Usage: python test_chat_integration.py
"""

import requests
import json
import time
import asyncio
from typing import Dict, Any


BASE_URL = "http://localhost:8000/api/v1"
TEST_USER_EMAIL = "admin@example.com"  # Use superuser credentials for testing
TEST_USER_PASSWORD = "password"


def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for API requests."""
    login_data = {
        "username": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    }
    
    response = requests.post(f"{BASE_URL}/login/access-token", data=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        print("💡 Make sure you have a test user or use superuser credentials")
        return {}
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_chat_health():
    """Test the chat health endpoint."""
    print("🔍 Testing chat health endpoint...")
    
    response = requests.get(f"{BASE_URL}/chat/health")
    
    if response.status_code == 200:
        data = response.json()
        status = data.get("status", "unknown")
        openai_configured = data.get("openai_configured", False)
        
        print(f"✅ Chat health check passed")
        print(f"   Status: {status}")
        print(f"   OpenAI configured: {openai_configured}")
        
        if not openai_configured:
            print("⚠️  Warning: OpenAI is not configured. Chat responses will fail.")
        
        return True
    else:
        print(f"❌ Chat health check failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def test_chat_non_streaming(headers: Dict[str, str]):
    """Test non-streaming chat message."""
    print("\n🔍 Testing non-streaming chat...")
    
    chat_data = {
        "message": "Hello, this is a test message. Can you help me understand my documents?",
        "context_limit": 5,
        "stream": False
    }
    
    response = requests.post(
        f"{BASE_URL}/chat/message",
        headers=headers,
        json=chat_data
    )
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Non-streaming chat test passed")
        print(f"   Message ID: {data.get('message_id', 'N/A')}")
        print(f"   Response length: {len(data.get('response', ''))}")
        print(f"   Context used: {len(data.get('context_used', []))} documents")
        print(f"   Response preview: {data.get('response', '')[:100]}...")
        return True
    else:
        print(f"❌ Non-streaming chat test failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False


def test_chat_streaming(headers: Dict[str, str]):
    """Test streaming chat message."""
    print("\n🔍 Testing streaming chat...")
    
    chat_data = {
        "message": "What are the main topics covered in my uploaded documents?",
        "context_limit": 3,
        "stream": True
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat/message",
            headers=headers,
            json=chat_data,
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Streaming chat test started")
            
            chunks_received = 0
            content_chunks = []
            metadata = None
            completion_data = None
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                            chunks_received += 1
                            
                            if data.get("type") == "metadata":
                                metadata = data
                                print(f"   📋 Metadata received - Message ID: {data.get('message_id')}")
                                print(f"       Context used: {len(data.get('context_used', []))} documents")
                            
                            elif data.get("type") == "content":
                                content_chunks.append(data.get("content", ""))
                                print(f"   📝 Content chunk: '{data.get('content', '')}'", end="", flush=True)
                            
                            elif data.get("type") == "complete":
                                completion_data = data
                                print(f"\n   ✅ Stream completed")
                                print(f"       Full response length: {len(data.get('full_response', ''))}")
                                break
                                
                        except json.JSONDecodeError:
                            print(f"   ⚠️ Invalid JSON in stream: {line_str}")
            
            print(f"\n✅ Streaming chat test completed")
            print(f"   Total chunks received: {chunks_received}")
            print(f"   Content chunks: {len(content_chunks)}")
            
            if metadata and completion_data:
                print(f"   Message ID: {metadata.get('message_id')}")
                full_content = "".join(content_chunks)
                print(f"   Reconstructed content length: {len(full_content)}")
                return True
            else:
                print("❌ Missing metadata or completion data")
                return False
                
        else:
            print(f"❌ Streaming chat test failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Streaming chat test timed out")
        return False
    except Exception as e:
        print(f"❌ Streaming chat test error: {str(e)}")
        return False


def test_chat_edge_cases(headers: Dict[str, str]):
    """Test edge cases and error handling."""
    print("\n🔍 Testing edge cases...")
    
    # Test empty message
    print("   Testing empty message...")
    response = requests.post(
        f"{BASE_URL}/chat/message",
        headers=headers,
        json={"message": "", "stream": False}
    )
    
    if response.status_code == 400:
        print("   ✅ Empty message correctly rejected")
    else:
        print(f"   ❌ Empty message test failed: {response.status_code}")
    
    # Test whitespace-only message
    print("   Testing whitespace-only message...")
    response = requests.post(
        f"{BASE_URL}/chat/message",
        headers=headers,
        json={"message": "   \n\t   ", "stream": False}
    )
    
    if response.status_code == 400:
        print("   ✅ Whitespace-only message correctly rejected")
    else:
        print(f"   ❌ Whitespace-only message test failed: {response.status_code}")
    
    # Test very long message
    print("   Testing very long message...")
    long_message = "A" * 10000
    response = requests.post(
        f"{BASE_URL}/chat/message",
        headers=headers,
        json={"message": long_message, "stream": False}
    )
    
    if response.status_code in [200, 400]:  # Either accept or reject gracefully
        print("   ✅ Long message handled appropriately")
    else:
        print(f"   ❌ Long message test failed: {response.status_code}")


def test_unauthorized_access():
    """Test that chat endpoints require authentication."""
    print("\n🔍 Testing unauthorized access...")
    
    response = requests.post(
        f"{BASE_URL}/chat/message",
        json={"message": "Test", "stream": False}
    )
    
    if response.status_code == 401:
        print("✅ Unauthorized access correctly blocked")
        return True
    else:
        print(f"❌ Unauthorized access test failed: {response.status_code}")
        return False


def check_documents_exist(headers: Dict[str, str]):
    """Check if user has any documents uploaded."""
    print("\n🔍 Checking if user has documents...")
    
    response = requests.get(f"{BASE_URL}/documents/?limit=1", headers=headers)
    
    if response.status_code == 200:
        documents = response.json()
        if documents:
            print(f"✅ User has {len(documents)} document(s)")
            return True
        else:
            print("⚠️  User has no documents uploaded")
            print("💡 Upload some documents for better chat testing")
            return False
    else:
        print(f"❌ Could not check documents: {response.status_code}")
        return False


def main():
    """Run all chat integration tests."""
    print("🚀 Starting Chat Integration Tests")
    print("=" * 50)
    
    # Test health endpoint (no auth required)
    health_ok = test_chat_health()
    
    if not health_ok:
        print("\n❌ Health check failed. Stopping tests.")
        return
    
    # Get authentication
    print(f"\n🔐 Authenticating as {TEST_USER_EMAIL}...")
    headers = get_auth_headers()
    
    if not headers:
        print("❌ Authentication failed. Stopping tests.")
        return
    
    print("✅ Authentication successful")
    
    # Check if user has documents
    check_documents_exist(headers)
    
    # Test unauthorized access
    test_unauthorized_access()
    
    # Test edge cases
    test_chat_edge_cases(headers)
    
    # Test chat functionality
    non_streaming_ok = test_chat_non_streaming(headers)
    streaming_ok = test_chat_streaming(headers)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print(f"   Health check: {'✅' if health_ok else '❌'}")
    print(f"   Non-streaming chat: {'✅' if non_streaming_ok else '❌'}")
    print(f"   Streaming chat: {'✅' if streaming_ok else '❌'}")
    
    if health_ok and non_streaming_ok and streaming_ok:
        print("\n🎉 All core chat tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check the logs above.")
    
    print("\n💡 To test with actual documents:")
    print("   1. Upload some documents through the web interface")
    print("   2. Run this test again to see context-aware responses")


if __name__ == "__main__":
    main() 
