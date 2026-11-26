from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
from types import SimpleNamespace

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models import ChatMessage, Package, PendingAction, ToolRun, User
from rag import chunk_text, retrieve


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        hashed = bcrypt.hashpw(b"test-password", bcrypt.gensalt(rounds=4)).decode()
        db.add_all([User(username="alice", password_hash=hashed, role="user"),
                    User(username="bob", password_hash=hashed, role="user"),
                    User(username="admin", password_hash=hashed, role="admin"),
                    Package(title="Test Escape", destination="Goa", duration_days=3, price=Decimal("100.00"),
                            capacity=2, start_date=date.today() + timedelta(days=8), active=True)])
        db.commit()
    def override():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = override
    with TestClient(app) as test_client:
        yield test_client, factory
    app.dependency_overrides.clear()
    engine.dispose()


def auth(name):
    return (name, "test-password")


def test_booking_idempotency_ownership_and_capacity(client):
    c, _ = client
    payload = {"lines": [{"item_id": 1, "quantity": 2}]}
    headers = {"Idempotency-Key": "one"}
    first = c.post("/api/bookings", json=payload, headers=headers, auth=auth("alice"))
    assert first.status_code == 201
    assert first.json()["total"] == "200.00"
    assert c.post("/api/bookings", json=payload, headers=headers, auth=auth("alice")).json()["id"] == first.json()["id"]
    assert c.post("/api/bookings", json={"lines": [{"item_id": 1, "quantity": 1}]}, headers=headers, auth=auth("alice")).status_code == 409
    assert c.post("/api/bookings", json=payload, headers={"Idempotency-Key": "two"}, auth=auth("bob")).status_code == 409
    assert c.get(f"/api/bookings/{first.json()['id']}", auth=auth("bob")).status_code == 404
    assert c.get("/api/packages/1").json()["capacity"] == 0


def test_cancel_restores_only_once_and_rechecks_refund(client):
    c, _ = client
    booking = c.post("/api/bookings", json={"lines": [{"item_id": 1, "quantity": 1}]},
                     headers={"Idempotency-Key": "cancel"}, auth=auth("alice")).json()
    url = f"/api/bookings/{booking['id']}/cancel"
    assert c.post(url + "?expected_refund=50", auth=auth("alice")).status_code == 409
    assert c.get("/api/packages/1").json()["capacity"] == 1
    assert c.post(url + "?expected_refund=100", auth=auth("alice")).json()["refund"] == "100.00"
    assert c.post(url, auth=auth("alice")).status_code == 200
    assert c.get("/api/packages/1").json()["capacity"] == 2


def test_validation_admin_and_changed_terms(client):
    c, _ = client
    data = {"title": "New Trip", "destination": "Goa", "duration_days": 3, "price": "0",
            "capacity": 2, "start_date": (date.today() + timedelta(days=2)).isoformat()}
    assert c.post("/api/packages", json=data, auth=auth("alice")).status_code == 403
    assert c.post("/api/packages", json=data, auth=auth("admin")).status_code == 422
    result = c.post("/api/bookings", auth=auth("alice"), headers={"Idempotency-Key": "terms"},
                    json={"lines": [{"item_id": 1, "quantity": 1, "expected_price": "99.00"}]})
    assert result.status_code == 409
    assert c.get("/api/packages/1").json()["capacity"] == 2


def test_chat_missing_key_persists_failure_and_is_private(client):
    c, factory = client
    session_id = c.post("/api/chat/sessions", auth=auth("alice")).json()["id"]
    with patch("rag.settings") as config:
        config.return_value.openai_api_key = ""
        response = c.post(f"/api/chat/sessions/{session_id}/messages", json={"message": "Hello"}, auth=auth("alice"))
    assert response.status_code == 503
    assert c.get(f"/api/chat/sessions/{session_id}/messages", auth=auth("bob")).status_code == 404
    history = c.get(f"/api/chat/sessions/{session_id}/messages", auth=auth("alice")).json()
    assert [entry["role"] for entry in history] == ["user", "assistant"]
    assert history[1]["metadata"]["mode"] == "ERROR"
    with factory() as db:
        assert len(db.scalars(select(ChatMessage)).all()) == 2


