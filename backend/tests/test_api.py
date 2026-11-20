"""Recorrido completo de la API sin red ni claves (modo semilla)."""
from app.agents import explorer


def test_health_and_status(client):
    assert client.get("/health").json()["ok"] is True
    s = client.get("/api/status").json()
    assert s["items_total"] >= 40
    assert s["claude"]["enabled"] is False


def test_feed_pagination_no_duplicates(client):
    r = client.get("/api/feed", params={"limit": 8}).json()
    sid = r["session"]
    ids = [i["id"] for i in r["items"]]
    assert len(ids) == 8
    r2 = client.get("/api/feed", params={"limit": 8, "offset": 8, "session": sid}).json()
    ids2 = [i["id"] for i in r2["items"]]
    assert not set(ids) & set(ids2)
    for it in r["items"]:
        assert it["score"]["reasons"] is not None
        assert set(it["score"]["parts"]) >= {"relevance", "quality", "recency", "credibility", "novelty"}


def test_feed_diversity(client):
    items = client.get("/api/feed", params={"limit": 12}).json()["items"]
    cats = [i["category"] for i in items]
    assert len(set(cats)) >= 4  # cubre varias de las 6 áreas
    for a, b, c in zip(cats, cats[1:], cats[2:]):
        assert not (a == b == c), "tres seguidos de la misma categoría"


def test_format_filter(client):
    items = client.get("/api/feed", params={"limit": 10, "format": "long"}).json()["items"]
    assert items and all(i["format"] == "long" for i in items)


def test_like_save_learn_and_hide(client):
    item = client.get("/api/feed", params={"limit": 1, "category": "ciberseguridad"}).json()["items"][0]
    r = client.post(f"/api/items/{item['id']}/events", json={"kind": "like"}).json()
    assert r["state"]["liked"]
    r = client.post(f"/api/items/{item['id']}/events", json={"kind": "save"}).json()
    assert r["state"]["saved"]
    prefs = client.get("/api/preferences").json()
    assert any(p["key"] == "cat:ciberseguridad" for p in prefs["likes"])
    saved = client.get("/api/saved").json()
    assert item["id"] in [s["id"] for s in saved]
    assert item["id"] in [s["id"] for s in client.get("/api/liked").json()]
    # Lo guardado ya no reaparece en el feed
    feed_ids = [i["id"] for i in client.get("/api/feed", params={"limit": 30}).json()["items"]]
    assert item["id"] not in feed_ids


def test_hide_negative_signal(client):
    item = client.get("/api/feed", params={"limit": 1, "category": "deporte"}).json()["items"][0]
    client.post(f"/api/items/{item['id']}/events", json={"kind": "hide"})
    feed_ids = [i["id"] for i in client.get("/api/feed", params={"limit": 30}).json()["items"]]
    assert item["id"] not in feed_ids


def test_view_goes_to_history(client):
    item = client.get("/api/feed", params={"limit": 1, "category": "mente"}).json()["items"][0]
    client.post(f"/api/items/{item['id']}/events", json={"kind": "view", "value": 40})
    hist = client.get("/api/history").json()
    assert hist[0]["id"] == item["id"]


def test_note_and_collection(client):
    item = client.get("/api/feed", params={"limit": 1, "category": "ia"}).json()["items"][0]
    r = client.put(f"/api/items/{item['id']}/note", json={"note": "Aprendí qué es la atención", "collection": "IA"}).json()
    assert r["state"]["note"] and r["state"]["saved"] and r["state"]["collection"] == "IA"
    assert any(n["id"] == item["id"] for n in client.get("/api/notes").json())
    assert any(c["key"] == "IA" for c in client.get("/api/collections").json())
    review = client.get("/api/review", params={"n": 10}).json()
    assert review and all("points" in x for x in review)


