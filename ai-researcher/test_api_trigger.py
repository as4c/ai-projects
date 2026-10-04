#!/usr/bin/env python3
"""
Test script for API trigger call endpoint
"""
import requests
import json

# API endpoint
BASE_URL = "http://localhost:8000"  # Change to your server URL
API_ENDPOINT = f"{BASE_URL}/api/trigger-call/"

# Test payload
payload = {
    "event_name": "gyantv_survey",
    "phone_number": "+917491073491",  # Replace with your verified number
    "name": "Rahul Sharma",
    "gender": "male",
    "age": "28"
}

print("=" * 60)
print("Testing API Trigger Call Endpoint")
print("=" * 60)
print(f"\n📡 Endpoint: {API_ENDPOINT}")
print(f"\n📦 Payload:")
print(json.dumps(payload, indent=2))

try:
    response = requests.post(API_ENDPOINT, json=payload)

    print(f"\n📊 Response Status: {response.status_code}")
    print(f"📄 Response Body:")
    print(json.dumps(response.json(), indent=2))

    if response.status_code == 201:
        print("\n✅ Call triggered successfully!")
        data = response.json()
        print(f"   Call SID: {data.get('call_sid')}")
        print(f"   Event Name: {data.get('event_name')}")
        print(f"   User: {data.get('user_data', {}).get('name')}")
    else:
        print("\n❌ Error occurred")

except requests.exceptions.ConnectionError:
    print("\n❌ Connection Error: Make sure Django server is running!")
    print(f"   Start server with: python manage.py runserver")
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "=" * 60)

