#!/usr/bin/env python3
"""
Quick auth test to verify invalid token handling
"""

import requests
import json

BASE_URL = "https://fantasy-jornada-v1.preview.emergentagent.com/api"

def test_invalid_token():
    """Test invalid token scenario"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer invalid_token_here"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers, timeout=30)
        print(f"Invalid token test - Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 401
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_no_token():
    """Test no token scenario"""
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers, timeout=30)
        print(f"No token test - Status: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 403
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing invalid token scenarios...")
    
    result1 = test_invalid_token()
    result2 = test_no_token()
    
    print(f"\nResults:")
    print(f"Invalid token: {'✅ PASS' if result1 else '❌ FAIL'}")
    print(f"No token: {'✅ PASS' if result2 else '❌ FAIL'}")
    
    if result1 and result2:
        print("\n🎉 Both auth tests passed!")
    else:
        print("\n❌ Some auth tests failed")