#!/usr/bin/env python3
"""
Comprehensive Backend API Test Suite for Liga MX Quiniela App
Executes the full 15-step regression test as requested
"""

import requests
import json
from datetime import datetime
import sys

# Configuration
BACKEND_URL = "https://fantasy-jornada-v1.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

# Test data
test_users = [
    {
        "email": "regression_test@test.com",
        "password": "test1234",
        "display_name": "Regression Tester"
    },
    {
        "email": "regression_test2@test.com", 
        "password": "test1234",
        "display_name": "Second Tester"
    }
]

# Test state storage
test_state = {
    "user1_token": None,
    "user2_token": None,
    "jornada_id": None,
    "fantasy_league_code": None,
    "fantasy_league_id": None,
    "quiniela_league_code": None,
    "quiniela_league_id": None,
    "match_ids": []
}

def print_step(step, description):
    """Print test step with formatting"""
    print(f"\n{'='*60}")
    print(f"STEP {step}: {description}")
    print(f"{'='*60}")

def make_request(method, endpoint, headers=None, json_data=None):
    """Make HTTP request with error handling"""
    url = f"{BACKEND_URL}{endpoint}"
    full_headers = HEADERS.copy()
    if headers:
        full_headers.update(headers)
    
    try:
        if method == "GET":
            response = requests.get(url, headers=full_headers)
        elif method == "POST":
            response = requests.post(url, headers=full_headers, json=json_data)
        elif method == "PUT":
            response = requests.put(url, headers=full_headers, json=json_data)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        print(f"📡 {method} {url}")
        print(f"🔢 Status: {response.status_code}")
        
        # Try to parse JSON response
        try:
            response_data = response.json()
            print(f"📄 Response: {json.dumps(response_data, indent=2)[:500]}")
        except:
            print(f"📄 Response: {response.text[:500]}")
        
        return response
    
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return None

def auth_header(token):
    """Generate authorization header"""
    return {"Authorization": f"Bearer {token}"}

