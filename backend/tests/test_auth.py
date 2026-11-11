GOOD = {"username": "admin", "password": "test-password-123"}


def test_routes_need_a_token(anon):
    assert anon.get("/health").status_code == 200
    for path in ["/courses", "/courses/ncert-maths/concepts", "/courses/ncert-maths/graph", "/sessions/x",
                 "/learners/a/progress?course_id=ncert-maths", "/auth/me", "/search?course_id=ncert-maths&q=x"]:
        assert anon.get(path).status_code == 401, path
    assert anon.post("/sessions", json={"course_id": "ncert-maths"}).status_code == 401
    assert anon.post("/practice", json={"course_id": "ncert-maths", "concept_id": "percentages"}).status_code == 401
    assert anon.post("/courses", json={}).status_code == 401


def test_login(anon):
    ok = anon.post("/auth/login", json=GOOD)
    assert ok.status_code == 200 and ok.json()["username"] == "admin"
    token = ok.json()["access_token"]
    assert anon.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json() == {"username": "admin"}
    assert anon.post("/auth/login", json={**GOOD, "password": "wrong"}).status_code == 401
    assert anon.post("/auth/login", json={**GOOD, "username": "someone"}).status_code == 401


def test_bad_and_tampered_tokens_are_rejected(anon):
    assert anon.get("/courses", headers={"Authorization": "Bearer nonsense"}).status_code == 401
    token = anon.post("/auth/login", json=GOOD).json()["access_token"]
    assert anon.get("/courses", headers={"Authorization": f"Bearer {token[:-3]}abc"}).status_code == 401


def test_expired_token_is_rejected(anon, monkeypatch):
    monkeypatch.setenv("TOKEN_MINUTES", "-1")
    token = anon.post("/auth/login", json=GOOD).json()["access_token"]
    assert anon.get("/courses", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_login_is_rate_limited(anon):
    codes = [anon.post("/auth/login", json={"username": "x", "password": "y"}).status_code for _ in range(12)]
    assert codes[:10] == [401] * 10 and codes[10:] == [429, 429]


def test_session_uses_the_signed_in_user_by_default(client):
    assert client.post("/sessions", json={"course_id": "ncert-maths"}).json()["learner_id"] == "admin"


def test_answer_key_is_not_sent_to_learners(client):
    concepts = client.get("/courses/ncert-maths/concepts").json()
    assert concepts and all("questions" not in c for c in concepts)
    assert all("questions" not in n for n in client.get("/courses/ncert-maths/graph").json()["nodes"])


def test_message_rate_limit(client, monkeypatch):
    monkeypatch.setenv("MESSAGES_PER_MINUTE", "3")
    sid = client.post("/sessions", json={"course_id": "ncert-maths"}).json()["session_id"]
    codes = [client.post(f"/sessions/{sid}/messages", json={"text": "hello"}).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]


def test_oversized_message_rejected(client):
    sid = client.post("/sessions", json={"course_id": "ncert-maths"}).json()["session_id"]
    assert client.post(f"/sessions/{sid}/messages", json={"text": "x" * 2001}).status_code == 422
