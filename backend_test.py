#!/usr/bin/env python3
"""
Backend API Testing for Football Pool App
Tests all critical backend flows as requested in the review.
"""

import requests
import json
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://fantasy-jornada-v1.preview.emergentagent.com/api"
HEADERS = {"Content-Type": "application/json"}

class BackendTester:
    def __init__(self):
        self.access_token = None
        self.user_data = None
        self.jornada_data = None
        self.test_results = []
        self.failed_tests = []
        
    def log_result(self, test_name: str, success: bool, details: str = "", response: Optional[requests.Response] = None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        if response:
            result["response_code"] = response.status_code
            result["response_time"] = f"{response.elapsed.total_seconds():.3f}s"
            
        self.test_results.append(result)
        
        if not success:
            self.failed_tests.append(result)
            
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        if response:
            print(f"    Response: {response.status_code} in {response.elapsed.total_seconds():.3f}s")
    
    def make_request(self, method: str, endpoint: str, data: Dict[Any, Any] = None, use_auth: bool = False) -> Optional[requests.Response]:
        """Make HTTP request with proper error handling"""
        url = f"{BASE_URL}{endpoint}"
        headers = HEADERS.copy()
        
        if use_auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
            
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None
    
    # TEST FLOW 1: Authentication System
    def test_auth_flow(self):
        """Test complete authentication flow"""
        print("\n🔐 TESTING AUTHENTICATION FLOW...")
        
        # Generate unique test email
        test_email = f"testauth-{uuid.uuid4().hex[:8]}@test.com"
        test_password = "test1234"
        test_display_name = "Test Auth User"
        
        # 1. Register new user
        register_data = {
            "email": test_email,
            "password": test_password,
            "display_name": test_display_name
        }
        
        response = self.make_request("POST", "/auth/register", register_data)
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                self.access_token = data.get("access_token")
                self.user_data = data.get("user")
                
                if self.access_token and self.user_data:
                    self.log_result("Auth Register", True, f"User registered: {test_email}", response)
                else:
                    self.log_result("Auth Register", False, "Missing access_token or user data", response)
                    return
            except json.JSONDecodeError:
                self.log_result("Auth Register", False, "Invalid JSON response", response)
                return
        else:
            self.log_result("Auth Register", False, f"Registration failed", response)
            return
            
        # 2. Test /auth/me with valid token
        response = self.make_request("GET", "/auth/me", use_auth=True)
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                if data.get("email") == test_email:
                    self.log_result("Auth Me (Valid Token)", True, f"User data retrieved: {data.get('display_name')}", response)
                else:
                    self.log_result("Auth Me (Valid Token)", False, "User email mismatch", response)
            except json.JSONDecodeError:
                self.log_result("Auth Me (Valid Token)", False, "Invalid JSON response", response)
        else:
            self.log_result("Auth Me (Valid Token)", False, "Failed to get user data", response)
            
        # 3. Login with same credentials
        login_data = {
            "email": test_email,
            "password": test_password
        }
        
        response = self.make_request("POST", "/auth/login", login_data)
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                new_token = data.get("access_token")
                
                if new_token:
                    self.access_token = new_token  # Update token
                    self.log_result("Auth Login", True, f"Login successful with new token", response)
                else:
                    self.log_result("Auth Login", False, "No access_token in login response", response)
            except json.JSONDecodeError:
                self.log_result("Auth Login", False, "Invalid JSON response", response)
        else:
            self.log_result("Auth Login", False, "Login failed", response)
            
        # 4. Test /auth/me with new token
        response = self.make_request("GET", "/auth/me", use_auth=True)
        
        if response and response.status_code == 200:
            self.log_result("Auth Me (New Token)", True, "User data retrieved with new token", response)
        else:
            self.log_result("Auth Me (New Token)", False, "Failed with new token", response)
            
        # 5. Test with INVALID token
        original_token = self.access_token
        self.access_token = "invalid_token_here"
        
        response = self.make_request("GET", "/auth/me", use_auth=True)
        
        if response and response.status_code == 401:
            self.log_result("Auth Invalid Token", True, "Correctly returned 401 for invalid token", response)
        else:
            expected_code = 401
            actual_code = response.status_code if response else "No response"
            self.log_result("Auth Invalid Token", False, f"Expected 401, got {actual_code}", response)
            
        # Restore valid token
        self.access_token = original_token
        
        # 6. Test with NO token
        response = self.make_request("GET", "/auth/me", use_auth=False)
        
        if response and response.status_code == 403:
            self.log_result("Auth No Token", True, "Correctly returned 403 for missing token", response)
        else:
            expected_code = 403
            actual_code = response.status_code if response else "No response"
            self.log_result("Auth No Token", False, f"Expected 403, got {actual_code}", response)
    
    # TEST FLOW 2: Jornada System
    def test_jornada_system(self):
        """Test complete jornada management system"""
        print("\n📅 TESTING JORNADA SYSTEM...")
        
        # 1. Seed teams first
        response = self.make_request("POST", "/admin/seed-teams")
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                teams_count = data.get("count", 0)
                if teams_count >= 18:
                    self.log_result("Admin Seed Teams", True, f"Created {teams_count} teams", response)
                else:
                    self.log_result("Admin Seed Teams", False, f"Expected 18+ teams, got {teams_count}", response)
                    return
            except json.JSONDecodeError:
                self.log_result("Admin Seed Teams", False, "Invalid JSON response", response)
                return
        else:
            self.log_result("Admin Seed Teams", False, "Failed to seed teams", response)
            return
            
        # 2. Seed full season (17 jornadas)
        response = self.make_request("POST", "/admin/seed-season")
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                jornadas = data.get("jornadas", [])
                if len(jornadas) == 17:
                    self.log_result("Admin Seed Season", True, f"Created {len(jornadas)} jornadas", response)
                else:
                    self.log_result("Admin Seed Season", False, f"Expected 17 jornadas, got {len(jornadas)}", response)
                    return
            except json.JSONDecodeError:
                self.log_result("Admin Seed Season", False, "Invalid JSON response", response)
                return
        else:
            self.log_result("Admin Seed Season", False, "Failed to seed season", response)
            return
            
        # 3. List all jornadas
        response = self.make_request("GET", "/admin/jornadas")
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                jornadas = data.get("jornadas", [])
                total = data.get("total", 0)
                
                if total == 17:
                    # Check if jornada 1 is active
                    jornada_1 = next((j for j in jornadas if j.get("week_number") == 1), None)
                    if jornada_1 and jornada_1.get("is_active"):
                        self.log_result("Admin List Jornadas", True, f"17 jornadas exist, jornada 1 is active", response)
                        
                        # Store jornada 1 ID for later tests
                        self.jornada_1_id = jornada_1.get("id")
                        
                        # Find jornada 2 ID as well
                        jornada_2 = next((j for j in jornadas if j.get("week_number") == 2), None)
                        if jornada_2:
                            self.jornada_2_id = jornada_2.get("id")
                    else:
                        self.log_result("Admin List Jornadas", False, "Jornada 1 is not active", response)
                        return
                else:
                    self.log_result("Admin List Jornadas", False, f"Expected 17 jornadas, got {total}", response)
                    return
            except json.JSONDecodeError:
                self.log_result("Admin List Jornadas", False, "Invalid JSON response", response)
                return
        else:
            self.log_result("Admin List Jornadas", False, "Failed to list jornadas", response)
            return
            
        # 4. Get current jornada (should be week 1)
        response = self.make_request("GET", "/jornadas/current")
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                jornada = data.get("jornada", {})
                week_number = jornada.get("week_number")
                
                if week_number == 1:
                    self.jornada_data = jornada
                    self.log_result("Get Current Jornada (Week 1)", True, f"Current jornada is week {week_number}", response)
                else:
                    self.log_result("Get Current Jornada (Week 1)", False, f"Expected week 1, got {week_number}", response)
            except json.JSONDecodeError:
                self.log_result("Get Current Jornada (Week 1)", False, "Invalid JSON response", response)
        else:
            self.log_result("Get Current Jornada (Week 1)", False, "Failed to get current jornada", response)
            return
            
        # 5. Close jornada 1
        if hasattr(self, 'jornada_1_id'):
            response = self.make_request("POST", f"/admin/quiniela/cerrar-jornada/{self.jornada_1_id}")
            
            if response and response.status_code == 200:
                try:
                    data = response.json()
                    closed_jornada = data.get("closed_jornada", {})
                    next_jornada = data.get("next_jornada", {})
                    
                    if closed_jornada.get("week_number") == 1 and next_jornada.get("week_number") == 2:
                        self.log_result("Close Jornada 1", True, "Jornada 1 closed, jornada 2 activated", response)
                    else:
                        self.log_result("Close Jornada 1", False, "Unexpected jornada transition", response)
                except json.JSONDecodeError:
                    self.log_result("Close Jornada 1", False, "Invalid JSON response", response)
            else:
                self.log_result("Close Jornada 1", False, "Failed to close jornada 1", response)
        else:
            self.log_result("Close Jornada 1", False, "No jornada 1 ID available", None)
            
        # 6. List jornadas again to verify transition
        response = self.make_request("GET", "/admin/jornadas")
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                jornadas = data.get("jornadas", [])
                
                jornada_1 = next((j for j in jornadas if j.get("week_number") == 1), None)
                jornada_2 = next((j for j in jornadas if j.get("week_number") == 2), None)
                
                if (jornada_1 and not jornada_1.get("is_active") and jornada_1.get("status") == "finished" and
                    jornada_2 and jornada_2.get("is_active")):
                    self.log_result("Verify Jornada Transition", True, "Jornada 1 finished, jornada 2 active", response)
                else:
                    self.log_result("Verify Jornada Transition", False, "Jornada transition verification failed", response)
            except json.JSONDecodeError:
                self.log_result("Verify Jornada Transition", False, "Invalid JSON response", response)
        else:
            self.log_result("Verify Jornada Transition", False, "Failed to verify transition", response)
            
        # 7. Get current jornada again (should be week 2)
        response = self.make_request("GET", "/jornadas/current")
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                jornada = data.get("jornada", {})
                week_number = jornada.get("week_number")
                
                if week_number == 2:
                    self.log_result("Get Current Jornada (Week 2)", True, f"Current jornada is now week {week_number}", response)
                else:
                    self.log_result("Get Current Jornada (Week 2)", False, f"Expected week 2, got {week_number}", response)
            except json.JSONDecodeError:
                self.log_result("Get Current Jornada (Week 2)", False, "Invalid JSON response", response)
        else:
            self.log_result("Get Current Jornada (Week 2)", False, "Failed to get current jornada", response)
            
        # 8. Close jornada 2
        if hasattr(self, 'jornada_2_id'):
            response = self.make_request("POST", f"/admin/quiniela/cerrar-jornada/{self.jornada_2_id}")
            
            if response and response.status_code == 200:
                self.log_result("Close Jornada 2", True, "Jornada 2 closed successfully", response)
            else:
                self.log_result("Close Jornada 2", False, "Failed to close jornada 2", response)
        else:
            self.log_result("Close Jornada 2", False, "No jornada 2 ID available", None)
            
        # 9. Get current jornada (should be week 3)
        response = self.make_request("GET", "/jornadas/current")
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                jornada = data.get("jornada", {})
                week_number = jornada.get("week_number")
                
                if week_number == 3:
                    self.log_result("Get Current Jornada (Week 3)", True, f"Current jornada is now week {week_number}", response)
                else:
                    self.log_result("Get Current Jornada (Week 3)", False, f"Expected week 3, got {week_number}", response)
            except json.JSONDecodeError:
                self.log_result("Get Current Jornada (Week 3)", False, "Invalid JSON response", response)
        else:
            self.log_result("Get Current Jornada (Week 3)", False, "Failed to get current jornada", response)
    
    # TEST FLOW 3: Seed Jornada Auto-increment  
    def test_seed_jornada_auto_increment(self):
        """Test auto-increment feature of seed-jornada"""
        print("\n🔄 TESTING SEED JORNADA AUTO-INCREMENT...")
        
        # After previous tests, we should have 17 jornadas, so next should be 18
        response = self.make_request("POST", "/admin/seed-jornada")
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                week_number = data.get("week_number")
                
                if week_number == 18:
                    self.log_result("Seed Jornada Auto-increment", True, f"Created jornada with week_number=18", response)
                    self.jornada_18_id = data.get("jornada_id")
                else:
                    self.log_result("Seed Jornada Auto-increment", False, f"Expected week 18, got {week_number}", response)
                    return
            except json.JSONDecodeError:
                self.log_result("Seed Jornada Auto-increment", False, "Invalid JSON response", response)
                return
        else:
            self.log_result("Seed Jornada Auto-increment", False, "Failed to create new jornada", response)
            return
            
        # Verify new jornada exists and is active
        response = self.make_request("GET", "/admin/jornadas")
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                jornadas = data.get("jornadas", [])
                total = data.get("total", 0)
                
                if total == 18:  # Should be 18 now
                    jornada_18 = next((j for j in jornadas if j.get("week_number") == 18), None)
                    jornada_3 = next((j for j in jornadas if j.get("week_number") == 3), None)
                    
                    if (jornada_18 and jornada_18.get("is_active") and
                        jornada_3 and not jornada_3.get("is_active")):
                        self.log_result("Verify Auto-increment Result", True, "Jornada 18 is active, previous jornadas finished", response)
                    else:
                        self.log_result("Verify Auto-increment Result", False, "Jornada activation state incorrect", response)
                else:
                    self.log_result("Verify Auto-increment Result", False, f"Expected 18 jornadas, got {total}", response)
            except json.JSONDecodeError:
                self.log_result("Verify Auto-increment Result", False, "Invalid JSON response", response)
        else:
            self.log_result("Verify Auto-increment Result", False, "Failed to verify auto-increment", response)
    
    # TEST FLOW 4: Authenticated Quiniela Submission
    def test_quiniela_submission(self):
        """Test authenticated quiniela submission"""
        print("\n🎯 TESTING QUINIELA SUBMISSION...")
        
        if not self.access_token:
            self.log_result("Quiniela Submission", False, "No valid access token available", None)
            return
            
        # 1. Get current active jornada with matches
        response = self.make_request("GET", "/jornadas/current")
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                jornada = data.get("jornada", {})
                matches = jornada.get("matches", [])
                
                if matches:
                    self.log_result("Get Current Jornada for Quiniela", True, f"Found {len(matches)} matches in active jornada", response)
                    
                    # Store jornada and match data
                    self.active_jornada_id = jornada.get("id")
                    self.matches_data = matches
                else:
                    self.log_result("Get Current Jornada for Quiniela", False, "No matches found in active jornada", response)
                    return
            except json.JSONDecodeError:
                self.log_result("Get Current Jornada for Quiniela", False, "Invalid JSON response", response)
                return
        else:
            self.log_result("Get Current Jornada for Quiniela", False, "Failed to get current jornada", response)
            return
            
        # 2. Submit quiniela with valid selections
        if hasattr(self, 'active_jornada_id') and hasattr(self, 'matches_data'):
            # Create selections for all matches
            selections = []
            valid_choices = ["HOME", "DRAW", "AWAY"]
            
            for i, match in enumerate(self.matches_data):
                match_id = match.get("id")
                if match_id:
                    # Alternate selections for testing
                    selection = valid_choices[i % 3]
                    selections.append({
                        "match_id": match_id,
                        "selection": selection
                    })
            
            quiniela_data = {
                "jornada_id": self.active_jornada_id,
                "selections": selections
            }
            
            response = self.make_request("POST", "/quiniela/submit", quiniela_data, use_auth=True)
            
            if response and response.status_code == 200:
                try:
                    data = response.json()
                    selections_count = data.get("selections_count", 0)
                    
                    if selections_count == len(selections):
                        self.log_result("Submit Quiniela", True, f"Submitted {selections_count} selections", response)
                    else:
                        self.log_result("Submit Quiniela", False, f"Expected {len(selections)} selections, got {selections_count}", response)
                except json.JSONDecodeError:
                    self.log_result("Submit Quiniela", False, "Invalid JSON response", response)
            else:
                self.log_result("Submit Quiniela", False, "Failed to submit quiniela", response)
                return
                
            # 3. Verify submitted selections
            response = self.make_request("GET", f"/quiniela/my-picks/{self.active_jornada_id}", use_auth=True)
            
            if response and response.status_code == 200:
                try:
                    data = response.json()
                    submitted = data.get("submitted", False)
                    returned_selections = data.get("selections", [])
                    
                    if submitted and len(returned_selections) == len(selections):
                        self.log_result("Verify Quiniela Selections", True, f"Retrieved {len(returned_selections)} submitted selections", response)
                    else:
                        self.log_result("Verify Quiniela Selections", False, f"Selection count mismatch or not submitted", response)
                except json.JSONDecodeError:
                    self.log_result("Verify Quiniela Selections", False, "Invalid JSON response", response)
            else:
                self.log_result("Verify Quiniela Selections", False, "Failed to retrieve selections", response)
        else:
            self.log_result("Submit Quiniela", False, "Missing jornada or matches data", None)
    
    def run_all_tests(self):
        """Run all test flows"""
        print("🚀 STARTING BACKEND API TESTING...")
        print(f"📡 Base URL: {BASE_URL}")
        
        try:
            # Run all test flows
            self.test_auth_flow()
            self.test_jornada_system()
            self.test_seed_jornada_auto_increment()
            self.test_quiniela_submission()
            
            # Print summary
            self.print_summary()
            
        except Exception as e:
            print(f"\n💥 TESTING CRASHED: {str(e)}")
            return False
            
        return len(self.failed_tests) == 0
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("📊 BACKEND TESTING SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = total_tests - len(self.failed_tests)
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {len(self.failed_tests)}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                print(f"  • {test['test']}: {test['details']}")
                
        print("\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            print(f"{result['status']} {result['test']}")
            if result['details']:
                print(f"    {result['details']}")


if __name__ == "__main__":
    tester = BackendTester()
    success = tester.run_all_tests()
    
    if not success:
        sys.exit(1)
    else:
        print("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)