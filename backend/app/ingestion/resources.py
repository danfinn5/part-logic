"""
Smart external link generator connector.

Uses the source registry to generate contextual search links
based on query analysis: detected vehicle make, part type, and
whether the query is a part number or description.

Generates links from 80+ registered sources, filtered by relevance
to the query context. This is the primary "breadth" mechanism —
even when scrapers fail, users get direct links to search every
relevant source.
"""

import logging
from typing import Any
from urllib.parse import quote, quote_plus

from app.data.source_registry import get_active_sources
from app.ingestion.base import BaseConnector
from app.schemas.search import ExternalLink

logger = logging.getLogger(__name__)


# --- Verified search URL templates ---
# Each returns a working search URL for the given query string.
# Organized by domain. Only domains with verified URL patterns are included;
# others fall back to a generic /search?q= pattern.


def _search_url(domain: str, query: str) -> str | None:
    """Generate a search URL for a known domain. Returns None for unknown domains."""
    q = quote_plus(query)
    qr = quote(query)  # raw URL encoding (no + for spaces)

    TEMPLATES = {
        # ── Major Retailers ──────────────────────────────────
        "rockauto.com": f"https://www.rockauto.com/en/partsearch/?partnum={q}",
        "autozone.com": f"https://www.autozone.com/searchresult?searchText={q}",
        "oreillyauto.com": f"https://www.oreillyauto.com/shop/b/search?q={q}",
        "advanceautoparts.com": f"https://shop.advanceautoparts.com/find/{q}.html",
        "napaonline.com": f"https://www.napaonline.com/en/search?q={q}",
        "carparts.com": f"https://www.carparts.com/search?q={q}",
        "1aauto.com": f"https://www.1aauto.com/search?q={q}",
        "partsgeek.com": f"https://www.partsgeek.com/search.html?query={q}",
        "autopartswarehouse.com": f"https://www.autopartswarehouse.com/search/?Ntt={q}",
        # ── Performance ──────────────────────────────────────
        "summitracing.com": f"https://www.summitracing.com/search?SortBy=Default&SortOrder=Default&keyword={q}",
        "jegs.com": f"https://www.jegs.com/webapp/wcs/stores/servlet/SearchView?storeId=10001&searchTerm={q}",
        "speedwaymotors.com": f"https://www.speedwaymotors.com/search?query={q}",
        # ── Tires & Wheels ───────────────────────────────────
        "tirerack.com": "https://www.tirerack.com/content/tirerack/desktop/en/homepage.html",
        "discounttire.com": f"https://www.discounttire.com/search/{qr}",
        "simpletire.com": f"https://simpletire.com/search#{q}",
        # ── Accessories ──────────────────────────────────────
        "carid.com": f"https://www.carid.com/search.html?search={q}",
        "autoanything.com": f"https://www.autoanything.com/search?q={q}",
        # ── Marketplaces ─────────────────────────────────────
        "amazon.com": f"https://www.amazon.com/s?k={q}&i=automotive",
        "ebay.com": f"https://www.ebay.com/sch/i.html?_nkw={q}&_sacat=6028",
        "facebook.com/marketplace": f"https://www.facebook.com/marketplace/search/?query={q}&category=vehicles",
        "craigslist.org": f"https://www.craigslist.org/search/pta?query={q}",
        # ── Used / Salvage ───────────────────────────────────
        "car-part.com": "https://www.car-part.com",
        "lkqonline.com": f"https://www.lkqonline.com/search?q={q}",
        "row52.com": f"https://row52.com/Search/?YMMorVin=&Keyword={q}",
        "pullapart.com": f"https://www.pullapart.com/vehicle-search/?q={q}",
        "picknpull.com": "https://www.picknpull.com/check-inventory",
        "upullandpay.com": "https://upullandpay.com/inventory-search/",
        # ── OEM Dealer Parts Stores ──────────────────────────
        "tascaparts.com": f"https://www.tascaparts.com/search?search_str={q}",
        "gmpartsdirect.com": f"https://www.gmpartsdirect.com/oem-parts?filter_keyword={q}",
        "moparpartsgiant.com": f"https://www.moparpartsgiant.com/parts-list.html?search={q}",
        "fordpartsgiant.com": f"https://www.fordpartsgiant.com/parts-list.html?search={q}",
        "hondapartsnow.com": f"https://www.hondapartsnow.com/parts-list.html?search={q}",
        "toyotapartsdeal.com": f"https://www.toyotapartsdeal.com/parts-list.html?search={q}",
        "lexuspartsnow.com": f"https://www.lexuspartsnow.com/parts-list.html?search={q}",
        "nissanpartsdeal.com": f"https://www.nissanpartsdeal.com/parts-list.html?search={q}",
        "subarupartsdeal.com": f"https://www.subarupartsdeal.com/parts-list.html?search={q}",
        # ── Euro Specialists ─────────────────────────────────
        "fcpeuro.com": f"https://www.fcpeuro.com/products?keywords={q}",
        "ecstuning.com": f"https://www.ecstuning.com/Search/{q}/",
        "turnermotorsport.com": f"https://www.turnermotorsport.com/Search?q={q}",
        "pelicanparts.com": f"https://www.pelicanparts.com/catalog/search.php?searchString={q}",
        "autohauzaz.com": f"https://www.autohauzaz.com/catalogsearch/result/?q={q}",
        "eeuroparts.com": f"https://www.eeuroparts.com/Search/?q={q}",
        "bimmerworld.com": f"https://www.bimmerworld.com/search?q={q}",
        "ipdusa.com": f"https://www.ipdusa.com/search?type=product&q={q}",
        "swedishcarparts.com": f"https://www.swedishcarparts.com/search?q={q}",
        # ── Porsche Specialists ──────────────────────────────
        "suncoastparts.com": f"https://www.suncoastparts.com/SearchResults.asp?Search={q}",
        "stoddard.com": f"https://www.stoddard.com/catalogsearch/result/?q={q}",
        "sierramadrecollection.com": f"https://www.sierramadrecollection.com/search?q={q}",
        "design911.com": f"https://www.design911.co.uk/search/{q}",
        "rosepassion.com": f"https://www.rosepassion.com/en/search?s={q}",
        # ── Restoration ──────────────────────────────────────
        "yearone.com": f"https://www.yearone.com/Catalog?SearchText={q}",
        "classicindustries.com": f"https://www.classicindustries.com/search/?q={q}",
        "nationalpartsdepot.com": f"https://www.nationalpartsdepot.com/nsearch?q={q}",
        "kanter.com": f"https://www.kanter.com/product-search?search={q}",
        "steelerubber.com": f"https://www.steelerubber.com/search?q={q}",
        "eastwood.com": f"https://www.eastwood.com/search?w={q}",
        # ── Industrial Crossover ─────────────────────────────
        "mcmaster.com": f"https://www.mcmaster.com/{qr}",
        "grainger.com": f"https://www.grainger.com/search?searchQuery={q}",
        "fastenal.com": f"https://www.fastenal.com/product?query={q}",
        "zoro.com": f"https://www.zoro.com/search?q={q}",
        # ── Automotive Electrical ────────────────────────────
        "waytekwire.com": f"https://www.waytekwire.com/search/?q={q}",
        "delcity.net": f"https://www.delcity.net/search?q={q}",
        # ── Electronics (Crossover) ──────────────────────────
        "digikey.com": f"https://www.digikey.com/en/products/result?keywords={q}",
        "mouser.com": f"https://www.mouser.com/c/?q={q}",
        # ── Reference / EPC ──────────────────────────────────
        "realoem.com": f"https://www.realoem.com/bmw/enUS/partgrp?q={q}",
        "partsouq.com": f"https://partsouq.com/en/search/all?q={q}",
        "amayama.com": f"https://www.amayama.com/en/search?q={q}",
        "megazip.net": f"https://megazip.net/search?q={q}",
        "toyota.epc-data.com": f"https://toyota.epc-data.com/search/?q={q}",
        # ── Official OEM Catalogs ────────────────────────────
        "parts.ford.com": f"https://parts.ford.com/shop/SearchDisplay?searchTerm={q}",
        "parts.toyota.com": f"https://parts.toyota.com/search?searchTerm={q}",
        "parts.lexus.com": f"https://parts.lexus.com/search?searchTerm={q}",
        "parts.honda.com": f"https://parts.honda.com/search?searchTerm={q}",
        "parts.acura.com": f"https://parts.acura.com/search?searchTerm={q}",
        "parts.nissanusa.com": f"https://parts.nissanusa.com/search?searchTerm={q}",
        "parts.subaru.com": f"https://parts.subaru.com/search?searchTerm={q}",
        "parts.gm.com": f"https://parts.gm.com/content/gmparts/search.html?q={q}",
        "parts.mopar.com": f"https://www.mopar.com/en-us/parts/search.html?q={q}",
        "parts.mbusa.com": f"https://parts.mbusa.com/search?q={q}",
        # ── Repair Resources ─────────────────────────────────
        "youtube.com": f"https://www.youtube.com/results?search_query={quote_plus(query + ' replacement')}",
    }

    return TEMPLATES.get(domain)


