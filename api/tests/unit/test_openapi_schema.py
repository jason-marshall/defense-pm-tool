"""Tests for OpenAPI schema validation and documentation completeness."""

import pytest

from src.main import app


class TestOpenAPISchema:
    """Tests for OpenAPI schema structure and completeness."""

    @pytest.fixture
    def openapi_schema(self) -> dict:
        """Get the OpenAPI schema from the app."""
        # Use app.openapi() to get the complete schema including tags
        return app.openapi()

    def test_openapi_schema_has_info(self, openapi_schema: dict) -> None:
        """Schema should have info section with required fields."""
        assert "info" in openapi_schema
        info = openapi_schema["info"]
        assert info["title"] == "Defense PM Tool API"
        assert "version" in info
        assert "description" in info

    def test_openapi_schema_has_paths(self, openapi_schema: dict) -> None:
        """Schema should have paths defined."""
        assert "paths" in openapi_schema
        assert len(openapi_schema["paths"]) > 0

    def test_openapi_schema_has_tags(self, openapi_schema: dict) -> None:
        """Schema should have tag definitions for endpoint grouping."""
        assert "tags" in openapi_schema
        tags = openapi_schema["tags"]
        assert len(tags) > 0

        # Check expected tags are present
        tag_names = [tag["name"] for tag in tags]
        expected_tags = [
            "Authentication",
            "Programs",
            "Activities",
            "Dependencies",
            "WBS",
        ]
        for expected in expected_tags:
            assert expected in tag_names, f"Expected tag '{expected}' not found"

    def test_openapi_schema_has_components(self, openapi_schema: dict) -> None:
        """Schema should have components section with schemas."""
        assert "components" in openapi_schema
        assert "schemas" in openapi_schema["components"]
        schemas = openapi_schema["components"]["schemas"]
        assert len(schemas) > 0

    def test_error_schemas_defined(self, openapi_schema: dict) -> None:
        """Error response schemas should be defined in components."""
        schemas = openapi_schema["components"]["schemas"]

        # These error schemas should be defined
        expected_error_schemas = [
            "ValidationErrorResponse",
            "AuthenticationErrorResponse",
            "AuthorizationErrorResponse",
            "NotFoundErrorResponse",
        ]

        for schema_name in expected_error_schemas:
            assert schema_name in schemas, f"Error schema '{schema_name}' not defined"

    def test_authentication_endpoints_documented(self, openapi_schema: dict) -> None:
        """Authentication endpoints should have proper documentation."""
        paths = openapi_schema["paths"]

        # Check register endpoint
        assert "/api/v1/auth/register" in paths
        register = paths["/api/v1/auth/register"]["post"]
        assert "summary" in register
        assert "responses" in register
        assert "201" in register["responses"]

        # Check login endpoint
        assert "/api/v1/auth/login" in paths
        login = paths["/api/v1/auth/login"]["post"]
        assert "summary" in login
        assert "responses" in login
        assert "200" in login["responses"]

    def test_programs_endpoints_documented(self, openapi_schema: dict) -> None:
        """Programs endpoints should have proper documentation."""
        paths = openapi_schema["paths"]

        # Check list programs endpoint
        assert "/api/v1/programs" in paths
        list_programs = paths["/api/v1/programs"]["get"]
        assert "summary" in list_programs
        assert "responses" in list_programs
        assert "200" in list_programs["responses"]

        # Check create program endpoint
        create_program = paths["/api/v1/programs"]["post"]
        assert "summary" in create_program
        assert "responses" in create_program
        assert "201" in create_program["responses"]

    def test_activities_endpoints_documented(self, openapi_schema: dict) -> None:
        """Activities endpoints should have proper documentation."""
        paths = openapi_schema["paths"]

        assert "/api/v1/activities" in paths
        activities = paths["/api/v1/activities"]

        # GET should have response documentation
        get_activities = activities["get"]
        assert "summary" in get_activities
        assert "responses" in get_activities
        assert "200" in get_activities["responses"]

        # POST should have response documentation
        post_activity = activities["post"]
        assert "summary" in post_activity
        assert "responses" in post_activity
        assert "201" in post_activity["responses"]

    def test_all_endpoints_have_responses(self, openapi_schema: dict) -> None:
        """All endpoints should have at least one response defined."""
        paths = openapi_schema["paths"]

        for path, methods in paths.items():
            for method, details in methods.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    assert "responses" in details, f"{method.upper()} {path} missing responses"
                    assert len(details["responses"]) > 0, (
                        f"{method.upper()} {path} has no responses"
                    )

    def test_all_endpoints_have_summary(self, openapi_schema: dict) -> None:
        """All endpoints should have a summary defined."""
        paths = openapi_schema["paths"]

        # Skip health and root endpoints which may not have summary
        skip_paths = ["/health", "/"]

        for path, methods in paths.items():
            if path in skip_paths:
                continue
            for method, details in methods.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    # Summary or operationId should be present
                    has_summary = "summary" in details or "operationId" in details
                    assert has_summary, f"{method.upper()} {path} missing summary"


class TestErrorResponseSchemas:
    """Tests for error response schema structure."""

    @pytest.fixture
    def openapi_schema(self) -> dict:
        """Get the OpenAPI schema from the app."""
        return app.openapi()

    def test_validation_error_schema_structure(self, openapi_schema: dict) -> None:
        """ValidationErrorResponse should have correct structure."""
        schemas = openapi_schema["components"]["schemas"]
        if "ValidationErrorResponse" in schemas:
            schema = schemas["ValidationErrorResponse"]
            assert "properties" in schema
            assert "detail" in schema["properties"]

    def test_not_found_error_schema_structure(self, openapi_schema: dict) -> None:
        """NotFoundErrorResponse should have correct structure."""
        schemas = openapi_schema["components"]["schemas"]
        if "NotFoundErrorResponse" in schemas:
            schema = schemas["NotFoundErrorResponse"]
            assert "properties" in schema
            assert "detail" in schema["properties"]
            assert "code" in schema["properties"]

    def test_authentication_error_schema_structure(self, openapi_schema: dict) -> None:
        """AuthenticationErrorResponse should have correct structure."""
        schemas = openapi_schema["components"]["schemas"]
        if "AuthenticationErrorResponse" in schemas:
            schema = schemas["AuthenticationErrorResponse"]
            assert "properties" in schema
            assert "detail" in schema["properties"]
            assert "code" in schema["properties"]


class TestAPIDescription:
    """Tests for API description and metadata."""

    def test_app_has_description(self) -> None:
        """App should have a description."""
        assert app.description is not None
        assert len(app.description) > 100  # Should be substantial

    def test_app_has_version(self) -> None:
        """App should have a version."""
        assert app.version is not None

    def test_app_has_title(self) -> None:
        """App should have a title."""
        assert app.title == "Defense PM Tool API"

    def test_app_has_openapi_tags(self) -> None:
        """App should have OpenAPI tags configured."""
        assert app.openapi_tags is not None
        assert len(app.openapi_tags) > 0

    def test_tag_descriptions(self) -> None:
        """Tags should have descriptions."""
        for tag in app.openapi_tags:
            assert "name" in tag, "Tag missing name"
            assert "description" in tag, f"Tag '{tag.get('name')}' missing description"
            assert len(tag["description"]) > 10, f"Tag '{tag.get('name')}' has short description"