def test_written_command_focuses_feed(client):
    r = client.post("/api/commands", json={"text": "Enséñame proyectos interesantes de ciberseguridad"}).json()
    assert "ciberseguridad" in r["parsed"]["categories"]
    feed = client.get("/api/feed", params={"limit": 6}).json()
    assert feed["command"] and feed["command"]["id"] == r["id"]
    assert all(i["category"] == "ciberseguridad" for i in feed["items"])
    assert client.delete("/api/commands/active").json()["ok"]
    assert client.get("/api/feed", params={"limit": 3}).json()["command"] is None
    assert client.get("/api/commands").json()[0]["text"].startswith("Enséñame")


def test_category_weight_and_disable(client):
    client.patch("/api/categories/deporte", json={"enabled": False})
    items = client.get("/api/feed", params={"limit": 20}).json()["items"]
    assert all(i["category"] != "deporte" for i in items)
    client.patch("/api/categories/deporte", json={"enabled": True, "weight": 2.0})
    cats = {c["slug"]: c for c in client.get("/api/categories").json()}
    assert cats["deporte"]["weight"] == 2.0 and cats["deporte"]["enabled"]
    assert len(cats) == 6 and all(len(c["subtopics"]) == 5 for c in cats.values())


def test_usage_limit_and_extend(client):
    client.patch("/api/settings", json={"daily_limit_minutes": 1})
    st = client.post("/api/usage/heartbeat", json={"seconds": 70, "category": "ia", "items_viewed": 2}).json()
    assert st["exceeded"]
    st = client.post("/api/usage/extend", json={"minutes": 10}).json()
    assert not st["exceeded"] and st["extra_minutes"] == 10
    assert client.get("/api/feed", params={"limit": 1}).json()["usage"]["limit_seconds"] == 660
    stats = client.get("/api/stats").json()
    assert stats["total_minutes"] > 1 and stats["by_category"][0]["slug"] == "ia"
    client.patch("/api/settings", json={"daily_limit_minutes": 45})


def test_settings_validation(client):
    assert client.patch("/api/settings", json={"nope": 1}).status_code == 422
    assert client.patch("/api/settings", json={"autoplay": "si"}).status_code == 422
    assert client.patch("/api/settings", json={"autoplay": False}).json()["autoplay"] is False


def test_creator_suggestions_flow(client):
    sugg = client.get("/api/creators", params={"status": "suggested"}).json()
    assert len(sugg) >= 2
    a, b = sugg[0], sugg[1]
    assert client.patch(f"/api/creators/{a['id']}", json={"status": "approved"}).json()["status"] == "approved"
    assert client.patch(f"/api/creators/{b['id']}", json={"status": "rejected"}).json()["status"] == "rejected"
    assert len(client.get("/api/creators", params={"status": "suggested"}).json()) == len(sugg) - 2


def test_highlights(client):
    h = client.get("/api/highlights").json()
    assert len(h["items"]) >= 6
    assert h["headline"]
    assert len({i["category"] for i in h["items"]}) >= 5


def test_search(client):
    res = client.get("/api/search", params={"q": "neural network"}).json()
    assert res and "neural" in res[0]["title"].lower()


def test_add_link_without_network(client, monkeypatch):
    async def fake_resolve(_client, info):
        return {**info, "title": "Cómo entrenar velocidad en futsal", "author_name": "Coach", "verified": True}

    monkeypatch.setattr(explorer, "resolve_link", fake_resolve)
    r = client.post("/api/items", json={"url": "https://www.tiktok.com/@coach/video/7311111111111111111"})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["platform"] == "tiktok" and d["category"] == "deporte" and d["state"]["saved"]
    # idempotente
    assert client.post("/api/items", json={"url": "https://www.tiktok.com/@coach/video/7311111111111111111"}).json()["id"] == d["id"]
    assert client.post("/api/items", json={"url": "nada"}).status_code in (201, 422)


def test_broken_report(client):
    item = client.get("/api/feed", params={"limit": 1, "format": "long"}).json()["items"][0]
    assert client.post(f"/api/items/{item['id']}/broken").json()["ok"]
    assert client.get(f"/api/items/{item['id']}").json()["id"] == item["id"]


def test_reset_preferences(client):
    assert client.delete("/api/preferences").json()["ok"]
    assert client.get("/api/preferences").json()["likes"] == []
