"""get_material_reference tool — looks up construction material data.

All data comes from the local ``material_references.json`` file.
No external API or database is contacted.
"""

from __future__ import annotations

import json
import logging
import importlib.resources
from typing import Any

from construction_reference_mcp_remote.config import DEFAULT_LOCATION

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DISCLAIMER: str = (
    "Reference values only. Actual prices may vary by supplier, quality, "
    "location, date, quantity, and delivery conditions."
)

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_materials() -> list[dict[str, Any]]:
    """Read and return the materials list from the JSON data file."""
    # Use importlib.resources to access the file regardless of installation path
    data_file = importlib.resources.files("construction_reference_mcp_remote.data").joinpath("material_references.json")
    
    with data_file.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data["materials"]


def _build_lookup() -> dict[str, dict[str, Any]]:
    """Build a case-insensitive lookup mapping aliases → material records."""
    materials = _load_materials()
    lookup: dict[str, dict[str, Any]] = {}
    for mat in materials:
        # Index by canonical name and each alias.
        for key in [mat["canonical_name"]] + mat.get("aliases", []):
            lookup[key.lower()] = mat
    return lookup


# Module-level lookup table (built once on first import).
_MATERIAL_LOOKUP: dict[str, dict[str, Any]] = _build_lookup()

# ---------------------------------------------------------------------------
# MCP tool definition (returned by tools/list)
# ---------------------------------------------------------------------------

TOOL_DEFINITION: dict[str, Any] = {
    "name": "get_material_reference",
    "description": (
        "Returns general reference information (category, unit, approximate "
        "price range, observations) for a construction material. "
        "Data is illustrative and located in Guatemala by default."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "material_name": {
                "type": "string",
                "description": "Name or common alias of the construction material to look up.",
            },
            "location": {
                "type": "string",
                "description": "Location context for the reference data. Defaults to 'Guatemala'.",
            },
        },
        "required": ["material_name"],
    },
}

# ---------------------------------------------------------------------------
# Tool execution (called by tools/call)
# ---------------------------------------------------------------------------

def execute(params: dict[str, Any]) -> dict[str, Any]:
    """Execute the get_material_reference tool.

    Returns a result dict on success.
    Raises ``MaterialNotFoundError`` when the material is unknown.
    """
    material_name: str = params.get("material_name", "").strip()
    location: str = params.get("location", DEFAULT_LOCATION).strip() or DEFAULT_LOCATION

    if not material_name:
        raise ValueError("'material_name' is required and must not be empty.")

    key = material_name.lower()
    mat = _MATERIAL_LOOKUP.get(key)

    if mat is None:
        raise MaterialNotFoundError(material_name)

    return {
        "material_name": mat["canonical_name"],
        "category": mat["category"],
        "unit": mat["unit"],
        "reference_price_range": {
            "minimum": mat["reference_price_min"],
            "maximum": mat["reference_price_max"],
            "currency": mat["currency"],
        },
        "reference_updated_at": mat["reference_updated_at"],
        "location": location,
        "observations": mat.get("observations", []),
        "disclaimer": DISCLAIMER,
    }


class MaterialNotFoundError(Exception):
    """Raised when a material name/alias is not found in the reference data."""

    def __init__(self, material_name: str) -> None:
        self.material_name = material_name
        super().__init__(
            f"Material '{material_name}' not found in the reference database. "
            "Check the spelling or try a common alias."
        )
