import os
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4

import pytest

test_url = os.environ.get("TEST_DATABASE_URL")
if not test_url or not test_url.rsplit("/", 1)[-1].startswith("food_ai_test"):
    pytest.skip("Set TEST_DATABASE_URL to a dedicated food_ai_test database", allow_module_level=True)
os.environ["DATABASE_URL"] = test_url
os.environ["OPENAI_API_KEY"] = ""

from fastapi import HTTPException
from fastapi.testclient import TestClient

import chat
import rag
from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def new_item(client, capacity=2):
    response = client.post("/api/menu_items", auth=("admin", "admin123"), json={
        "title": f"Test dish {uuid4().hex[:8]}", "category": "Test", "vegetarian": True,
        "price": "75.00", "capacity": capacity, "active": True,
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_authorization_and_validation(client):
    assert client.get("/api/menu_items").status_code == 200
    assert client.post("/api/menu_items", auth=("alice", "alice123"), json={}).status_code == 403
    assert client.get("/api/me", auth=("alice", "wrong")).status_code == 401
    assert client.post("/api/menu_items", auth=("admin", "admin123"), json={
        "title": "Bad", "category": "Test", "vegetarian": True, "price": "-1", "capacity": 1
    }).status_code == 422
    assert client.post("/api/orders", auth=("alice", "alice123"), headers={"Idempotency-Key": str(uuid4())},
                       json={"lines": [{"item_id": 1, "quantity": 11}]}).status_code == 422


def test_order_idempotency_ownership_and_cancellation(client):
    item = new_item(client)
    auth = ("alice", "alice123")
    key = str(uuid4())
    body = {"lines": [{"item_id": item["id"], "quantity": 1}]}
    first = client.post("/api/orders", auth=auth, headers={"Idempotency-Key": key}, json=body)
    assert first.status_code == 201
    assert client.post("/api/orders", auth=auth, headers={"Idempotency-Key": key}, json=body).json()["id"] == first.json()["id"]
    conflict = client.post("/api/orders", auth=auth, headers={"Idempotency-Key": key},
                           json={"lines": [{"item_id": item["id"], "quantity": 2}]})
    assert conflict.status_code == 409
    order_id = first.json()["id"]
    assert client.get(f"/api/orders/{order_id}", auth=("bob", "bob123")).status_code == 404
    cancel_key = str(uuid4())
    cancel = lambda: client.post(f"/api/orders/{order_id}/cancel", auth=auth, headers={"Idempotency-Key": cancel_key})
    assert cancel().json()["status"] == "CANCELLED"
    assert cancel().json()["status"] == "CANCELLED"
    assert client.get(f"/api/menu_items/{item['id']}").json()["capacity"] == 2
    assert client.post(f"/api/orders/{order_id}/cancel", auth=auth).status_code == 409


def test_concurrent_last_portion(client):
    item = new_item(client, capacity=1)
    def order(user):
        return client.post("/api/orders", auth=(user, f"{user}123"), headers={"Idempotency-Key": str(uuid4())},
                           json={"lines": [{"item_id": item["id"], "quantity": 1}]})
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(order, ["alice", "bob"]))
    assert sorted(response.status_code for response in responses) == [201, 409]
    assert client.get(f"/api/menu_items/{item['id']}").json()["capacity"] == 0


def test_chat_persistence_and_missing_key(client):
    auth = ("alice", "alice123")
    session = client.post("/api/chat/sessions", auth=auth, json={"title": "Persistence test"}).json()["id"]
    response = client.post(f"/api/chat/sessions/{session}/messages", auth=auth, json={"message": "Hello"})
    assert response.status_code == 503
    history = client.get(f"/api/chat/sessions/{session}/messages", auth=auth).json()["messages"]
    assert [(m["seq_no"], m["role"]) for m in history] == [(1, "user"), (2, "assistant")]
    assert history[1]["metadata"]["mode"] == "ERROR"
    assert client.get(f"/api/chat/sessions/{session}/messages", auth=("bob", "bob123")).status_code == 404


def test_agent_confirmation_idempotency_and_changed_price(client, monkeypatch):
    item = new_item(client, capacity=3)
    original_request = chat.internal_request
    def internal(method, path, credentials, *, params=None, payload=None, key=None):
        headers = {"Idempotency-Key": key} if key else {}
        response = client.request(method, path, auth=(credentials.username, credentials.password),
                                  params=params, json=payload, headers=headers)
        if response.is_error:
            raise HTTPException(response.status_code, response.json()["message"])
        return response.json()
    monkeypatch.setattr(chat, "internal_request", internal)

    class Reply:
        def __init__(self, tool):
            self.tool_calls = [SimpleNamespace(id="call1", function=SimpleNamespace(
                name="create_order", arguments='{"lines":[{"item_id":%d,"quantity":1}]}' % item["id"]))] if tool else None
            self.content = None if tool else "Please confirm your order."
        def model_dump(self, **kwargs):
            return {"role": "assistant", "tool_calls": [{"id": "call1", "type": "function",
                    "function": {"name": "create_order", "arguments": self.tool_calls[0].function.arguments}}]}
    class FakeAI:
        def __init__(self):
            self.chat = SimpleNamespace(completions=self)
            self.count = 0
        def create(self, **kwargs):
            self.count += 1
            return SimpleNamespace(choices=[SimpleNamespace(message=Reply(self.count % 2 == 1))])
    monkeypatch.setattr(chat, "client", FakeAI)
    auth = ("alice", "alice123")
    session = client.post("/api/chat/sessions", auth=auth, json={"title": "Agent"}).json()["id"]
    def prepare():
        response = client.post(f"/api/chat/sessions/{session}/messages", auth=auth, json={"message": "Order one"})
        assert response.status_code == 200, response.text
        return response.json()["metadata"]["pending_actions"][0]["id"]
    action = prepare()
    assert client.get(f"/api/menu_items/{item['id']}").json()["capacity"] == 3
    assert client.post(f"/api/chat/actions/{action}/confirm", auth=("bob", "bob123"), json={"confirm": True}).status_code == 404
    first = client.post(f"/api/chat/actions/{action}/confirm", auth=auth, json={"confirm": True})
    assert first.status_code == 200, first.text
    again = client.post(f"/api/chat/actions/{action}/confirm", auth=auth, json={"confirm": True})
    assert again.json() == first.json()
    assert client.get(f"/api/menu_items/{item['id']}").json()["capacity"] == 2
    changed = prepare()
    item["price"] = "80.00"
    item["capacity"] = 2
    assert client.put(f"/api/menu_items/{item['id']}", auth=("admin", "admin123"), json=item).status_code == 200
    assert client.post(f"/api/chat/actions/{changed}/confirm", auth=auth, json={"confirm": True}).status_code == 409
    assert client.get(f"/api/menu_items/{item['id']}").json()["capacity"] == 2
    rejected = prepare()
    assert client.post(f"/api/chat/actions/{rejected}/confirm", auth=auth, json={"confirm": False}).json()["status"] == "REJECTED"
    assert client.post(f"/api/chat/actions/{rejected}/confirm", auth=auth, json={"confirm": True}).status_code == 409
    expired = prepare()
    from datetime import timedelta
    from database import SessionLocal
    from models import PendingAction, now
    with SessionLocal() as db:
        db.get(PendingAction, expired).expires_at = now() - timedelta(seconds=1)
        db.commit()
    assert client.post(f"/api/chat/actions/{expired}/confirm", auth=auth, json={"confirm": True}).status_code == 409
    assert client.get(f"/api/menu_items/{item['id']}").json()["capacity"] == 2
    monkeypatch.setattr(chat, "internal_request", original_request)


def test_document_upload_and_retrieval(client, monkeypatch, tmp_path):
    monkeypatch.setattr(rag, "UPLOAD_DIR", tmp_path)
    class Embeddings:
        def create(self, **kwargs):
            return SimpleNamespace(data=[SimpleNamespace(embedding=[1.0, 0.0]) for _ in kwargs["input"]])
    class Collection:
        def upsert(self, **kwargs):
            self.stored = kwargs
        def query(self, **kwargs):
            return {"documents": [[self.stored["documents"][0]]], "metadatas": [[self.stored["metadatas"][0]]], "distances": [[0.1]]}
    vector_store = Collection()
    monkeypatch.setattr(rag, "client", lambda: SimpleNamespace(embeddings=Embeddings()))
    monkeypatch.setattr(rag, "collection", lambda: vector_store)
    filename = f"policy-{uuid4().hex}.txt"
    response = client.post("/api/documents", auth=("admin", "admin123"),
                           files={"file": (filename, b"Masala Dosa contains mustard. Cross-contact cannot be ruled out.", "text/plain")})
    assert response.status_code == 201, response.text
    from database import SessionLocal
    with SessionLocal() as db:
        sources = rag.retrieve(db, "What allergens are in Masala Dosa?")
    assert sources[0]["filename"] == filename
    assert sources[0]["page"] == "1"
    assert "mustard" in sources[0]["text"]
    assert client.post("/api/documents", auth=("alice", "alice123"), files={"file": ("x.txt", b"test")}).status_code == 403