# --- Vehicle make to registry tag mapping ---

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
    "FIAT": ["euro"],
    "ALFA ROMEO": ["euro"],
    "FORD": ["ford"],
    "LINCOLN": ["ford"],
    "CHEVROLET": ["gm"],
    "CHEVY": ["gm"],
    "GMC": ["gm"],
    "BUICK": ["gm"],
    "CADILLAC": ["gm"],
    "PONTIAC": ["gm"],
    "SATURN": ["gm"],
    "DODGE": ["mopar"],
    "CHRYSLER": ["mopar"],
    "JEEP": ["mopar"],
    "RAM": ["mopar"],
    "HONDA": ["honda"],
    "ACURA": ["acura", "honda"],
    "TOYOTA": ["toyota"],
    "LEXUS": ["lexus", "toyota"],
    "SCION": ["toyota"],
    "NISSAN": ["nissan"],
    "INFINITI": ["nissan"],
    "SUBARU": ["subaru"],
    "MAZDA": [],
    "MITSUBISHI": [],
    "HYUNDAI": [],
    "KIA": [],
}

# Source category -> external link category
_LINK_CATEGORY_MAP = {
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

# Keywords that trigger inclusion of industrial/specialty sources
_INDUSTRIAL_KEYWORDS = frozenset(
    {
        "bolt",
        "nut",
        "screw",
        "bearing",
        "seal",
        "gasket",
        "bushing",
        "connector",
        "wire",
        "harness",
        "terminal",
        "relay",
        "fuse",
        "o-ring",
        "washer",
        "clip",
        "fastener",
        "hose",
        "clamp",
    }
)

_TIRE_KEYWORDS = frozenset({"tire", "tyre", "wheel", "rim", "hubcap"})

_RESTORATION_KEYWORDS = frozenset(
    {
        "classic",
        "vintage",
        "restore",
        "restoration",
        "muscle",
        "antique",
        "hot rod",
        "hotrod",
    }
)


class ResourcesConnector(BaseConnector):
    """
    Smart link generator using the source registry.

    Generates contextual search links based on query analysis:
    - Always includes major retailers and marketplaces
    - Adds OEM dealer links when vehicle make is detected
    - Adds specialist links (euro, porsche, etc.) when relevant
    - Adds EPC/reference links for part number queries
    - Adds repair resource links
    - Filters out irrelevant sources (no euro specialists for a Honda query)
    - Prioritizes by registry priority
    """

    def __init__(self):
        super().__init__("resources")

    async def search(self, query: str, **kwargs) -> dict[str, Any]:
        """Generate contextual external links from the source registry."""
        links: list[ExternalLink] = []
        part_numbers = kwargs.get("part_numbers", [])
        query_lower = query.lower()

        # Detect vehicle make for specialist source filtering
        detected_make = self._detect_make(query)
        relevant_tags = set()
        if detected_make:
            relevant_tags.update(_MAKE_TO_TAGS.get(detected_make.upper(), []))

        # Check for keyword triggers
        has_industrial = any(kw in query_lower for kw in _INDUSTRIAL_KEYWORDS)
        has_tire = any(kw in query_lower for kw in _TIRE_KEYWORDS)
        has_restoration = any(kw in query_lower for kw in _RESTORATION_KEYWORDS)

        # Get all active sources sorted by priority
        buyable_sources = get_active_sources(source_type="buyable")
        reference_sources = get_active_sources(source_type="reference")

        seen_domains = set()

        # --- Buyable sources ---
        for source in buyable_sources:
            domain = source["domain"]
            if domain in seen_domains:
                continue

            category = source.get("category", "")
            tags = set(source.get("tags", []))

            if not self._should_include_buyable(
                category, tags, relevant_tags, has_industrial, has_tire, has_restoration
            ):
                continue

            url = _search_url(domain, query)
            if not url:
                url = f"https://{domain}"

            link_category = _LINK_CATEGORY_MAP.get(category, "new_parts")
            links.append(
                ExternalLink(
                    label=f"{source['name']}: '{query}'",
                    url=url,
                    source=domain.replace(".", "_"),
                    category=link_category,
                )
            )
            seen_domains.add(domain)

        # --- Reference sources ---
        for source in reference_sources:
            domain = source["domain"]
            if domain in seen_domains:
                continue

            tags = set(source.get("tags", []))

            # Only include make-specific OEM catalogs if make detected
            if "official" in tags:
                if not relevant_tags or not tags.intersection(relevant_tags):
                    continue

            url = _search_url(domain, query)
            if not url:
                url = f"https://{domain}"

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
        encoded = quote_plus(query)
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

        # --- Per-part-number links for key reference sources ---
        if part_numbers:
            pn_domains = ["rockauto.com", "partsouq.com"]
            if detected_make and detected_make.upper() == "BMW":
                pn_domains.append("realoem.com")

            for pn in part_numbers[:3]:
                for domain in pn_domains:
                    url = _search_url(domain, pn)
                    if url:
                        src_name = domain
                        for s in buyable_sources + reference_sources:
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

        logger.info(f"Generated {len(links)} external links ({len(seen_domains)} sources)")

        return {
            "market_listings": [],
            "salvage_hits": [],
            "external_links": links,
            "error": None,
        }

    def _should_include_buyable(
        self,
        category: str,
        tags: set,
        relevant_tags: set,
        has_industrial: bool,
        has_tire: bool,
        has_restoration: bool,
    ) -> bool:
        """Decide whether to include a buyable source based on context."""
        # Always include general retailers and marketplaces
        if category in ("retailer", "marketplace"):
            # But filter out niche retailers that don't match context
            if tags.intersection({"euro", "porsche", "bmw", "volvo", "audi"}):
                # Euro specialist — only if euro make detected
                if not relevant_tags or not tags.intersection(relevant_tags | {"euro"}):
                    return False
            if tags.intersection({"tires_wheels"}) and not has_tire:
                return False
            if tags.intersection({"restoration", "classic_restoration", "classic_hotrod", "muscle"}):
                if not has_restoration:
                    return False
            return True

        # Always include used/salvage
        if category in ("used_aggregator", "salvage_yard"):
            return True

        # OEM dealers: only if vehicle make matches
        if category == "oe_dealer":
            if not relevant_tags:
                return False
            # Check if any tag overlaps (e.g., "ford_oem_dealer" contains "ford")
            for rt in relevant_tags:
                if any(rt in t for t in tags):
                    return True
            # Also match generic "new_oem" tag with any relevant tag
            if "new_oem" in tags and relevant_tags:
                return True
            return False

        # Industrial/electronics: only if industrial keywords present
        if category in ("industrial", "electronics"):
            return has_industrial

        return True

    def _detect_make(self, query: str) -> str | None:
        """Detect vehicle make from query string."""
        upper = query.upper()
        # Check longest names first to avoid partial matches (e.g., "MINI" before "MI")
        for make in sorted(_MAKE_TO_TAGS.keys(), key=len, reverse=True):
            if make in upper:
                return make
        return None
