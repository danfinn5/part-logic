"""
Smart external link generator connector.

Uses the source registry to generate contextual search links
based on query analysis: detected vehicle make, part type, and
whether the query is a part number or description.

This replaces the old hardcoded YouTube+Charm.li links with
a comprehensive link set drawn from 80+ registered sources.
"""

import logging
from typing import Any
from urllib.parse import quote_plus

from app.data.source_registry import get_active_sources
from app.ingestion.base import BaseConnector
from app.schemas.search import ExternalLink

logger = logging.getLogger(__name__)


# --- URL template builders by domain pattern ---


def _search_url(domain: str, query: str) -> str | None:
    """
    Generate a plausible search URL for a given domain and query.
    Returns None if we don't have a pattern for this domain.
    """
    q = quote_plus(query)
    templates = {
        # Major retailers
        "rockauto.com": f"https://www.rockauto.com/en/catalog/?a=search&s={q}",
        "autozone.com": f"https://www.autozone.com/searchresult?searchText={q}",
        "oreillyauto.com": f"https://www.oreillyauto.com/shop/b/search?q={q}",
        "advanceautoparts.com": f"https://shop.advanceautoparts.com/web/PartSearchCmd?storeId=10151&searchTerm={q}",
        "napaonline.com": f"https://www.napaonline.com/en/search?q={q}",
        "carparts.com": f"https://www.carparts.com/search?q={q}",
        "1aauto.com": f"https://www.1aauto.com/search?q={q}",
        "partsgeek.com": f"https://www.partsgeek.com/find/{q}.html",
        "autopartswarehouse.com": f"https://www.autopartswarehouse.com/search/?Ntt={q}",
        "jcwhitney.com": f"https://www.jcwhitney.com/search?q={q}",
        # Performance
        "summitracing.com": f"https://www.summitracing.com/search?SortBy=Default&SortOrder=Default&keyword={q}",
        "jegs.com": f"https://www.jegs.com/webapp/wcs/stores/servlet/SearchView?storeId=10001&searchTerm={q}",
        "speedwaymotors.com": f"https://www.speedwaymotors.com/search?query={q}",
        # Tires/Wheels
        "tirerack.com": "https://www.tirerack.com/tires/TireSearchResults.jsp?width=&ratio=&diameter=&rearWidth=&rearRatio=&rearDiameter=&sortCode=58060&autoMake=&autoYear=&autoModel=&autoModClar=",
        "discounttire.com": f"https://www.discounttire.com/search/{q}",
        # Accessories
        "carid.com": f"https://www.carid.com/search.html?search={q}",
        "autoanything.com": f"https://www.autoanything.com/search?q={q}",
        # Marketplaces
        "amazon.com": f"https://www.amazon.com/s?k={q}&i=automotive",
        "ebay.com": f"https://www.ebay.com/sch/i.html?_nkw={q}&_sacat=6028",
        "facebook.com/marketplace": f"https://www.facebook.com/marketplace/search/?query={q}",
        "craigslist.org": f"https://www.craigslist.org/search/pta?query={q}",
        # Used/Salvage
        "car-part.com": f"https://www.car-part.com/cgi-bin/search.cgi?userSearch={q}",
        "lkqonline.com": f"https://www.lkqonline.com/search?q={q}",
        "row52.com": f"https://row52.com/Search/?YMMorVin=&Keyword={q}",
        "pullapart.com": f"https://www.pullapart.com/vehicle-search/?q={q}",
        "picknpull.com": f"https://www.picknpull.com/check-inventory?q={q}",
        # OEM Dealers
        "tascaparts.com": f"https://www.tascaparts.com/search?search_str={q}",
        "gmpartsdirect.com": f"https://www.gmpartsdirect.com/oem-parts?filter_keyword={q}",
        "moparpartsgiant.com": f"https://www.moparpartsgiant.com/parts-list.html?search={q}",
        "fordpartsgiant.com": f"https://www.fordpartsgiant.com/parts-list.html?search={q}",
        "hondapartsnow.com": f"https://www.hondapartsnow.com/parts-list.html?search={q}",
        "toyotapartsdeal.com": f"https://www.toyotapartsdeal.com/parts-list.html?search={q}",
        "lexuspartsnow.com": f"https://www.lexuspartsnow.com/parts-list.html?search={q}",
        "nissanpartsdeal.com": f"https://www.nissanpartsdeal.com/parts-list.html?search={q}",
        "subarupartsdeal.com": f"https://www.subarupartsdeal.com/parts-list.html?search={q}",
        # Euro Specialist
        "fcpeuro.com": f"https://www.fcpeuro.com/search?query={q}",
        "ecstuning.com": f"https://www.ecstuning.com/Search/{q}/",
        "turnermotorsport.com": f"https://www.turnermotorsport.com/Search?q={q}",
        "pelicanparts.com": f"https://www.pelicanparts.com/catalog/search.php?q={q}",
        "autohauzaz.com": f"https://www.autohauzaz.com/search?q={q}",
        "eeuroparts.com": f"https://www.eeuroparts.com/Search/?q={q}",
        "bimmerworld.com": f"https://www.bimmerworld.com/search?q={q}",
        # Porsche Specialist
        "suncoastparts.com": f"https://www.suncoastparts.com/search?q={q}",
        "stoddard.com": f"https://www.stoddard.com/search?q={q}",
        # Reference/EPC
        "realoem.com": f"https://www.realoem.com/bmw/enUS/partgrp?q={q}",
        "partsouq.com": f"https://partsouq.com/en/search/all?q={q}",
        "amayama.com": f"https://www.amayama.com/en/search?q={q}",
        "megazip.net": f"https://megazip.net/search?q={q}",
        # Official OEM catalogs
        "parts.ford.com": f"https://parts.ford.com/shop/SearchDisplay?searchTerm={q}",
        "parts.toyota.com": f"https://parts.toyota.com/search?q={q}",
        "parts.honda.com": f"https://parts.honda.com/search?q={q}",
        "parts.gm.com": f"https://parts.gm.com/accessories/search?q={q}",
        # Industrial crossover
        "mcmaster.com": f"https://www.mcmaster.com/{q}",
        "grainger.com": f"https://www.grainger.com/search?searchQuery={q}",
        "fastenal.com": f"https://www.fastenal.com/product?query={q}",
        # Automotive electrical
        "waytekwire.com": f"https://www.waytekwire.com/search?q={q}",
        # Restoration
        "yearone.com": f"https://www.yearone.com/Catalog?SearchText={q}",
        "classicindustries.com": f"https://www.classicindustries.com/search/?q={q}",
        "nationalpartsdepot.com": f"https://www.nationalpartsdepot.com/search?q={q}",
        # Repair resources
        "youtube.com": f"https://www.youtube.com/results?search_query={quote_plus(query + ' replacement')}",
    }
    return templates.get(domain)


