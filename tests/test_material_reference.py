"""Tests for the get_material_reference tool logic."""

from __future__ import annotations

import pytest

from construction_reference_mcp_remote.tools.material_reference import (
    DISCLAIMER,
    TOOL_DEFINITION,
    MaterialNotFoundError,
    execute,
)


class TestToolDefinition:
    """Verify the tool definition schema for tools/list."""

    def test_has_required_fields(self) -> None:
        assert TOOL_DEFINITION["name"] == "get_material_reference"
        assert "description" in TOOL_DEFINITION
        assert "inputSchema" in TOOL_DEFINITION

    def test_input_schema_requires_material_name(self) -> None:
        schema = TOOL_DEFINITION["inputSchema"]
        assert "material_name" in schema["properties"]
        assert "material_name" in schema["required"]

    def test_location_is_optional(self) -> None:
        schema = TOOL_DEFINITION["inputSchema"]
        assert "location" in schema["properties"]
        assert "location" not in schema["required"]


class TestExecute:
    """Test the execute() function with various inputs."""

    def test_canonical_name(self) -> None:
        result = execute({"material_name": "cement"})
        assert result["material_name"] == "cement"
        assert result["category"] == "binders"
        assert result["disclaimer"] == DISCLAIMER

    def test_alias_lookup(self) -> None:
        result = execute({"material_name": "rebar"})
        assert result["material_name"] == "reinforcing steel bar"

    def test_case_insensitive(self) -> None:
        result = execute({"material_name": "CEMENT"})
        assert result["material_name"] == "cement"

    def test_default_location(self) -> None:
        result = execute({"material_name": "sand"})
        assert result["location"] == "Guatemala"

    def test_custom_location(self) -> None:
        result = execute({"material_name": "sand", "location": "Quetzaltenango"})
        assert result["location"] == "Quetzaltenango"

    def test_price_range_validity(self) -> None:
        result = execute({"material_name": "gravel"})
        pr = result["reference_price_range"]
        assert pr["minimum"] > 0
        assert pr["maximum"] >= pr["minimum"]
        assert pr["currency"] == "GTQ"

    def test_observations_present(self) -> None:
        result = execute({"material_name": "interior paint"})
        assert isinstance(result["observations"], list)
        assert len(result["observations"]) > 0

    def test_reference_updated_at_present(self) -> None:
        result = execute({"material_name": "PVC pipe"})
        assert "reference_updated_at" in result

    def test_unknown_material_raises(self) -> None:
        with pytest.raises(MaterialNotFoundError):
            execute({"material_name": "unobtainium"})

    def test_empty_material_name_raises(self) -> None:
        with pytest.raises(ValueError):
            execute({"material_name": ""})

    def test_missing_material_name_raises(self) -> None:
        with pytest.raises(ValueError):
            execute({})

    def test_all_eleven_materials_accessible(self) -> None:
        """Verify every material listed in the brief is reachable."""
        names = [
            "concrete block 10 cm",
            "concrete block 15 cm",
            "cement",
            "sand",
            "gravel",
            "reinforcing steel bar",
            "electrical conduit",
            "electrical cable",
            "PVC pipe",
            "ceramic floor tile",
            "interior paint",
        ]
        for name in names:
            result = execute({"material_name": name})
            assert result["material_name"] == name

    def test_alias_bloque_15(self) -> None:
        result = execute({"material_name": "bloque 15"})
        assert result["material_name"] == "concrete block 15 cm"

    def test_alias_pintura(self) -> None:
        result = execute({"material_name": "pintura"})
        assert result["material_name"] == "interior paint"
