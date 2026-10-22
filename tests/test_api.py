import io
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_validate_single_product_normalization():
    """Verifica que Pydantic limpie espacios y convierta códigos a mayúsculas"""
    dirty_payload = {
        "sku": "  mat-777  ",
        "product_name": "  Meguiars Foam Cannon Shampoo  ",
        "category": "Chemicals",
        "unit_price": 24.99,
        "currency": "usd",
        "uom": "l",
        "supplier_email": "info@meguiars.com",
    }
    response = client.post("/api/v1/products/validate", json=dirty_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["sku"] == "MAT-777"
    assert data["currency"] == "USD"
    assert data["uom"] == "L"
    assert data["validation_status"] == "VALID"


def test_validate_single_product_rejection():
    """Verifica que un SKU sin prefijo MAT-/SKU- o precio negativo devuelva 422"""
    bad_payload = {
        "sku": "BAD-999",
        "product_name": "Invalid Item",
        "category": "Tools",
        "unit_price": -10.0,
        "currency": "USD",
        "uom": "EA",
        "supplier_email": "not-an-email",
    }
    response = client.post("/api/v1/products/validate", json=bad_payload)
    assert response.status_code == 422


def test_upload_csv_unauthorized_without_valid_api_key():
    """Verifica que el endpoint rechace peticiones con un X-API-Key incorrecto"""
    csv_content = b"sku,product_name,category,unit_price,currency,uom,supplier_email\nMAT-1,Test,Tools,10,USD,EA,a@b.com"
    files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
    response = client.post(
        "/api/v1/products/upload-csv?persist_to_db=false",
        files=files,
        headers={"X-API-Key": "wrong-hacker-token"},
    )
    assert response.status_code == 401


def test_upload_csv_batch_processing_in_memory():
    """Verifica el conteo exacto de filas válidas vs rechazadas en un lote CSV"""
    csv_content = (
        "sku,product_name,category,unit_price,currency,uom,supplier_email\n"
        "MAT-501,Valid Coating,Chemicals,50.00,USD,EA,ok@vendor.com\n"
        "INVALID-502,Bad Prefix,Chemicals,-20.00,USD,GALON,bad_email\n"
    ).encode("utf-8")

    files = {"file": ("batch.csv", io.BytesIO(csv_content), "text/csv")}
    response = client.post(
        "/api/v1/products/upload-csv?persist_to_db=false",
        files=files,
        headers={"X-API-Key": "mdg-enterprise-secret-token-2026"},
    )
    assert response.status_code == 200
    summary = response.json()
    assert summary["total_rows_processed"] == 2
    assert summary["valid_count"] == 1
    assert summary["rejected_count"] == 1
    assert summary["data_quality_score_pct"] == 50.0
