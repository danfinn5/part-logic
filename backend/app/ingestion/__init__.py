"""
Connector registry for ingestion sources.

Each connector module registers itself by calling register_connector().
The search route uses get_all_connectors() to fan out searches.
"""
from typing import Dict, List
from app.ingestion.base import BaseConnector

_registry: Dict[str, BaseConnector] = {}


def register_connector(connector: BaseConnector) -> None:
    """Register a connector instance by its source_name."""
    _registry[connector.source_name] = connector


def get_all_connectors() -> List[BaseConnector]:
    """Return all registered connector instances."""
    return list(_registry.values())


def get_connector(name: str) -> BaseConnector | None:
    """Return a specific connector by name."""
    return _registry.get(name)


def _register_all() -> None:
    """Import all connector modules so they self-register."""
    from app.ingestion.ebay import eBayConnector
    from app.ingestion.rockauto import RockAutoConnector
    from app.ingestion.row52 import Row52Connector
    from app.ingestion.carpart import CarPartConnector
    from app.ingestion.partsouq import PartsouqConnector
    from app.ingestion.ecstuning import ECSTuningConnector
    from app.ingestion.fcpeuro import FCPEuroConnector
    from app.ingestion.amazon import AmazonConnector
    from app.ingestion.partsgeek import PartsGeekConnector
    from app.ingestion.resources import ResourcesConnector

    register_connector(eBayConnector())
    register_connector(RockAutoConnector())
    register_connector(Row52Connector())
    register_connector(CarPartConnector())
    register_connector(PartsouqConnector())
    register_connector(ECSTuningConnector())
    register_connector(FCPEuroConnector())
    register_connector(AmazonConnector())
    register_connector(PartsGeekConnector())
    register_connector(ResourcesConnector())


_register_all()