# --- Make-to-tag mapping for OEM/specialist filtering ---

_MAKE_TO_TAGS = {
    "BMW": ["bmw", "euro"],
    "AUDI": ["audi", "euro"],
    "VOLKSWAGEN": ["euro"],
    "VW": ["euro"],
    "PORSCHE": ["porsche", "euro"],
    "MERCEDES": ["mercedes", "euro"],
    "MERCEDES-BENZ": ["mercedes", "euro"],
    "VOLVO": ["volvo", "euro"],
    "SAAB": ["euro"],
    "MINI": ["bmw", "euro"],
    "FORD": ["ford"],
    "LINCOLN": ["ford"],
    "CHEVROLET": ["gm"],
    "CHEVY": ["gm"],
    "GMC": ["gm"],
    "BUICK": ["gm"],
    "CADILLAC": ["gm"],
    "DODGE": ["mopar"],
    "CHRYSLER": ["mopar"],
    "JEEP": ["mopar"],
    "RAM": ["mopar"],
    "HONDA": ["honda"],
    "ACURA": ["acura", "honda"],
    "TOYOTA": ["toyota"],
    "LEXUS": ["lexus", "toyota"],
    "NISSAN": ["nissan"],
    "INFINITI": ["nissan"],
    "SUBARU": ["subaru"],
}

# Categories that should always be included for buyable queries
_ALWAYS_CATEGORIES = {"retailer", "marketplace"}
# Categories for used/salvage
_USED_CATEGORIES = {"used_aggregator", "salvage_yard"}
# Categories for reference
_REFERENCE_CATEGORIES = {"epc", "epc_retail", "oem_catalog", "interchange"}

# Link category mapping from source categories
_SOURCE_CATEGORY_TO_LINK_CATEGORY = {
    "retailer": "new_parts",
    "marketplace": "marketplace",
    "used_aggregator": "used_parts",
    "salvage_yard": "used_parts",
    "oe_dealer": "oem_parts",
    "industrial": "industrial",
    "electronics": "industrial",
    "interchange": "reference",
    "epc": "reference",
    "epc_retail": "reference",
    "oem_catalog": "oem_parts",
}


