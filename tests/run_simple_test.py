"""
Максимально простой тест, который можно запустить даже без установленных библиотек
Использует только стандартную библиотеку Python
"""
import urllib.request
import urllib.error
import json
import sys

API_URL = "http://localhost:8000"

def test_api():
    """Простая проверка API"""
    print("Testing API at", API_URL)
    print("-" * 60)
    
    try:
        # Проверка доступности
        url = f"{API_URL}/api/reviewer/sessions"
        print(f"GET {url}")
        
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            print(f"✓ API is accessible")
            print(f"✓ Response status: {response.status}")
            print(f"✓ Found {len(data)} sessions")
            return True
            
    except urllib.error.URLError as e:
        print(f"✗ Cannot connect: {e}")
        print("\nMake sure API is running:")
        print("  docker compose up -d")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Simple API Test")
    print("=" * 60)
    print()
    
    success = test_api()
    print()
    print("=" * 60)
    
    if success:
        print("✓ Test PASSED")
        sys.exit(0)
    else:
        print("✗ Test FAILED")
        sys.exit(1)

