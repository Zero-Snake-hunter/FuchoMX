#!/usr/bin/env python3
"""
Backend Testing Suite for Quiniela Liga MX API
Tests authentication, admin/seed endpoints, and data retrieval
"""

import requests
import json
import sys
from datetime import datetime
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Base URL from frontend .env
BASE_URL = "https://fantasy-jornada-v1.preview.emergentagent.com/api"

# Load environment for database access
load_dotenv('/app/backend/.env')

def clear_test_user():
    """Clear test user from database"""
    try:
        async def clear_user():
            mongo_url = os.environ['MONGO_URL']
            client = AsyncIOMotorClient(mongo_url)
            db = client[os.environ.get('DB_NAME', 'quiniela_db')]
            await db.users.delete_many({"email": "testuser@ligamx.com"})
            client.close()
        
        asyncio.run(clear_user())
    except Exception as e:
        print(f"Warning: Could not clear test user: {e}")

def clear_all_data():
    """Clear all test data from database"""
    try:
        async def clear_data():
            mongo_url = os.environ['MONGO_URL']
            client = AsyncIOMotorClient(mongo_url)
            db = client[os.environ.get('DB_NAME', 'quiniela_db')]
            await db.teams.delete_many({})
            await db.jornadas.delete_many({})
            await db.matches.delete_many({})
            await db.users.delete_many({"email": "testuser@ligamx.com"})
            client.close()
        
        asyncio.run(clear_data())
    except Exception as e:
        print(f"Warning: Could not clear data: {e}")

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_test(test_name, status, details=""):
    color = Colors.GREEN if status == "PASS" else Colors.RED if status == "FAIL" else Colors.YELLOW
    print(f"{color}[{status}]{Colors.END} {test_name}")
    if details:
        print(f"    {details}")

