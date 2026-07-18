"""
Single source of truth for IronWatch v1 environment configuration.

Every notebook and script must obtain workspace settings through
get_config() / get_lakehouse_path() — never read os.environ (or load
.env) directly. Centralizing resolution here means the v1 -> v2 cutover
is mechanical: this module will become forge_core.config during
IronCore extraction in July 2026, at which point the env-var lookups
below will be replaced by Fabric Variable Library calls without any
caller having to change.

v1 reads configuration from environment variables only (see
.env.template). Variable Library integration is an IronCore concern,
not a v1 concern.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

ONELAKE_HOST = "onelake.dfs.fabric.microsoft.com"

DEFAULT_ENVIRONMENT = "dev"

# Fabric item type per medallion layer — Gold is a Warehouse, not a
# Lakehouse (ADR-001); Silver is also a Warehouse as of ADR-010
# (re-provisioned 2026-07-18, superseding its original Lakehouse
# item). The abfss path suffix differs by layer accordingly.
_ITEM_TYPES = {
    "bronze": "Lakehouse",
    "silver": "Warehouse",
    "gold": "Warehouse",
}


class ConfigurationError(Exception):
    """Raised when required IronWatch configuration is missing or invalid."""


@dataclass(frozen=True)
class WorkspaceConfig:
    workspace_name: str
    lakehouse_bronze: str
    lakehouse_silver: str
    warehouse_gold: str
    environment: str
    output_path: str

    def item_name(self, layer: str) -> str:
        try:
            return {
                "bronze": self.lakehouse_bronze,
                "silver": self.lakehouse_silver,
                "gold": self.warehouse_gold,
            }[layer]
        except KeyError as exc:
            raise ConfigurationError(
                f"Unknown layer '{layer}' - expected one of: bronze, silver, gold"
            ) from exc


def _require(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value or value.strip().startswith("<"):
        raise ConfigurationError(
            f"Missing required configuration: '{var_name}' is not set. "
            f"Copy .env.template to .env and fill in real values before running."
        )
    return value


def get_config() -> WorkspaceConfig:
    """Resolve and return all workspace-level settings as a WorkspaceConfig."""
    load_dotenv()

    environment = os.getenv("IRONWATCH_ENV", DEFAULT_ENVIRONMENT).lower()
    workspace_var = f"FABRIC_WORKSPACE_{environment.upper()}"

    return WorkspaceConfig(
        workspace_name=_require(workspace_var),
        lakehouse_bronze=_require("FABRIC_LAKEHOUSE_BRONZE"),
        lakehouse_silver=_require("FABRIC_LAKEHOUSE_SILVER"),
        warehouse_gold=_require("FABRIC_WAREHOUSE_GOLD"),
        environment=environment,
        output_path=os.getenv("SYNTHETIC_OUTPUT_PATH", "./synthetic_data/output/"),
    )


# Fabric item IDs for ModernAnalyticsLab-DEV, provisioned 2026-06-20 via the
# Fabric REST API. Names above (FABRIC_WORKSPACE_DEV etc.) remain the
# authoritative source for path construction; these IDs are recorded for
# automation that needs a direct item reference (e.g. REST calls that take
# an itemId rather than resolving by displayName) instead of re-resolving
# names to IDs on every run. Bronze also carries a OneLake shortcut
# ("ironwatch-landing", via Fabric connection 8b72d01d-1f45-4c66-b08c-
# e5883f6d5184) live against fabricf2landingsa/ironwatch-landing — not an
# item itself, so not listed below.
FABRIC_WORKSPACE_ID = "e0bb7021-f3a3-430f-a739-442d4be7a40f"
FABRIC_ITEM_IDS = {
    "ironwatch_bronze": "7f1e5fd6-7fbc-4ea1-b31a-fd8baa978349",
    # ironwatch_silver re-provisioned as a Warehouse 2026-07-18 (ADR-010);
    # this is the new item's ID — the original Lakehouse ID
    # (751457c4-0644-447b-a688-d63c6950a5df) no longer exists.
    "ironwatch_silver": "d500a99b-6f2a-41d8-9cf4-97a8153931d9",
    "ironwatch_gold": "6c377782-795b-4b95-85c5-96231d43174c",
}


def get_lakehouse_path(layer: str) -> str:
    """Return the abfss:// OneLake path for the given medallion layer.

    `layer` must be one of "bronze", "silver", "gold". The returned path
    points at the Lakehouse (bronze/silver) or Warehouse (gold) item root.
    """
    layer = layer.lower()
    item_type = _ITEM_TYPES.get(layer)
    if item_type is None:
        raise ConfigurationError(
            f"Unknown layer '{layer}' - expected one of: bronze, silver, gold"
        )

    config = get_config()
    item_name = config.item_name(layer)

    return f"abfss://{config.workspace_name}@{ONELAKE_HOST}/{item_name}.{item_type}"
