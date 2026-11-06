"""OpenAPI contract for the export operation."""

from app.main import app


def test_export_openapi_contract():
    operation = app.openapi()["paths"]["/api/export"]["get"]
    assert "requestBody" not in operation
    assert not operation.get("parameters")
    assert {"200", "401", "403", "409"} <= operation["responses"].keys()
    success = operation["responses"]["200"]
    assert success["content"]["application/zip"]["schema"] == {
        "type": "string",
        "format": "binary",
    }
    assert "Content-Disposition" in success["headers"]
    assert "/export" not in app.openapi()["paths"]
