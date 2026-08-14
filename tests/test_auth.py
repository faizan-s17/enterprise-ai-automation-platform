"""Registration, login, tokens, and the no-enumeration guarantee."""


def test_register_creates_a_viewer_regardless_of_requested_role(client):
    """Self-registration always produces a viewer.

    Posting role: admin here would be a privilege-escalation bug if it were
    honoured, so this is a security assertion, not just a shape check.
    """
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@acmecorp-test.com",
            "password": "Passw0rd!",
            "role": "admin",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["role"] == "viewer"


def test_register_rejects_a_duplicate_email(client):
    # EmailStr (via email-validator) rejects RFC 2606 reserved domains
    # (.local, .test, example.com, ...), so a syntactically ordinary-looking
    # but fake domain is used here rather than the more obviously-fake
    # .local addresses used elsewhere in this suite for rows inserted
    # directly via SQLAlchemy, which bypass that validation entirely.
    payload = {"email": "dup@acmecorp-test.com", "password": "Passw0rd!"}
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


def test_login_succeeds_with_correct_credentials(client, users):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.local", "password": "Admin@12345"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_rejects_wrong_password(client, users):
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.local", "password": "wrong-password"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Incorrect email or password"


def test_login_unknown_email_gives_the_identical_message(client, users):
    """A different message here would let an attacker enumerate accounts by
    timing or wording differences between 'no such user' and 'wrong password'.
    """
    known_wrong = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.local", "password": "wrong-password"},
    )
    unknown = client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@test.local", "password": "wrong-password"},
    )
    assert known_wrong.status_code == unknown.status_code == 401
    assert known_wrong.json()["detail"] == unknown.json()["detail"]


def test_login_rejects_a_disabled_account(client, db, users):
    users["viewer"].is_active = False
    db.commit()

    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "viewer@test.local", "password": "Viewer@12345"},
    )
    assert resp.status_code == 403


def test_me_returns_the_authenticated_users_profile(client, tokens):
    resp = client.get("/api/v1/auth/me", headers=tokens["manager"])
    assert resp.status_code == 200
    assert resp.json()["email"] == "manager@test.local"
    assert resp.json()["role"] == "manager"


def test_protected_route_without_a_token_is_rejected(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_refresh_token_cannot_be_used_as_an_access_token(client, users):
    """decode_token enforces the `type` claim; a stolen refresh token should
    not work directly against a protected route."""
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.local", "password": "Admin@12345"},
    )
    refresh_token = login.json()["refresh_token"]

    resp = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh_token}"}
    )
    assert resp.status_code == 401


def test_refresh_issues_a_new_access_token(client, users):
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.local", "password": "Admin@12345"},
    )
    refresh_token = login.json()["refresh_token"]

    resp = client.post(
        "/api/v1/auth/refresh", params={"refresh_token": refresh_token}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]
