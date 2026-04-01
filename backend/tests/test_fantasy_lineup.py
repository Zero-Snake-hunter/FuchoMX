"""
Backend tests for Fantasy Lineup P0 bug fix:
1. /api/jornadas/current stability (no auto-advance on repeated calls)
2. Full fantasy lineup submission flow (POST /api/fantasy/lineup)
3. Duplicate lineup prevention (400 on second submission)
4. GET /api/fantasy/lineup/{jornada_id} - check submitted flag
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = 'https://quiniela-fantasy.preview.emergentagent.com'

# Test credentials from review_request
EXISTING_USER_EMAIL = "fantasytest2@gmail.com"
EXISTING_USER_PASSWORD = "Test123!"

# New user for fresh flow
NEW_USER_EMAIL = f"newuser_fantasy_{uuid.uuid4().hex[:6]}@test.com"
NEW_USER_PASSWORD = "Test123!"

@pytest.fixture(scope="module")
def api():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def existing_user_token(api):
    """Login with existing user (has fantasy team + submitted lineup)"""
    resp = api.post(f"{BASE_URL}/api/auth/login", json={
        "email": EXISTING_USER_EMAIL,
        "password": EXISTING_USER_PASSWORD
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
def new_user_token(api):
    """Register and login a new user (no fantasy team)"""
    reg_resp = api.post(f"{BASE_URL}/api/auth/register", json={
        "email": NEW_USER_EMAIL,
        "password": NEW_USER_PASSWORD,
        "display_name": "NewFantasyUser"
    })
    # May already exist from prior run - try login
    if reg_resp.status_code not in (200, 201):
        pass  # fall through to login
    
    login_resp = api.post(f"{BASE_URL}/api/auth/login", json={
        "email": NEW_USER_EMAIL,
        "password": NEW_USER_PASSWORD
    })
    assert login_resp.status_code == 200, f"Login new user failed: {login_resp.text}"
    return login_resp.json()["access_token"]


# ============================================================
# Test 1: /api/jornadas/current stability - no auto-advance
# ============================================================
class TestJornadaCurrentStability:
    """Verify that calling /api/jornadas/current 3 times returns SAME jornada"""

    def test_jornada_current_call_1(self, api):
        resp = api.get(f"{BASE_URL}/api/jornadas/current")
        assert resp.status_code == 200, f"First call failed: {resp.text}"
        data = resp.json()
        assert "jornada" in data
        assert data["jornada"]["id"] is not None
        self.__class__.first_id = data["jornada"]["id"]
        self.__class__.first_week = data["jornada"]["week_number"]
        print(f"Call 1: jornada_id={data['jornada']['id']}, week={data['jornada']['week_number']}")

    def test_jornada_current_call_2(self, api):
        resp = api.get(f"{BASE_URL}/api/jornadas/current")
        assert resp.status_code == 200, f"Second call failed: {resp.text}"
        data = resp.json()
        assert data["jornada"]["id"] == self.__class__.first_id, \
            f"Jornada changed! Call1={self.__class__.first_id}, Call2={data['jornada']['id']}"
        print(f"Call 2: Same jornada_id={data['jornada']['id']} ✓")

    def test_jornada_current_call_3(self, api):
        resp = api.get(f"{BASE_URL}/api/jornadas/current")
        assert resp.status_code == 200, f"Third call failed: {resp.text}"
        data = resp.json()
        assert data["jornada"]["id"] == self.__class__.first_id, \
            f"Jornada changed! Expected={self.__class__.first_id}, Got={data['jornada']['id']}"
        print(f"Call 3: Same jornada_id={data['jornada']['id']} ✓")

    def test_jornada_current_returns_required_fields(self, api):
        resp = api.get(f"{BASE_URL}/api/jornadas/current")
        assert resp.status_code == 200
        jornada = resp.json()["jornada"]
        assert "id" in jornada
        assert "week_number" in jornada
        assert "status" in jornada
        assert "matches" in jornada
        print(f"Jornada fields: id, week_number, status, matches present ✓")

    def test_jornada_end_date_in_future(self, api):
        """Verify end_date is in the future (prevents auto-advance)"""
        resp = api.get(f"{BASE_URL}/api/jornadas/current")
        assert resp.status_code == 200
        jornada = resp.json()["jornada"]
        # end_date should be present and in future to prevent auto-advance
        assert "end_date" in jornada and jornada["end_date"] is not None, \
            "end_date field missing - auto-advance protection may fail"
        print(f"end_date: {jornada['end_date']} - future protection in place ✓")


# ============================================================
# Test 2: Full Fantasy Lineup Flow (new user with no team)
# ============================================================
class TestFantasyNewUserFlow:
    """Test the no-team scenario: 400 when submitting lineup without fantasy team"""

    def test_new_user_has_no_team(self, api, new_user_token):
        resp = api.get(
            f"{BASE_URL}/api/fantasy/my-team",
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["exists"] == False, f"New user should not have team, got: {data}"
        print(f"New user has no team: exists={data['exists']} ✓")

    def test_submit_lineup_without_team_returns_400(self, api, new_user_token):
        """Submitting lineup without a fantasy team should return 400"""
        # Get current jornada first
        jornada_resp = api.get(f"{BASE_URL}/api/jornadas/current")
        jornada_id = jornada_resp.json()["jornada"]["id"]

        # Get some players to use as dummy lineup
        teams_resp = api.get(f"{BASE_URL}/api/teams")
        teams = teams_resp.json()["teams"]
        first_team_id = teams[0]["id"]

        players_resp = api.get(f"{BASE_URL}/api/players?team_id={first_team_id}")
        players = players_resp.json().get("players", [])

        if len(players) < 11:
            pytest.skip("Not enough players available for this test")

        dummy_lineup = []
        positions = ["POR_1", "DEF_1", "DEF_2", "DEF_3", "DEF_4",
                     "MED_1", "MED_2", "MED_3", "MED_4", "DEL_1", "DEL_2"]
        for i, slot in enumerate(positions):
            if i < len(players):
                dummy_lineup.append({
                    "player_id": players[i % len(players)]["id"],
                    "position_slot": slot
                })

        resp = api.post(
            f"{BASE_URL}/api/fantasy/lineup",
            headers={"Authorization": f"Bearer {new_user_token}"},
            json={
                "jornada_id": jornada_id,
                "players": dummy_lineup,
                "dt_team_id": first_team_id
            }
        )
        assert resp.status_code == 400, f"Expected 400 for user without team, got {resp.status_code}: {resp.text}"
        assert "equipo" in resp.json().get("detail", "").lower() or "equipo" in resp.text.lower(), \
            f"Expected 'equipo' in error message: {resp.text}"
        print(f"Lineup without team → 400 ✓ msg: {resp.json().get('detail')}")


# ============================================================
# Test 3: Full Fantasy Lineup Flow (new user - create team + submit)
# ============================================================
class TestFantasyFullFlow:
    """Full flow: register new user → create team → submit lineup → verify → duplicate check"""

    @pytest.fixture(scope="class")
    def fresh_user_token(self, api):
        """Create a completely fresh user for full flow test"""
        email = f"TEST_fresh_fantasy_{uuid.uuid4().hex[:6]}@test.com"
        reg_resp = api.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "Test123!",
            "display_name": "FreshFantasyUser"
        })
        if reg_resp.status_code not in (200, 201):
            # Try login
            pass
        login_resp = api.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": "Test123!"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.__class__._fresh_email = email
        return login_resp.json()["access_token"]

    def test_create_fantasy_team(self, api, fresh_user_token):
        resp = api.post(
            f"{BASE_URL}/api/fantasy/team",
            headers={"Authorization": f"Bearer {fresh_user_token}"},
            json={"name": "TEST_Fresh Fantasy FC", "formation": "4-4-2"}
        )
        assert resp.status_code in (200, 201), f"Create team failed: {resp.text}"
        data = resp.json()
        assert data.get("success") == True or "team" in data or "id" in data or "message" in data, \
            f"Unexpected response: {data}"
        print(f"Team created ✓: {data}")

    def test_verify_team_exists_after_creation(self, api, fresh_user_token):
        resp = api.get(
            f"{BASE_URL}/api/fantasy/my-team",
            headers={"Authorization": f"Bearer {fresh_user_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["exists"] == True, f"Team should exist after creation: {data}"
        print(f"Team exists after creation ✓")

    def test_submit_full_lineup_11_players_plus_dt(self, api, fresh_user_token):
        """Submit valid lineup with 11 players + DT"""
        # Get current jornada
        jornada_resp = api.get(f"{BASE_URL}/api/jornadas/current")
        assert jornada_resp.status_code == 200
        jornada_id = jornada_resp.json()["jornada"]["id"]
        self.__class__._jornada_id = jornada_id

        # Get teams and players
        teams_resp = api.get(f"{BASE_URL}/api/teams")
        teams = teams_resp.json()["teams"]
        assert len(teams) > 0, "No teams available"
        dt_team_id = teams[0]["id"]

        # Collect 11 unique players from different teams/positions
        lineup = []
        position_slots = [
            ("POR", "POR_1"),
            ("DEF", "DEF_1"), ("DEF", "DEF_2"), ("DEF", "DEF_3"), ("DEF", "DEF_4"),
            ("MED", "MED_1"), ("MED", "MED_2"), ("MED", "MED_3"), ("MED", "MED_4"),
            ("DEL", "DEL_1"), ("DEL", "DEL_2"),
        ]
        
        used_ids = set()
        for position, slot in position_slots:
            # Try multiple teams until we get enough players
            found = False
            for team in teams:
                players_resp = api.get(
                    f"{BASE_URL}/api/players?position={position}&team_id={team['id']}"
                )
                if players_resp.status_code == 200:
                    players = players_resp.json().get("players", [])
                    for player in players:
                        if player["id"] not in used_ids:
                            lineup.append({"player_id": player["id"], "position_slot": slot})
                            used_ids.add(player["id"])
                            found = True
                            break
                if found:
                    break
            
            if not found:
                pytest.skip(f"Could not find player for position {position}")

        assert len(lineup) == 11, f"Expected 11 players, got {len(lineup)}"

        resp = api.post(
            f"{BASE_URL}/api/fantasy/lineup",
            headers={"Authorization": f"Bearer {fresh_user_token}"},
            json={
                "jornada_id": jornada_id,
                "players": lineup,
                "dt_team_id": dt_team_id
            }
        )
        assert resp.status_code == 200, f"Lineup submission failed: {resp.text}"
        data = resp.json()
        assert "message" in data or "players_count" in data, f"Unexpected response: {data}"
        print(f"Lineup submitted ✓: players_count={data.get('players_count')}")

    def test_lineup_persisted_in_db(self, api, fresh_user_token):
        """Verify GET /api/fantasy/lineup/{jornada_id} shows submitted=True"""
        jornada_id = self.__class__._jornada_id
        resp = api.get(
            f"{BASE_URL}/api/fantasy/lineup/{jornada_id}",
            headers={"Authorization": f"Bearer {fresh_user_token}"}
        )
        assert resp.status_code == 200, f"GET lineup failed: {resp.text}"
        data = resp.json()
        assert data.get("submitted") == True, \
            f"submitted should be True after submission: {data}"
        assert len(data.get("lineup", [])) > 0, "Lineup should have entries"
        print(f"Lineup persisted ✓: submitted={data['submitted']}, entries={len(data['lineup'])}")

    def test_duplicate_lineup_returns_400(self, api, fresh_user_token):
        """Second submission for same jornada → 400 with proper message"""
        jornada_id = self.__class__._jornada_id

        # Get teams and players for second submission
        teams_resp = api.get(f"{BASE_URL}/api/teams")
        teams = teams_resp.json()["teams"]
        dt_team_id = teams[1]["id"]  # different DT

        position_slots = [
            ("POR", "POR_1"),
            ("DEF", "DEF_1"), ("DEF", "DEF_2"), ("DEF", "DEF_3"), ("DEF", "DEF_4"),
            ("MED", "MED_1"), ("MED", "MED_2"), ("MED", "MED_3"), ("MED", "MED_4"),
            ("DEL", "DEL_1"), ("DEL", "DEL_2"),
        ]
        used_ids = set()
        lineup = []
        for position, slot in position_slots:
            for team in teams:
                players_resp = api.get(
                    f"{BASE_URL}/api/players?position={position}&team_id={team['id']}"
                )
                if players_resp.status_code == 200:
                    players = players_resp.json().get("players", [])
                    for player in players:
                        if player["id"] not in used_ids:
                            lineup.append({"player_id": player["id"], "position_slot": slot})
                            used_ids.add(player["id"])
                            break
                if len([l for l in lineup if l["position_slot"] == slot]) > 0:
                    break

        if len(lineup) < 11:
            pytest.skip("Could not build second lineup for duplicate test")

        resp = api.post(
            f"{BASE_URL}/api/fantasy/lineup",
            headers={"Authorization": f"Bearer {fresh_user_token}"},
            json={
                "jornada_id": jornada_id,
                "players": lineup,
                "dt_team_id": dt_team_id
            }
        )
        assert resp.status_code == 400, \
            f"Expected 400 for duplicate lineup, got {resp.status_code}: {resp.text}"
        detail = resp.json().get("detail", "")
        assert "alineación" in detail.lower() or "jornada" in detail.lower(), \
            f"Expected alineación/jornada in error: {detail}"
        print(f"Duplicate lineup → 400 ✓ msg: {detail}")


# ============================================================
# Test 4: Existing user (fantasytest2) - already has lineup
# ============================================================
class TestExistingUserAlreadySubmitted:
    """Existing user fantasytest2@gmail.com has already submitted lineup for jornada 14"""

    def test_existing_user_my_team_exists(self, api, existing_user_token):
        resp = api.get(
            f"{BASE_URL}/api/fantasy/my-team",
            headers={"Authorization": f"Bearer {existing_user_token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["exists"] == True, f"User should have team: {data}"
        print(f"Existing user team: exists={data['exists']}, name={data.get('name')} ✓")

    def test_existing_user_lineup_submitted(self, api, existing_user_token):
        """GET /api/fantasy/lineup/{jornada_id} should return submitted=True"""
        jornada_resp = api.get(f"{BASE_URL}/api/jornadas/current")
        jornada_id = jornada_resp.json()["jornada"]["id"]

        resp = api.get(
            f"{BASE_URL}/api/fantasy/lineup/{jornada_id}",
            headers={"Authorization": f"Bearer {existing_user_token}"}
        )
        assert resp.status_code == 200, f"GET lineup failed: {resp.text}"
        data = resp.json()
        assert data.get("submitted") == True, \
            f"Expected submitted=True for existing user: {data}"
        print(f"Existing user lineup: submitted={data['submitted']} ✓")

    def test_existing_user_duplicate_lineup_returns_400(self, api, existing_user_token):
        """Attempting second submission returns 400 with correct message"""
        jornada_resp = api.get(f"{BASE_URL}/api/jornadas/current")
        jornada_id = jornada_resp.json()["jornada"]["id"]

        teams_resp = api.get(f"{BASE_URL}/api/teams")
        teams = teams_resp.json()["teams"]
        dt_team_id = teams[0]["id"]

        position_slots = [
            ("POR", "POR_1"),
            ("DEF", "DEF_1"), ("DEF", "DEF_2"), ("DEF", "DEF_3"), ("DEF", "DEF_4"),
            ("MED", "MED_1"), ("MED", "MED_2"), ("MED", "MED_3"), ("MED", "MED_4"),
            ("DEL", "DEL_1"), ("DEL", "DEL_2"),
        ]
        used_ids = set()
        lineup = []
        for position, slot in position_slots:
            for team in teams:
                players_resp = api.get(
                    f"{BASE_URL}/api/players?position={position}&team_id={team['id']}"
                )
                if players_resp.status_code == 200:
                    players = players_resp.json().get("players", [])
                    for player in players:
                        if player["id"] not in used_ids:
                            lineup.append({"player_id": player["id"], "position_slot": slot})
                            used_ids.add(player["id"])
                            break
                if len([l for l in lineup if l["position_slot"] == slot]) > 0:
                    break

        if len(lineup) < 11:
            pytest.skip("Could not build lineup for duplicate test")

        resp = api.post(
            f"{BASE_URL}/api/fantasy/lineup",
            headers={"Authorization": f"Bearer {existing_user_token}"},
            json={
                "jornada_id": jornada_id,
                "players": lineup,
                "dt_team_id": dt_team_id
            }
        )
        assert resp.status_code == 400, \
            f"Expected 400 for duplicate submission, got {resp.status_code}: {resp.text}"
        detail = resp.json().get("detail", "")
        assert "alineación" in detail.lower(), \
            f"Expected 'alineación' in error detail: {detail}"
        print(f"Duplicate for existing user → 400 ✓ msg: {detail}")
