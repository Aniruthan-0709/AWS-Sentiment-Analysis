import io
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend import utils
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_login_returns_tokens(client):
    tokens = {"access_token": "a", "id_token": "i", "refresh_token": "r"}
    with patch("backend.main.authenticate_user", return_value=tokens) as auth:
        response = client.post("/login", json={"username": "u", "password": "p"})

    assert response.status_code == 200
    assert response.json()["tokens"] == tokens
    auth.assert_called_once_with("u", "p")


def test_login_keeps_auth_error_status(client):
    error = HTTPException(status_code=401, detail="Invalid username or password.")
    with patch("backend.main.authenticate_user", side_effect=error):
        response = client.post("/login", json={"username": "u", "password": "bad"})

    assert response.status_code == 401


def test_login_rejects_missing_password(client):
    response = client.post("/login", json={"username": "u"})

    assert response.status_code == 422


def test_trigger_pipeline_passes_file_and_user(client):
    with patch("backend.main.trigger_ecs_pipeline", return_value="task-arn") as trigger:
        response = client.post("/trigger_pipeline", json={"filename": "f.csv", "user": "u"})

    assert response.status_code == 200
    assert response.json() == {"status": "pipeline_triggered", "task_arn": "task-arn"}
    trigger.assert_called_once_with("f.csv", "u")


def test_generate_dashboard_endpoint_maps_missing_file_to_404(client):
    with patch("backend.main.generate_dashboard", side_effect=FileNotFoundError("served.csv")):
        response = client.post("/generate_dashboard", json={"filename": "f.csv", "user": "u"})

    assert response.status_code == 404


def test_trigger_ecs_pipeline_sends_user_and_file_to_container():
    ecs = MagicMock()
    ecs.run_task.return_value = {"tasks": []}
    with patch.object(utils, "ecs_client", ecs):
        utils.trigger_ecs_pipeline("f.csv", "u")

    override = ecs.run_task.call_args.kwargs["overrides"]["containerOverrides"][0]
    assert override["name"] == "sentiment-pipeline"
    assert {"name": "USER_NAME", "value": "u"} in override["environment"]
    assert {"name": "FILENAME", "value": "f.csv"} in override["environment"]


def test_generate_dashboard_writes_summary_to_s3():
    csv_body = (
        "review,prediction,short_review\n"
        "great product,positive,False\n"
        "love it,positive,True\n"
        "awful,negative,True\n"
    )
    s3 = MagicMock()
    s3.get_object.return_value = {"Body": io.BytesIO(csv_body.encode())}
    with patch.object(utils, "s3", s3):
        utils.generate_dashboard("u", "f.csv")

    s3.get_object.assert_called_once_with(Bucket="test-bucket", Key="output/u/served.csv")
    written = s3.put_object.call_args.kwargs
    assert written["Key"] == "metadata/u/inference_summary.json"

    summary = json.loads(written["Body"])
    assert summary["total_reviews"] == 3
    assert summary["positive_reviews"] == 2
    assert summary["negative_reviews"] == 1
    assert summary["neutral_reviews"] == 0
    assert summary["short_reviews_flagged"] == 2
    assert summary["top_negative_reviews"] == ["awful"]
