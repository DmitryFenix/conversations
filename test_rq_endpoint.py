#!/usr/bin/env python3
"""
Простой скрипт для проверки доступности RQ endpoints
"""
import requests
import sys

BASE_URL = "http://localhost:8000"

endpoints = [
    "/api/rq/stats",
    "/api/rq/jobs/recent?limit=5",
]

print("Testing RQ endpoints...")
print("=" * 60)

for endpoint in endpoints:
    url = f"{BASE_URL}{endpoint}"
    print(f"\nTesting: {url}")
    try:
        response = requests.get(url, timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
            print("✓ OK")
        else:
            print(f"Response: {response.text}")
            print("✗ FAILED")
    except Exception as e:
        print(f"✗ ERROR: {e}")

print("\n" + "=" * 60)
print("Done")


