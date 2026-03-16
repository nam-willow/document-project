from io import BytesIO
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_upload_image_stub():
    fake_image = BytesIO(b"fake image content")
    response = client.post(
        "/api/v1/files/upload",
        files={"file": ("sample.jpg", fake_image, "image/jpeg")},
        data={"save_to_db": "false"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_type"] == "image"
    assert "extracted_data" in payload


def test_upload_pdf_stub():
    fake_pdf = BytesIO(b"%PDF-1.4 fake pdf content")
    response = client.post(
        "/api/v1/files/upload",
        files={"file": ("sample.pdf", fake_pdf, "application/pdf")},
        data={"save_to_db": "false"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_type"] == "pdf"
    assert "extracted_data" in payload