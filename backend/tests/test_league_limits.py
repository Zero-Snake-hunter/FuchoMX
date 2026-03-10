"""
Backend tests for League Limits (Plan Gratuito) features:
- 1 liga max per user (owner)
- 25 members max per liga
- /api/leagues/{id}/availability endpoint
- /api/leagues/my-leagues returns max_members and is_full
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('EXPO_PUBLIC_BACKEND_URL', '').rstrip('/')

# If EXPO_PUBLIC_BACKEND_URL is not set, fallback to internal
if not BASE_URL:
    BASE_URL = "http://localhost:8001"


def register_user(session, suffix=None):
    """Helper: Register a unique test user and return token"""
    uid = suffix or str(uuid.uuid4())[:8]
    payload = {
        "email": f"TEST_limit_{uid}@test.com",
        "password": "testpass123",
        "display_name": f"Test Limit {uid}"
    }
    resp = session.post(f"{BASE_URL}/api/auth/register", json=payload)
    if resp.status_code == 200:
        return resp.json()["access_token"]
    # Try login if already registered
    login_resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": payload["email"],
        "password": payload["password"]
    })
    return login_resp.json()["access_token"]


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def owner_token(session):
    """Token for user who will create a league (owner)"""
    return register_user(session, "owner1")


@pytest.fixture(scope="module")
def owner2_token(session):
    """Second owner token - should be blocked from creating a second league"""
    return register_user(session, "owner2")


@pytest.fixture(scope="module")
def member_token(session):
    """Token for a member user"""
    return register_user(session, "member1")


# ============ TEST: LEAGUE CREATION LIMIT (1 PER USER) ============

class TestLeagueCreationLimit:
    """Plan Gratuito: Only 1 league per user (owner)"""

    _created_league_id = None
    _created_league_code = None

    def test_create_first_league_succeeds(self, session, owner_token):
        """Creating the first league should succeed"""
        resp = session.post(
            f"{BASE_URL}/api/leagues",
            json={"name": "TEST_First League", "mode": "quiniela"},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "league_id" in data
        assert "code" in data
        assert data["name"] == "TEST_First League"
        assert data["mode"] == "quiniela"
        TestLeagueCreationLimit._created_league_id = data["league_id"]
        TestLeagueCreationLimit._created_league_code = data["code"]
        print(f"✅ First league created: {data['league_id']} code={data['code']}")

    def test_create_second_league_rejected_400(self, session, owner_token):
        """Creating a second league should be rejected with 400"""
        resp = session.post(
            f"{BASE_URL}/api/leagues",
            json={"name": "TEST_Second League", "mode": "quiniela"},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 400, f"Expected 400 (plan limit), got {resp.status_code}: {resp.text}"
        data = resp.json()
        # Should mention plan gratuito in the error message
        detail = data.get("detail", "").lower()
        assert "gratuito" in detail or "plan" in detail or "liga" in detail, \
            f"Error message should mention plan limit, got: {data.get('detail')}"
        print(f"✅ Second league creation correctly rejected: {data.get('detail')}")

    def test_create_second_league_different_mode_also_rejected(self, session, owner_token):
        """Even fantasy mode should be rejected if user already owns a league"""
        resp = session.post(
            f"{BASE_URL}/api/leagues",
            json={"name": "TEST_Fantasy League", "mode": "fantasy"},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
        print(f"✅ Fantasy league also blocked for user with existing league")

    def test_different_user_can_create_league(self, session, owner2_token):
        """Different user should be able to create their own league"""
        resp = session.post(
            f"{BASE_URL}/api/leagues",
            json={"name": "TEST_Owner2 League", "mode": "quiniela"},
            headers={"Authorization": f"Bearer {owner2_token}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "league_id" in data
        print(f"✅ Different user can create their own league: {data['league_id']}")


# ============ TEST: MEMBER LIMIT (25 PER LEAGUE) ============

class TestMemberLimit:
    """Plan Gratuito: Max 25 members per league"""

    _league_code = None
    _league_id = None

    def test_join_league_succeeds_when_not_full(self, session, owner_token, member_token):
        """Should be able to join league when it's not full"""
        # Get the league code from creation test
        leagues_resp = session.get(
            f"{BASE_URL}/api/leagues/my-leagues",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert leagues_resp.status_code == 200
        leagues = leagues_resp.json()["leagues"]
        assert len(leagues) > 0, "Owner should have at least one league"

        # Find the TEST_First League
        test_league = None
        for league in leagues:
            if "TEST_First" in league.get("name", ""):
                test_league = league
                break

        if not test_league:
            test_league = leagues[0]

        TestMemberLimit._league_code = test_league["code"]
        TestMemberLimit._league_id = test_league["id"]

        # Try to join with member_token
        resp = session.post(
            f"{BASE_URL}/api/leagues/join",
            json={"code": test_league["code"]},
            headers={"Authorization": f"Bearer {member_token}"}
        )
        # 200 (joined) or 400 (already a member) are both acceptable
        assert resp.status_code in [200, 400], f"Expected 200 or 400, got {resp.status_code}: {resp.text}"
        if resp.status_code == 200:
            print(f"✅ Member joined league successfully")
        else:
            print(f"✅ Member already in league (expected): {resp.json().get('detail')}")


# ============ TEST: AVAILABILITY ENDPOINT ============

class TestAvailabilityEndpoint:
    """GET /api/leagues/{league_id}/availability"""

    def test_availability_returns_required_fields(self, session, owner_token):
        """Availability endpoint should return member_count, max_members, is_full, spots_left"""
        # Get owner's leagues
        leagues_resp = session.get(
            f"{BASE_URL}/api/leagues/my-leagues",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert leagues_resp.status_code == 200
        leagues = leagues_resp.json()["leagues"]
        assert len(leagues) > 0, "Owner must have leagues for this test"

        league_id = leagues[0]["id"]

        resp = session.get(
            f"{BASE_URL}/api/leagues/{league_id}/availability",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()

        # Verify required fields
        assert "member_count" in data, f"Missing member_count in {data}"
        assert "max_members" in data, f"Missing max_members in {data}"
        assert "is_full" in data, f"Missing is_full in {data}"
        assert "spots_left" in data, f"Missing spots_left in {data}"
        assert "league_id" in data, f"Missing league_id in {data}"

        # Verify data types and values
        assert isinstance(data["member_count"], int), "member_count should be int"
        assert isinstance(data["max_members"], int), "max_members should be int"
        assert isinstance(data["is_full"], bool), "is_full should be bool"
        assert isinstance(data["spots_left"], int), "spots_left should be int"
        assert data["max_members"] == 25, f"max_members should be 25 (free plan), got {data['max_members']}"
        assert data["spots_left"] == data["max_members"] - data["member_count"], \
            "spots_left should equal max_members - member_count"
        assert data["is_full"] == (data["member_count"] >= data["max_members"]), \
            "is_full should be True when member_count >= max_members"

        print(f"✅ Availability endpoint OK: {data['member_count']}/{data['max_members']} (full={data['is_full']}, spots_left={data['spots_left']})")

    def test_availability_invalid_id_returns_400(self, session, owner_token):
        """Invalid league ID should return 400"""
        resp = session.get(
            f"{BASE_URL}/api/leagues/invalid_id_xyz/availability",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code in [400, 422], f"Expected 400/422, got {resp.status_code}"
        print(f"✅ Invalid league ID returns {resp.status_code}")

    def test_availability_not_found_returns_404(self, session, owner_token):
        """Non-existent league ID (valid ObjectId format) should return 404"""
        resp = session.get(
            f"{BASE_URL}/api/leagues/000000000000000000000000/availability",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
        print(f"✅ Non-existent league returns 404")


# ============ TEST: MY-LEAGUES WITH NEW FIELDS ============

class TestMyLeaguesNewFields:
    """GET /api/leagues/my-leagues should return max_members and is_full"""

    def test_my_leagues_includes_max_members(self, session, owner_token):
        """my-leagues should include max_members field"""
        resp = session.get(
            f"{BASE_URL}/api/leagues/my-leagues",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "leagues" in data

        leagues = data["leagues"]
        assert len(leagues) > 0, "Should have at least 1 league"

        for league in leagues:
            assert "max_members" in league, f"Missing max_members in league {league.get('id')}"
            assert "is_full" in league, f"Missing is_full in league {league.get('id')}"
            assert "member_count" in league, f"Missing member_count in league {league.get('id')}"
            assert league["max_members"] == 25, f"max_members should be 25, got {league['max_members']}"
            assert isinstance(league["is_full"], bool), "is_full should be boolean"

        print(f"✅ my-leagues returns max_members/is_full for all {len(leagues)} league(s)")

    def test_my_leagues_is_full_consistency(self, session, owner_token):
        """is_full should be consistent with member_count and max_members"""
        resp = session.get(
            f"{BASE_URL}/api/leagues/my-leagues",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
        leagues = resp.json()["leagues"]

        for league in leagues:
            expected_full = league["member_count"] >= league["max_members"]
            assert league["is_full"] == expected_full, \
                f"is_full inconsistency: member_count={league['member_count']}, max_members={league['max_members']}, is_full={league['is_full']}"

        print(f"✅ is_full is consistent with member_count/max_members")

    def test_my_leagues_mode_field(self, session, owner_token):
        """Leagues should include mode field (quiniela or fantasy)"""
        resp = session.get(
            f"{BASE_URL}/api/leagues/my-leagues",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert resp.status_code == 200
        leagues = resp.json()["leagues"]

        for league in leagues:
            assert "mode" in league, f"Missing mode in league {league.get('id')}"
            assert league["mode"] in ["quiniela", "fantasy"], \
                f"Invalid mode: {league.get('mode')}"

        print(f"✅ All leagues have valid mode field")


# ============ TEST: AVAILABILITY ENDPOINT NOT CAPTURED BY WILDCARD ============

class TestAvailabilityRouteOrder:
    """Verify /leagues/{league_id}/availability is not captured by /{league_id} wildcard"""

    def test_availability_route_registered_correctly(self, session, owner_token):
        """
        Availability endpoint must NOT conflict with /{league_id} wildcard.
        FastAPI routes are matched by order: /availability must be registered before /{league_id}.
        """
        # Get a valid league
        leagues_resp = session.get(
            f"{BASE_URL}/api/leagues/my-leagues",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert leagues_resp.status_code == 200
        leagues = leagues_resp.json()["leagues"]
        assert len(leagues) > 0

        league_id = leagues[0]["id"]

        # Call availability endpoint
        resp = session.get(
            f"{BASE_URL}/api/leagues/{league_id}/availability",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        # Must return 200 with availability data, NOT 403 (would indicate /{league_id} captured it)
        assert resp.status_code == 200, \
            f"availability route captured by wildcard! Got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "spots_left" in data, \
            f"Route returned wrong data (possibly captured by /{league_id}): {data}"
        print(f"✅ /availability route correctly registered and not captured by /{'{league_id}'} wildcard")


# ============ TEST: UNAUTHENTICATED REQUESTS ============

class TestAuthRequirements:
    """All new league endpoints require authentication"""

    def test_availability_requires_auth(self, session):
        """Availability endpoint should require auth"""
        resp = session.get(f"{BASE_URL}/api/leagues/000000000000000000000000/availability")
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"
        print(f"✅ availability endpoint requires auth: {resp.status_code}")

    def test_my_leagues_requires_auth(self, session):
        """my-leagues endpoint should require auth"""
        resp = session.get(f"{BASE_URL}/api/leagues/my-leagues")
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"
        print(f"✅ my-leagues endpoint requires auth: {resp.status_code}")

    def test_create_league_requires_auth(self, session):
        """Create league should require auth"""
        resp = session.post(
            f"{BASE_URL}/api/leagues",
            json={"name": "Unauthorized League", "mode": "quiniela"}
        )
        assert resp.status_code in [401, 403], f"Expected 401/403, got {resp.status_code}"
        print(f"✅ create league requires auth: {resp.status_code}")
