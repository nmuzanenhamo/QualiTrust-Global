"""Integration tests for verification and audit endpoints."""

from app.services.blockchain_service import BlockchainService


class TestVerificationEndpoints:
    """Integration tests for verification API endpoints."""

    def test_verify_qualification(self, client, verifier_headers, sample_qualification_data):
        """Test verifying a qualification via API."""
        create = client.post(
            "/api/v1/qualifications/",
            json=sample_qualification_data,
            headers=verifier_headers,
        )
        qual_id = create.json()["id"]

        # Need to assign hash first via direct DB access
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        from app.models import Qualification
        qual = db.query(Qualification).filter(Qualification.id == qual_id).first()
        BlockchainService.assign_hash(db, qual)
        db.close()

        response = client.post(
            f"/api/v1/qualifications/{qual_id}/verify",
            params={"method": "blockchain"},
            headers=verifier_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "is_authentic" in data
        assert "result" in data
        assert "verification_hash" in data

    def test_verify_nonexistent_qualification(self, client, verifier_headers):
        """Test verifying a nonexistent qualification returns 404."""
        response = client.post(
            "/api/v1/qualifications/9999/verify",
            headers=verifier_headers,
        )
        assert response.status_code == 404

    def test_verify_as_viewer_denied(self, client, viewer_headers):
        """Test that viewers cannot verify qualifications."""
        response = client.post(
            "/api/v1/qualifications/1/verify",
            headers=viewer_headers,
        )
        assert response.status_code == 403

    def test_get_verification_history(self, client, verifier_headers, sample_qualification_data):
        """Test getting verification history for a qualification."""
        create = client.post(
            "/api/v1/qualifications/",
            json=sample_qualification_data,
            headers=verifier_headers,
        )
        qual_id = create.json()["id"]

        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        from app.models import Qualification
        qual = db.query(Qualification).filter(Qualification.id == qual_id).first()
        BlockchainService.assign_hash(db, qual)
        db.close()

        client.post(
            f"/api/v1/qualifications/{qual_id}/verify",
            headers=verifier_headers,
        )

        response = client.get(
            f"/api/v1/qualifications/{qual_id}/verifications",
            headers=verifier_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


class TestAuditEndpoints:
    """Integration tests for audit log API endpoints."""

    def test_get_audit_logs(self, client, admin_headers):
        """Test getting audit logs."""
        response = client.get("/api/v1/audit-logs/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data

    def test_get_audit_logs_no_auth(self, client):
        """Test accessing audit logs without auth fails."""
        response = client.get("/api/v1/audit-logs/")
        assert response.status_code == 401

    def test_get_audit_log_by_id(self, client, admin_headers):
        """Test getting a specific audit log."""
        response = client.get("/api/v1/audit-logs/1", headers=admin_headers)
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "action" in data
        else:
            assert response.status_code == 404


class TestAIEndpoint:
    """Integration tests for AI analysis endpoint."""

    def test_analyze_credential(self, client, verifier_headers, sample_qualification_data):
        """Test AI credential analysis."""
        create = client.post(
            "/api/v1/qualifications/",
            json=sample_qualification_data,
            headers=verifier_headers,
        )
        qual_id = create.json()["id"]
        response = client.post(
            f"/api/v1/ai/analyze/{qual_id}",
            headers=verifier_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "confidence_score" in data
        assert "recommendation" in data
        assert "anomalies" in data

    def test_analyze_nonexistent(self, client, verifier_headers):
        """Test analyzing a nonexistent qualification returns 404."""
        response = client.post(
            "/api/v1/ai/analyze/9999",
            headers=verifier_headers,
        )
        assert response.status_code == 404
