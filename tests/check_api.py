"""
Простая проверка доступности API
Можно запустить даже без httpx
"""
import urllib.request
import urllib.error
import json
import sys
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def check_api():
    """Проверка доступности API"""
    try:
        url = f"{API_BASE_URL}/api/reviewer/sessions"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                print(f"✓ API is accessible at {API_BASE_URL}")
                print(f"✓ Found {len(data)} sessions")
                return True
            else:
                print(f"✗ API returned status {response.status}")
                return False
    except urllib.error.URLError as e:
        print(f"✗ Cannot connect to API at {API_BASE_URL}")
        print(f"  Error: {e}")
        print("\nMake sure:")
        print("  1. API server is running")
        print("  2. Docker containers are up: docker compose up -d")
        print("  3. API is accessible at the specified URL")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("API Availability Check")
    print("=" * 60)
    print(f"Checking: {API_BASE_URL}")
    print()
    
    if check_api():
        print("\n✓ API is ready for testing!")
        sys.exit(0)
    else:
        print("\n✗ API is not available")
        sys.exit(1)