def test_auth_register():
    """Test user registration"""
    print(f"\n{Colors.BLUE}=== TESTING AUTH REGISTRATION ==={Colors.END}")
    
    # Clear existing user first
    clear_test_user()
    
    # Test valid registration
    test_user = {
        "email": "testuser@ligamx.com",
        "password": "password123",
        "display_name": "Test User Liga MX"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=test_user, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data and "user" in data:
                log_test("Valid user registration", "PASS", f"Token received, user ID: {data['user']['id']}")
                return data["access_token"]
            else:
                log_test("Valid user registration", "FAIL", "Missing token or user in response")
                return None
        else:
            log_test("Valid user registration", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            return None
            
    except Exception as e:
        log_test("Valid user registration", "FAIL", f"Exception: {str(e)}")
        return None

def test_auth_duplicate_register():
    """Test duplicate user registration"""
    duplicate_user = {
        "email": "testuser@ligamx.com",
        "password": "password123",
        "display_name": "Duplicate User"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=duplicate_user, timeout=10)
        
        if response.status_code == 400:
            log_test("Duplicate user registration (should fail)", "PASS", "Correctly rejected duplicate email")
        else:
            log_test("Duplicate user registration (should fail)", "FAIL", f"Status: {response.status_code}, should be 400")
            
    except Exception as e:
        log_test("Duplicate user registration (should fail)", "FAIL", f"Exception: {str(e)}")

def test_auth_login():
    """Test user login"""
    print(f"\n{Colors.BLUE}=== TESTING AUTH LOGIN ==={Colors.END}")
    
    # Test valid login
    credentials = {
        "email": "testuser@ligamx.com",
        "password": "password123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=credentials, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data and "user" in data:
                log_test("Valid login", "PASS", f"Token received, user: {data['user']['display_name']}")
                return data["access_token"]
            else:
                log_test("Valid login", "FAIL", "Missing token or user in response")
                return None
        else:
            log_test("Valid login", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            return None
            
    except Exception as e:
        log_test("Valid login", "FAIL", f"Exception: {str(e)}")
        return None

def test_auth_invalid_login():
    """Test invalid login"""
    invalid_credentials = {
        "email": "testuser@ligamx.com",
        "password": "wrongpassword"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=invalid_credentials, timeout=10)
        
        if response.status_code == 401:
            log_test("Invalid login (should fail)", "PASS", "Correctly rejected invalid credentials")
        else:
            log_test("Invalid login (should fail)", "FAIL", f"Status: {response.status_code}, should be 401")
            
    except Exception as e:
        log_test("Invalid login (should fail)", "FAIL", f"Exception: {str(e)}")

def test_auth_me(token):
    """Test get current user"""
    if not token:
        log_test("Get current user info", "FAIL", "No token available")
        return
        
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/auth/me", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "id" in data and "email" in data and "display_name" in data:
                log_test("Get current user info", "PASS", f"User: {data['display_name']} ({data['email']})")
            else:
                log_test("Get current user info", "FAIL", "Missing required user fields")
        else:
            log_test("Get current user info", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            
    except Exception as e:
        log_test("Get current user info", "FAIL", f"Exception: {str(e)}")

def test_auth_me_no_token():
    """Test get current user without token"""
    try:
        response = requests.get(f"{BASE_URL}/auth/me", timeout=10)
        
        if response.status_code == 403 or response.status_code == 401:
            log_test("Get user info without token (should fail)", "PASS", "Correctly rejected request without token")
        else:
            log_test("Get user info without token (should fail)", "FAIL", f"Status: {response.status_code}, should be 401/403")
            
    except Exception as e:
        log_test("Get user info without token (should fail)", "FAIL", f"Exception: {str(e)}")

def test_auth_recover_password():
    """Test password recovery"""
    print(f"\n{Colors.BLUE}=== TESTING PASSWORD RECOVERY ==={Colors.END}")
    
    recovery_request = {
        "email": "testuser@ligamx.com"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/recover-password", json=recovery_request, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "message" in data:
                log_test("Password recovery request", "PASS", f"Message: {data['message']}")
            else:
                log_test("Password recovery request", "FAIL", "Missing message in response")
        else:
            log_test("Password recovery request", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            
    except Exception as e:
        log_test("Password recovery request", "FAIL", f"Exception: {str(e)}")

def test_admin_seed_teams():
    """Test seeding Liga MX teams"""
    print(f"\n{Colors.BLUE}=== TESTING ADMIN SEED TEAMS ==={Colors.END}")
    
    try:
        response = requests.post(f"{BASE_URL}/admin/seed-teams", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "count" in data and data["count"] == 18:
                log_test("Seed Liga MX teams", "PASS", f"Created {data['count']} teams")
                return True
            else:
                log_test("Seed Liga MX teams", "FAIL", f"Expected 18 teams, got: {data}")
                return False
        else:
            log_test("Seed Liga MX teams", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            return False
            
    except Exception as e:
        log_test("Seed Liga MX teams", "FAIL", f"Exception: {str(e)}")
        return False

def test_get_teams():
    """Test getting all teams"""
    try:
        response = requests.get(f"{BASE_URL}/teams", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "teams" in data and len(data["teams"]) == 18:
                log_test("Get all teams", "PASS", f"Retrieved {len(data['teams'])} teams")
                # Verify team structure
                team = data["teams"][0]
                if "id" in team and "name" in team and "short_name" in team:
                    log_test("Team data structure", "PASS", f"Sample team: {team['name']} ({team['short_name']})")
                else:
                    log_test("Team data structure", "FAIL", "Missing required team fields")
                return True
            else:
                log_test("Get all teams", "FAIL", f"Expected 18 teams, got: {len(data.get('teams', []))}")
                return False
        else:
            log_test("Get all teams", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            return False
            
    except Exception as e:
        log_test("Get all teams", "FAIL", f"Exception: {str(e)}")
        return False

def test_admin_seed_jornada():
    """Test creating jornada with matches"""
    print(f"\n{Colors.BLUE}=== TESTING ADMIN SEED JORNADA ==={Colors.END}")
    
    try:
        response = requests.post(f"{BASE_URL}/admin/seed-jornada", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "jornada_id" in data and "matches_count" in data:
                log_test("Create jornada with matches", "PASS", f"Jornada ID: {data['jornada_id']}, Matches: {data['matches_count']}")
                return True
            else:
                log_test("Create jornada with matches", "FAIL", f"Missing jornada_id or matches_count: {data}")
                return False
        else:
            log_test("Create jornada with matches", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            return False
            
    except Exception as e:
        log_test("Create jornada with matches", "FAIL", f"Exception: {str(e)}")
        return False

def test_get_current_jornada():
    """Test getting current jornada with matches"""
    try:
        response = requests.get(f"{BASE_URL}/jornadas/current", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "jornada" in data:
                jornada = data["jornada"]
                if "id" in jornada and "matches" in jornada:
                    matches_count = len(jornada["matches"])
                    log_test("Get current jornada", "PASS", f"Jornada week {jornada.get('week_number', 'N/A')} with {matches_count} matches")
                    
                    # Verify match structure
                    if matches_count > 0:
                        match = jornada["matches"][0]
                        if "home_team" in match and "away_team" in match:
                            log_test("Match data structure", "PASS", f"Sample match: {match['home_team']['name']} vs {match['away_team']['name']}")
                        else:
                            log_test("Match data structure", "FAIL", "Missing team data in matches")
                    return True
                else:
                    log_test("Get current jornada", "FAIL", "Missing id or matches in jornada")
                    return False
            else:
                log_test("Get current jornada", "FAIL", "Missing jornada in response")
                return False
        else:
            log_test("Get current jornada", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            return False
            
    except Exception as e:
        log_test("Get current jornada", "FAIL", f"Exception: {str(e)}")
        return False

def test_api_root():
    """Test API root endpoint"""
    print(f"\n{Colors.BLUE}=== TESTING API ROOT ==={Colors.END}")
    
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "message" in data and "endpoints" in data:
                log_test("API root endpoint", "PASS", f"Message: {data['message']}")
            else:
                log_test("API root endpoint", "FAIL", "Missing message or endpoints")
        else:
            log_test("API root endpoint", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
            
    except Exception as e:
        log_test("API root endpoint", "FAIL", f"Exception: {str(e)}")

def main():
    """Run all backend tests"""
    print(f"{Colors.BLUE}{'='*60}")
    print("QUINIELA LIGA MX - BACKEND API TESTING SUITE")
    print(f"Base URL: {BASE_URL}")
    print(f"{'='*60}{Colors.END}")
    
    # Clear all data first to ensure clean state
    print(f"{Colors.YELLOW}Clearing test data...{Colors.END}")
    clear_all_data()
    
    # Test API root
    test_api_root()
    
    # Test authentication flow
    token = test_auth_register()
    test_auth_duplicate_register()
    
    # Test login (get fresh token)
    login_token = test_auth_login()
    test_auth_invalid_login()
    
    # Use login token for authenticated requests
    if login_token:
        token = login_token
    
    test_auth_me(token)
    test_auth_me_no_token()
    test_auth_recover_password()
    
    # Test admin/seed endpoints in correct order
    print(f"{Colors.YELLOW}Testing admin/seed endpoints...{Colors.END}")
    teams_created = test_admin_seed_teams()
    if teams_created:
        test_get_teams()
        
        jornada_created = test_admin_seed_jornada()
        if jornada_created:
            test_get_current_jornada()
    
    print(f"\n{Colors.BLUE}{'='*60}")
    print("BACKEND TESTING COMPLETE")
    print(f"{'='*60}{Colors.END}")

if __name__ == "__main__":
    main()