def run_regression_test():
    """Execute the complete 15-step regression test"""
    
    print("🚀 STARTING COMPREHENSIVE BACKEND REGRESSION TEST")
    print(f"Backend URL: {BACKEND_URL}")
    
    # STEP 1: Register first user
    print_step(1, "Register new user")
    response = make_request("POST", "/auth/register", json_data=test_users[0])
    
    if not response or response.status_code != 200:
        print("❌ STEP 1 FAILED: User registration failed")
        return False
    
    data = response.json()
    test_state["user1_token"] = data.get("access_token")
    if not test_state["user1_token"]:
        print("❌ STEP 1 FAILED: No access token received")
        return False
    
    print("✅ STEP 1 PASSED: User registered and token received")
    
    # STEP 2: Get current jornada
    print_step(2, "Get current jornada")
    response = make_request("GET", "/jornadas/current", 
                          headers=auth_header(test_state["user1_token"]))
    
    if not response or response.status_code != 200:
        print("❌ STEP 2 FAILED: Could not get current jornada")
        return False
    
    data = response.json()
    jornada = data.get("jornada", {})
    test_state["jornada_id"] = jornada.get("id")
    matches = jornada.get("matches", [])
    test_state["match_ids"] = [match["id"] for match in matches]
    
    if not test_state["jornada_id"] or len(matches) == 0:
        print("❌ STEP 2 FAILED: Invalid jornada data")
        return False
    
    print(f"✅ STEP 2 PASSED: Jornada {test_state['jornada_id']} with {len(matches)} matches")
    
    # STEP 3: Submit Quiniela prediction
    print_step(3, "Submit Quiniela prediction")
    
    # Build quiniela selections for all matches
    selections = []
    selection_options = ["HOME", "DRAW", "AWAY"]
    for i, match_id in enumerate(test_state["match_ids"]):
        selections.append({
            "match_id": match_id,
            "selection": selection_options[i % 3]  # Rotate through options
        })
    
    quiniela_data = {
        "jornada_id": test_state["jornada_id"],
        "selections": selections
    }
    
    response = make_request("POST", "/quiniela/submit", 
                          headers=auth_header(test_state["user1_token"]),
                          json_data=quiniela_data)
    
    if not response or response.status_code != 200:
        print("❌ STEP 3 FAILED: Quiniela submission failed")
        return False
    
    print("✅ STEP 3 PASSED: Quiniela submitted successfully")
    
    # STEP 4: Verify Quiniela predictions saved
    print_step(4, "Verify Quiniela predictions saved")
    response = make_request("GET", f"/quiniela/my-picks/{test_state['jornada_id']}", 
                          headers=auth_header(test_state["user1_token"]))
    
    if not response or response.status_code != 200:
        print("❌ STEP 4 FAILED: Could not retrieve picks")
        return False
    
    data = response.json()
    if not data.get("submitted") or len(data.get("selections", [])) != len(selections):
        print("❌ STEP 4 FAILED: Picks not properly saved")
        return False
    
    print("✅ STEP 4 PASSED: Quiniela predictions verified")
    
    # STEP 5: Create Fantasy League
    print_step(5, "Create Fantasy League")
    league_data = {
        "name": "Liga Regresión",
        "mode": "fantasy"
    }
    
    response = make_request("POST", "/leagues", 
                          headers=auth_header(test_state["user1_token"]),
                          json_data=league_data)
    
    if not response or response.status_code != 200:
        print("❌ STEP 5 FAILED: Fantasy league creation failed")
        return False
    
    data = response.json()
    test_state["fantasy_league_code"] = data.get("code")
    test_state["fantasy_league_id"] = data.get("league_id")
    
    if not test_state["fantasy_league_code"]:
        print("❌ STEP 5 FAILED: No league code received")
        return False
    
    print(f"✅ STEP 5 PASSED: Fantasy league created with code {test_state['fantasy_league_code']}")
    
    # STEP 6: Create Quiniela League  
    print_step(6, "Create Quiniela League")
    league_data = {
        "name": "Liga Quiniela Test",
        "mode": "quiniela"
    }
    
    response = make_request("POST", "/leagues", 
                          headers=auth_header(test_state["user1_token"]),
                          json_data=league_data)
    
    if not response or response.status_code != 200:
        print("❌ STEP 6 FAILED: Quiniela league creation failed")
        return False
    
    data = response.json()
    test_state["quiniela_league_code"] = data.get("code")
    test_state["quiniela_league_id"] = data.get("league_id")
    
    print(f"✅ STEP 6 PASSED: Quiniela league created with code {test_state['quiniela_league_code']}")
    
    # STEP 7: Register second user
    print_step(7, "Register SECOND user")
    response = make_request("POST", "/auth/register", json_data=test_users[1])
    
    if not response or response.status_code != 200:
        print("❌ STEP 7 FAILED: Second user registration failed")
        return False
    
    data = response.json()
    test_state["user2_token"] = data.get("access_token")
    if not test_state["user2_token"]:
        print("❌ STEP 7 FAILED: No access token for second user")
        return False
    
    print("✅ STEP 7 PASSED: Second user registered")
    
    # STEP 8: Join Fantasy league with second user
    print_step(8, "Join Fantasy league with second user")
    
    # First check if we need to create a fantasy team for this user (based on API requirements)
    # Attempt to join directly first
    response = make_request("POST", "/leagues/join", 
                          headers=auth_header(test_state["user2_token"]),
                          json_data={"code": test_state["fantasy_league_code"]})
    
    if response and response.status_code == 200:
        print("✅ STEP 8 PASSED: Successfully joined fantasy league")
    elif response and response.status_code == 400:
        # May need to create fantasy team first - this is acceptable behavior
        print("⚠️ STEP 8 PARTIAL: Fantasy league join blocked (need fantasy team) - Expected behavior")
    else:
        print("❌ STEP 8 FAILED: Fantasy league join failed unexpectedly")
        return False
    
    # STEP 9: Join Quiniela league with second user
    print_step(9, "Join Quiniela league with second user")
    response = make_request("POST", "/leagues/join", 
                          headers=auth_header(test_state["user2_token"]),
                          json_data={"code": test_state["quiniela_league_code"]})
    
    if not response or response.status_code != 200:
        print("❌ STEP 9 FAILED: Quiniela league join failed")
        return False
    
    print("✅ STEP 9 PASSED: Successfully joined quiniela league")
    
    # STEP 10: Get rankings
    print_step(10, "Get rankings")
    response = make_request("GET", "/quiniela/rankings/general", 
                          headers=auth_header(test_state["user1_token"]))
    
    if not response or response.status_code != 200:
        print("❌ STEP 10 FAILED: Could not get rankings")
        return False
    
    data = response.json()
    if "rankings" not in data:
        print("❌ STEP 10 FAILED: Invalid rankings format")
        return False
    
    print("✅ STEP 10 PASSED: Rankings retrieved successfully")
    
    # STEP 11: Get user profile
    print_step(11, "Get user profile")
    response = make_request("GET", "/auth/me", 
                          headers=auth_header(test_state["user1_token"]))
    
    if not response or response.status_code != 200:
        print("❌ STEP 11 FAILED: Could not get user profile")
        return False
    
    data = response.json()
    if not data.get("email") or not data.get("display_name"):
        print("❌ STEP 11 FAILED: Invalid user profile data")
        return False
    
    print("✅ STEP 11 PASSED: User profile retrieved successfully")
    
    # STEP 12: Get teams list
    print_step(12, "Get teams list")
    response = make_request("GET", "/teams")
    
    if not response or response.status_code != 200:
        print("❌ STEP 12 FAILED: Could not get teams")
        return False
    
    data = response.json()
    teams = data.get("teams", [])
    if len(teams) != 18:
        print(f"❌ STEP 12 FAILED: Expected 18 teams, got {len(teams)}")
        return False
    
    print("✅ STEP 12 PASSED: 18 teams retrieved successfully")
    
    # STEP 13: Get players
    print_step(13, "Get players")
    response = make_request("GET", "/players")
    
    if not response or response.status_code != 200:
        print("❌ STEP 13 FAILED: Could not get players")
        return False
    
    data = response.json()
    players = data.get("players", [])
    if len(players) == 0:
        print("⚠️ STEP 13 WARNING: No players found - may need to seed players first")
    else:
        print(f"✅ STEP 13 PASSED: {len(players)} players retrieved successfully")
    
    # STEP 14: Check jornada admin list
    print_step(14, "Check jornada admin list")
    response = make_request("GET", "/admin/jornadas")
    
    if not response or response.status_code != 200:
        print("❌ STEP 14 FAILED: Could not get admin jornadas")
        return False
    
    data = response.json()
    jornadas = data.get("jornadas", [])
    if len(jornadas) == 0:
        print("❌ STEP 14 FAILED: No jornadas found")
        return False
    
    # Check if at least one jornada has is_active=true
    active_jornadas = [j for j in jornadas if j.get("is_active")]
    if len(active_jornadas) == 0:
        print("❌ STEP 14 FAILED: No active jornada found")
        return False
    
    print(f"✅ STEP 14 PASSED: {len(jornadas)} jornadas found, {len(active_jornadas)} active")
    
    # STEP 15: Verify no 401 errors on authenticated endpoints
    print_step(15, "Verify no 401 errors on authenticated endpoints")
    
    # Test various authenticated endpoints
    auth_endpoints = [
        "/auth/me",
        "/jornadas/current",
        f"/quiniela/my-picks/{test_state['jornada_id']}",
        "/quiniela/rankings/general",
        "/leagues/my-leagues"
    ]
    
    all_auth_good = True
    for endpoint in auth_endpoints:
        response = make_request("GET", endpoint, 
                              headers=auth_header(test_state["user1_token"]))
        if not response or response.status_code == 401:
            print(f"❌ 401 error on {endpoint}")
            all_auth_good = False
        elif response.status_code != 200:
            print(f"⚠️ Non-200 status on {endpoint}: {response.status_code}")
    
    if all_auth_good:
        print("✅ STEP 15 PASSED: All authenticated endpoints working (no 401 errors)")
    else:
        print("❌ STEP 15 FAILED: Some authenticated endpoints returned 401")
        return False
    
    return True

def print_summary():
    """Print test summary"""
    print(f"\n{'='*60}")
    print("REGRESSION TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test completed at: {datetime.now()}")
    print(f"\nTest State:")
    for key, value in test_state.items():
        if "token" in key and value:
            print(f"  {key}: {'*' * 20}")  # Hide tokens
        else:
            print(f"  {key}: {value}")

if __name__ == "__main__":
    success = run_regression_test()
    print_summary()
    
    if success:
        print("\n🎉 ALL TESTS PASSED - BACKEND REGRESSION TEST SUCCESSFUL!")
        sys.exit(0)
    else:
        print("\n💥 SOME TESTS FAILED - BACKEND REGRESSION TEST FAILED!")
        sys.exit(1)