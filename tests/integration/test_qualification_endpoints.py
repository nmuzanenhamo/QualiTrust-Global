"""Integration tests for qualification CRUD endpoints."""


class TestQualificationEndpoints:
    """Integration tests for qualification API endpoints."""

    def test_create_qualification(self, client, verifier_headers, sample_qualification_data):
        """Test creating a qualification via API."""
        response = client.post(
            "/api/v1/qualifications/",
            json=sample_qualification_data,
            headers=verifier_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == sample_qualification_data["title"]
        assert data["status"] == "pending"
        assert "id" in data

    def test_create_qualification_as_viewer_denied(self, client, viewer_headers, sample_qualification_data):
        """Test that viewers cannot create qualifications."""
        response = client.post(
            "/api/v1/qualifications/",
            json=sample_qualification_data,
            headers=viewer_headers,
        )
        assert response.status_code == 403

    def test_create_qualification_no_auth(self, client, sample_qualification_data):
        """Test creating qualification without auth fails."""
        response = client.post(
            "/api/v1/qualifications/",
            json=sample_qualification_data,
        )
        assert response.status_code == 401

    def test_get_qualification(self, client, verifier_headers, admin_headers, sample_qualification_data):
        """Test getting a qualification by ID."""
        create = client.post(
            "/api/v1/qualifications/",
            json=sample_qualification_data,
            headers=verifier_headers,
        )
        qual_id = create.json()["id"]
        response = client.get(f"/api/v1/qualifications/{qual_id}", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["id"] == qual_id

    def test_get_qualification_not_found(self, client, admin_headers):
        """Test getting a nonexistent qualification returns 404."""
        response = client.get("/api/v1/qualifications/9999", headers=admin_headers)
        assert response.status_code == 404

    def test_search_qualifications(self, client, verifier_headers, admin_headers, sample_qualification_data):
        """Test searching qualifications."""
        client.post(
            "/api/v1/qualifications/",
            json=sample_qualification_data,
            headers=verifier_headers,
        )
        response = client.get(
            "/api/v1/qualifications/",
            params={"query": "Computer"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_search_with_pagination(self, client, admin_headers):
        """Test pagination in search results."""
        response = client.get(
            "/api/v1/qualifications/",
            params={"page": 1, "page_size": 5},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    def test_update_qualification(self, client, verifier_headers, admin_headers, sample_qualification_data):
        """Test updating a qualification."""
        create = client.post(
            "/api/v1/qualifications/",
            json=sample_qualification_data,
            headers=verifier_headers,
        )
        qual_id = create.json()["id"]
        response = client.put(
            f"/api/v1/qualifications/{qual_id}",
            json={"title": "Updated Title"},
            headers=verifier_headers,
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_delete_qualification(self, client, verifier_headers, admin_headers, sample_qualification_data):
        """Test soft deleting a qualification."""
        create = client.post(
            "/api/v1/qualifications/",
            json=sample_qualification_data,
            headers=verifier_headers,
        )
        qual_id = create.json()["id"]
        response = client.delete(f"/api/v1/qualifications/{qual_id}", headers=verifier_headers)
        assert response.status_code == 204
        get_response = client.get(f"/api/v1/qualifications/{qual_id}", headers=admin_headers)
        assert get_response.status_code == 404

    def test_health_check(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
