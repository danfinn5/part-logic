"""
NHTSA API integration — recalls, complaints, and manufacturer communications.

All endpoints are free, public domain, no API key required.
https://www.nhtsa.gov/nhtsa-datasets-and-apis
"""

import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

NHTSA_BASE = "https://api.nhtsa.gov"
RECALLS_URL = f"{NHTSA_BASE}/recalls/recallsByVehicle"
COMPLAINTS_URL = f"{NHTSA_BASE}/complaints/complaintsByVehicle"


@dataclass
class Recall:
    campaign_number: str
    component: str
    summary: str
    consequence: str
    remedy: str
    report_date: str | None = None


@dataclass
class Complaint:
    odi_number: str
    component: str
    summary: str
    crash: bool = False
    fire: bool = False
    date_of_incident: str | None = None


@dataclass
class NHTSAResult:
    recalls: list[Recall] = field(default_factory=list)
    complaints: list[Complaint] = field(default_factory=list)
    error: str | None = None


async def fetch_nhtsa_data(
    make: str,
    model: str,
    year: int | str,
) -> NHTSAResult:
    """
    Fetch recalls and complaints from NHTSA for a specific vehicle.
    Returns combined result. Both calls run in parallel.
    """
    import asyncio

    result = NHTSAResult()

    async with httpx.AsyncClient(timeout=10) as client:
        recalls_task = _fetch_recalls(client, make, model, year)
        complaints_task = _fetch_complaints(client, make, model, year)

        recalls_result, complaints_result = await asyncio.gather(recalls_task, complaints_task, return_exceptions=True)

        if isinstance(recalls_result, list):
            result.recalls = recalls_result
        elif isinstance(recalls_result, Exception):
            logger.warning(f"NHTSA recalls fetch failed: {recalls_result}")

        if isinstance(complaints_result, list):
            result.complaints = complaints_result
        elif isinstance(complaints_result, Exception):
            logger.warning(f"NHTSA complaints fetch failed: {complaints_result}")

    total = len(result.recalls) + len(result.complaints)
    if total > 0:
        logger.info(
            f"NHTSA: {len(result.recalls)} recalls, {len(result.complaints)} complaints for {year} {make} {model}"
        )

    return result


async def _fetch_recalls(client: httpx.AsyncClient, make: str, model: str, year: int | str) -> list[Recall]:
    """Fetch recalls from NHTSA."""
    params = {"make": make, "model": model, "modelYear": str(year)}
    response = await client.get(RECALLS_URL, params=params)

    if response.status_code != 200:
        logger.warning(f"NHTSA recalls HTTP {response.status_code}")
        return []

    data = response.json()
    results = data.get("results", [])

    recalls = []
    for item in results[:20]:  # Cap at 20
        recalls.append(
            Recall(
                campaign_number=item.get("NHTSACampaignNumber", ""),
                component=item.get("Component", ""),
                summary=item.get("Summary", ""),
                consequence=item.get("Consequence", ""),
                remedy=item.get("Remedy", ""),
                report_date=item.get("ReportReceivedDate"),
            )
        )

    return recalls


async def _fetch_complaints(client: httpx.AsyncClient, make: str, model: str, year: int | str) -> list[Complaint]:
    """Fetch consumer complaints from NHTSA."""
    params = {"make": make, "model": model, "modelYear": str(year)}
    response = await client.get(COMPLAINTS_URL, params=params)

    if response.status_code != 200:
        logger.warning(f"NHTSA complaints HTTP {response.status_code}")
        return []

    data = response.json()
    results = data.get("results", [])

    complaints = []
    for item in results[:20]:  # Cap at 20
        complaints.append(
            Complaint(
                odi_number=item.get("odiNumber", ""),
                component=item.get("components", ""),
                summary=item.get("summary", ""),
                crash=item.get("crash", "N") == "Y",
                fire=item.get("fire", "N") == "Y",
                date_of_incident=item.get("dateOfIncident"),
            )
        )

    return complaints


def filter_relevant(nhtsa: NHTSAResult, part_description: str | None) -> NHTSAResult:
    """Filter NHTSA results to those relevant to the part being searched."""
    if not part_description or not nhtsa:
        return nhtsa

    keywords = part_description.lower().split()

    filtered_recalls = [
        r for r in nhtsa.recalls if any(kw in r.component.lower() or kw in r.summary.lower() for kw in keywords)
    ]

    filtered_complaints = [
        c for c in nhtsa.complaints if any(kw in c.component.lower() or kw in c.summary.lower() for kw in keywords)
    ]

    return NHTSAResult(recalls=filtered_recalls, complaints=filtered_complaints)