def test_pending_action_reject_and_confirmation_replay(client):
    c, factory = client
    session_id = c.post("/api/chat/sessions", auth=auth("alice")).json()["id"]
    with factory() as db:
        user = db.scalar(select(User).where(User.username == "alice"))
        for key in ("reject", "confirm"):
            db.add(PendingAction(session_id=session_id, user_id=user.id, action="create_booking",
                                 payload={"lines": [{"item_id": 1, "quantity": 1, "expected_price": "100.00",
                                                     "expected_start_date": (date.today() + timedelta(days=8)).isoformat()}]},
                                 expires_at=datetime.utcnow() + timedelta(minutes=10), status="PENDING", idempotency_key=key))
        db.commit()
    assert c.post("/api/chat/actions/1/confirm", json={"confirm": False}, auth=auth("alice")).json()["status"] == "REJECTED"
    assert c.post("/api/chat/actions/2/confirm", json={"confirm": True}, auth=auth("bob")).status_code == 404
    def local_call(method, path, credentials, **kwargs):
        response = c.request(method, path, auth=(credentials.username, credentials.password), **kwargs)
        assert response.status_code == 201
        return response.json()
    with patch("chat.api_call", side_effect=local_call):
        first = c.post("/api/chat/actions/2/confirm", json={"confirm": True}, auth=auth("alice"))
        second = c.post("/api/chat/actions/2/confirm", json={"confirm": True}, auth=auth("alice"))
    assert first.json()["result"]["id"] == second.json()["result"]["id"]
    assert c.get("/api/packages/1").json()["capacity"] == 1


def test_agent_creates_pending_action_without_booking(client):
    c, factory = client
    session_id = c.post("/api/chat/sessions", auth=auth("alice")).json()["id"]
    call = SimpleNamespace(id="call-1", function=SimpleNamespace(name="create_booking", arguments='{"lines":[{"item_id":1,"quantity":1}]}'))
    first = SimpleNamespace(tool_calls=[call], content=None, model_dump=lambda **kwargs: {
        "role": "assistant", "tool_calls": [{"id": "call-1", "type": "function",
        "function": {"name": "create_booking", "arguments": call.function.arguments}}]})
    last = SimpleNamespace(tool_calls=None, content="Please confirm this booking.")
    completions = SimpleNamespace(create=Mock(
        side_effect=[SimpleNamespace(choices=[SimpleNamespace(message=first)]),
                     SimpleNamespace(choices=[SimpleNamespace(message=last)])]))
    ai = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    with patch("chat.ai_client", return_value=ai), patch("chat.api_call", return_value={
            "id": 1, "title": "Test Escape", "price": "100.00", "capacity": 2,
            "start_date": (date.today() + timedelta(days=8)).isoformat()}):
        response = c.post(f"/api/chat/sessions/{session_id}/messages",
                          json={"message": "Book one seat"}, auth=auth("alice"))
    assert response.status_code == 200
    assert response.json()["metadata"]["actions"][0]["status"] == "PENDING"
    assert c.get("/api/bookings", auth=auth("alice")).json() == []
    assert c.get("/api/packages/1").json()["capacity"] == 2
    with factory() as db:
        assert db.scalar(select(ToolRun)).status == "SUCCESS"


def test_retrieval_only_returns_active_relevant_sources(client):
    from models import Document
    c, factory = client
    with factory() as db:
        admin = db.scalar(select(User).where(User.username == "admin"))
        db.add(Document(filename="policy.txt", sha256="a" * 64, version=2, status="ACTIVE", uploaded_by=admin.id))
        db.commit()
        collection = SimpleNamespace(query=lambda **kwargs: {
            "documents": [["Relevant text", "Irrelevant text"]],
            "metadatas": [[{"filename": "policy.txt", "page": 1, "version": 2},
                           {"filename": "policy.txt", "page": 1, "version": 2}]],
            "ids": [["1-0", "1-1"]], "distances": [[0.1, 0.9]]})
        embeddings = SimpleNamespace(create=lambda **kwargs: SimpleNamespace(data=[SimpleNamespace(embedding=[0.1])]))
        with patch("rag.ai_client", return_value=SimpleNamespace(embeddings=embeddings)), patch("rag.collection", return_value=collection):
            sources = retrieve("What is the policy?", db)
        assert len(sources) == 1
        assert sources[0]["chunk_id"] == "1-0"
    chunks = chunk_text("x" * 1500)
    assert len(chunks) == 3 and chunks[0][-100:] == chunks[1][:100]