class ResourcesConnector(BaseConnector):
    """
    Smart link generator using the source registry.

    Generates contextual search links based on query analysis:
    - Always includes major retailers and marketplaces
    - Adds OEM dealer links when vehicle make is detected
    - Adds specialist links (euro, porsche, etc.) when relevant
    - Adds EPC/reference links for part number queries
    - Adds repair resource links for descriptive queries
    - Prioritizes sources by registry priority
    """

    def __init__(self):
        super().__init__("resources")

    async def search(self, query: str, **kwargs) -> dict[str, Any]:
        """Generate contextual external links from the source registry."""
        encoded = quote_plus(query)
        links: list[ExternalLink] = []
        part_numbers = kwargs.get("part_numbers", [])

        # Detect vehicle make from query for specialist filtering
        detected_make = self._detect_make(query)
        relevant_tags = set()
        if detected_make:
            relevant_tags.update(_MAKE_TO_TAGS.get(detected_make.upper(), []))

        # Get all active sources, sorted by priority
        buyable_sources = get_active_sources(source_type="buyable")
        reference_sources = get_active_sources(source_type="reference")

        # --- Buyable sources ---
        seen_domains = set()
        for source in buyable_sources:
            domain = source["domain"]
            if domain in seen_domains:
                continue

            category = source.get("category", "")
            tags = set(source.get("tags", []))

            # Always include major categories
            if category in _ALWAYS_CATEGORIES:
                pass  # include
            elif category == "oe_dealer":
                # Only include OEM dealers relevant to detected make
                if not relevant_tags or not tags.intersection(relevant_tags):
                    # Also include if it has the specific make tag
                    make_specific_tags = {t for t in tags if t.endswith("_oem_dealer")}
                    if not make_specific_tags or not any(rt in t for t in make_specific_tags for rt in relevant_tags):
                        continue
            elif category in _USED_CATEGORIES:
                pass  # always include used sources
            elif category in ("industrial", "electronics"):
                # Only include for specific part types (fasteners, bearings, connectors)
                industrial_keywords = {"bolt", "nut", "bearing", "seal", "connector", "wire", "gasket", "bushing"}
                if not any(kw in query.lower() for kw in industrial_keywords):
                    continue
            elif tags.intersection(relevant_tags):
                pass  # specialist match
            elif "euro" in tags and not relevant_tags:
                continue  # euro specialist but no euro make detected
            elif "porsche" in tags and "porsche" not in relevant_tags:
                continue
            elif "bmw" in tags and "bmw" not in relevant_tags:
                continue
            elif "volvo" in tags and "volvo" not in relevant_tags:
                continue
            elif any(t in tags for t in ("restoration", "classic_restoration", "classic_hotrod")):
                # Include restoration sources only for older vehicles or explicit keywords
                restoration_keywords = {"classic", "vintage", "restore", "restoration", "muscle"}
                if not any(kw in query.lower() for kw in restoration_keywords):
                    continue
            elif any(t in tags for t in ("tires_wheels",)):
                tire_keywords = {"tire", "wheel", "rim"}
                if not any(kw in query.lower() for kw in tire_keywords):
                    continue
            elif any(t in tags for t in ("accessories", "body", "lighting")):
                # accessories — always include
                pass
            else:
                # Generic retailer with new_aftermarket tag — include
                if "new_aftermarket" not in tags and category != "retailer":
                    continue

            url = _search_url(domain, query)
            if not url:
                # Fallback: generic search URL
                url = f"https://{domain}/search?q={encoded}"

            link_category = _SOURCE_CATEGORY_TO_LINK_CATEGORY.get(category, "new_parts")
            links.append(
                ExternalLink(
                    label=f"{source['name']}: '{query}'",
                    url=url,
                    source=domain.replace(".", "_"),
                    category=link_category,
                )
            )
            seen_domains.add(domain)

        # --- Reference sources (EPC, OEM catalogs, interchange) ---
        for source in reference_sources:
            domain = source["domain"]
            if domain in seen_domains:
                continue

            tags = set(source.get("tags", []))

            # Only include make-specific references if make detected
            if "official" in tags:
                if not relevant_tags or not tags.intersection(relevant_tags):
                    continue

            url = _search_url(domain, query)
            if not url:
                url = f"https://{domain}/search?q={encoded}"

            links.append(
                ExternalLink(
                    label=f"{source['name']}: '{query}'",
                    url=url,
                    source=domain.replace(".", "_"),
                    category="reference",
                )
            )
            seen_domains.add(domain)

        # --- Always include repair resources ---
        links.append(
            ExternalLink(
                label=f"YouTube: '{query} replacement'",
                url=f"https://www.youtube.com/results?search_query={quote_plus(query + ' replacement')}",
                source="youtube",
                category="repair_resources",
            )
        )
        links.append(
            ExternalLink(
                label=f"Charm.li: '{query}'",
                url=f"https://charm.li/?q={encoded}",
                source="charmli",
                category="repair_resources",
            )
        )

        # --- Per-part-number links for key sources (if part numbers extracted) ---
        if part_numbers:
            pn_domains = ["rockauto.com", "car-part.com", "partsouq.com"]
            if detected_make:
                if detected_make.upper() == "BMW":
                    pn_domains.append("realoem.com")
            for pn in part_numbers[:3]:  # Limit to top 3 PNs
                for domain in pn_domains:
                    if domain not in seen_domains or True:  # allow PN-specific links
                        url = _search_url(domain, pn)
                        if url:
                            source = get_active_sources()
                            src_name = domain
                            for s in get_active_sources():
                                if s["domain"] == domain:
                                    src_name = s["name"]
                                    break
                            links.append(
                                ExternalLink(
                                    label=f"{src_name}: {pn}",
                                    url=url,
                                    source=domain.replace(".", "_"),
                                    category="reference",
                                )
                            )

        logger.info(f"Generated {len(links)} external links ({len(seen_domains)} unique sources)")

        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": links,
            "error": None,
        }

    def _detect_make(self, query: str) -> str | None:
        """Detect vehicle make from query string."""
        upper = query.upper()
        for make in sorted(_MAKE_TO_TAGS.keys(), key=len, reverse=True):
            if make in upper:
                return make
        return None
