from fastapi.testclient import TestClient

import src.history as history
from api.main import app
from src.serving import sample_orders


def test_score_saves_record_and_history_endpoint_returns_it(tmp_path, monkeypatch):
    # Isolate this test from any project or production database.
    monkeypatch.setattr(history, "DB_PATH", tmp_path / "test_history.db")

    samples = sample_orders(n_per_tier=2)
    payload = next(
        order["payload"]
        for order in samples["orders"]
        if order["label"] == "REVIEW"
    )

    with TestClient(app) as client:
        before = client.get("/predictions")
        assert before.status_code == 200
        assert before.json()["count"] == 0

        scored = client.post("/score?explain_plainly=false", json=payload)
        assert scored.status_code == 200, scored.text

        result = scored.json()
        history_response = client.get("/predictions?limit=10")

        assert history_response.status_code == 200
        body = history_response.json()
        assert body["count"] == 1
        assert len(body["predictions"]) == 1

        record = body["predictions"][0]
        assert record["order_id"] == result["order_id"]
        assert record["action_label"] == result["action_label"]
        assert record["rto_probability"] == result["rto_probability"]
        assert "address_line" not in record
        assert "customer_history" not in record

        # The original /score response contract remains unchanged.
        assert "expected_loss_if_shipped_inr" in result
