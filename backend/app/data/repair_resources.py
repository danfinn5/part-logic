"""
Repair resources database — curated links to authoritative repair information.

Indexed by make/category so the intelligence panel can surface relevant
resources for any vehicle: OEM parts catalogs, factory service manuals,
wiring diagrams, YouTube channels, forums, and cross-reference tools.
"""

REPAIR_RESOURCES: list[dict] = [
    # ── OEM Parts Catalogs ─────────────────────────────────────────────
    {
        "name": "RealOEM",
        "url": "https://www.realoem.com/bmw/enUS/partgrp",
        "category": "oem_catalog",
        "makes": ["BMW"],
        "description": "BMW exploded parts diagrams with OEM part numbers",
    },
    {
        "name": "7zap (Audi)",
        "url": "https://audi.7zap.com/en/",
        "category": "oem_catalog",
        "makes": ["Audi"],
        "description": "Audi ETKA parts catalog with diagrams",
    },
    {
        "name": "7zap (VW)",
        "url": "https://volkswagen.7zap.com/en/",
        "category": "oem_catalog",
        "makes": ["Volkswagen", "VW"],
        "description": "VW ETKA parts catalog with diagrams",
    },
    {
        "name": "PartsLink24",
        "url": "https://www.partslink24.com/",
        "category": "oem_catalog",
        "makes": ["Volkswagen", "VW", "Audi", "SEAT", "Skoda"],
        "description": "Official ETKA online catalog, free US registration",
    },
    {
        "name": "SuperETKA",
        "url": "https://superetka.com/",
        "category": "oem_catalog",
        "makes": ["Volkswagen", "VW", "Audi"],
        "description": "Enhanced ETKA with VIN decoding and TPI access",
    },
    {
        "name": "PartSouq",
        "url": "https://partsouq.com/en/catalog/genuine",
        "category": "oem_catalog",
        "makes": [],
        "description": "Multi-brand OEM catalogs: Toyota, Nissan, Honda, Subaru, Kia, Hyundai, Mitsubishi",
    },
    {
        "name": "Megazip",
        "url": "https://www.megazip.net/",
        "category": "oem_catalog",
        "makes": [],
        "description": "OEM parts catalogs for Japanese and Korean makes with diagrams",
    },
    {
        "name": "7zap (All Makes)",
        "url": "https://7zap.com/en/catalog/cars/",
        "category": "oem_catalog",
        "makes": [],
        "description": "60+ brand OEM parts catalogs with exploded diagrams",
    },
    # ── Factory Service Manuals (Free) ─────────────────────────────────
    {
        "name": "Operation CHARM",
        "url": "https://charm.li/",
        "category": "fsm",
        "makes": [],
        "description": "50,000+ models 1982-2013, free factory service manuals. Same data ALLDATA sells.",
    },
    {
        "name": "NICOclub (Nissan FSMs)",
        "url": "https://www.nicoclub.com/nissan-service-manuals",
        "category": "fsm",
        "makes": ["Nissan", "Infiniti", "Datsun"],
        "description": "Legitimately hosted Nissan factory service manuals through ~2016",
    },
    {
        "name": "Internet Archive Auto Manuals",
        "url": "https://archive.org/details/manuals_automotive",
        "category": "fsm",
        "makes": [],
        "description": "Scanned factory service manuals, Chilton manuals from 1960s-1990s, OCR searchable",
    },
    {
        "name": "AllCarManuals",
        "url": "https://allcarmanuals.com/",
        "category": "fsm",
        "makes": [],
        "description": "300+ models, free PDF factory service manuals",
    },
    {
        "name": "JustGiveMeTheDamnManual",
        "url": "https://www.justgivemethedamnmanual.com/",
        "category": "fsm",
        "makes": [],
        "description": "Multi-make PDF service repair manuals",
    },
    # ── OEM Service Portals (Paid) ─────────────────────────────────────
    {
        "name": "erWin (VW/Audi)",
        "url": "https://erwin.vw.com/",
        "category": "oem_service",
        "makes": ["Volkswagen", "VW", "Audi", "SEAT", "Skoda"],
        "description": "Official VW AG repair info portal, pay-per-document",
    },
    {
        "name": "Toyota TIS",
        "url": "https://techinfo.toyota.com/",
        "category": "oem_service",
        "makes": ["Toyota", "Lexus", "Scion"],
        "description": "Official Toyota technical information system",
    },
    {
        "name": "Honda ServiceExpress",
        "url": "https://techinfo.honda.com/",
        "category": "oem_service",
        "makes": ["Honda", "Acura"],
        "description": "Official Honda/Acura service info — same as dealers",
    },
    {
        "name": "Motorcraft Service (Ford)",
        "url": "https://www.motorcraftservice.com/",
        "category": "oem_service",
        "makes": ["Ford", "Lincoln", "Mercury"],
        "description": "Ford official service information",
    },
    {
        "name": "TechAuthority (Stellantis)",
        "url": "https://www.techauthority.com/",
        "category": "oem_service",
        "makes": ["Chrysler", "Dodge", "Jeep", "Ram", "Fiat"],
        "description": "Stellantis official technical portal",
    },
    {
        "name": "ACDelco TDS (GM)",
        "url": "https://www.acdelcotds.com/",
        "category": "oem_service",
        "makes": ["Chevrolet", "GMC", "Buick", "Cadillac", "Pontiac", "Oldsmobile", "Saturn"],
        "description": "GM official technical delivery system",
    },
    {
        "name": "BMW TechInfo",
        "url": "https://www.bmwtechinfo.com/",
        "category": "oem_service",
        "makes": ["BMW", "MINI"],
        "description": "BMW official service information",
    },
    {
        "name": "StartekInfo (Mercedes)",
        "url": "https://www.startekinfo.com/",
        "category": "oem_service",
        "makes": ["Mercedes-Benz", "Mercedes"],
        "description": "Mercedes-Benz official service information",
    },
    {
        "name": "Porsche TechInfo",
        "url": "https://techinfo2.porsche.com/",
        "category": "oem_service",
        "makes": ["Porsche"],
        "description": "Porsche official service information",
    },
    {
        "name": "Subaru TechInfo",
        "url": "https://techinfo.subaru.com/",
        "category": "oem_service",
        "makes": ["Subaru"],
        "description": "Subaru official service information",
    },
    # ── Wiring Diagrams ────────────────────────────────────────────────
    {
        "name": "AutoZone Wiring Diagrams",
        "url": "https://www.autozone.com/diy/repair-guides/wiring-diagrams",
        "category": "wiring",
        "makes": [],
        "description": "Free wiring diagrams from Chilton data, extensive domestic/Asian coverage",
    },
    {
        "name": "GM Upfitter Manuals",
        "url": "https://www.gmupfitter.com/",
        "category": "wiring",
        "makes": ["Chevrolet", "GMC", "GM"],
        "description": "Complete GM wiring diagrams with pin-outs for every connector. Free.",
    },
    # ── TSBs & Recalls ─────────────────────────────────────────────────
    {
        "name": "NHTSA Recalls & TSBs",
        "url": "https://www.nhtsa.gov/recalls",
        "category": "tsb_recall",
        "makes": [],
        "description": "Government recall database + manufacturer communications (TSBs)",
    },
    {
        "name": "GM TSB Lookup",
        "url": "https://www.gmtcentral.com/gm-vin-decoder-tsb-lookup",
        "category": "tsb_recall",
        "makes": ["Chevrolet", "GMC", "Buick", "Cadillac", "GM"],
        "description": "Free GM VIN decoder + TSB lookup with RPO code decoding",
    },
    # ── Cross-Reference Tools ──────────────────────────────────────────
    {
        "name": "Parts Cross-Reference",
        "url": "https://parts-crossreference.com/",
        "category": "cross_reference",
        "makes": [],
        "description": "Free OEM-to-aftermarket cross-reference search tool",
    },
    {
        "name": "AutoZonePro Interchange",
        "url": "https://www.autozonepro.com/interchangeSearch.jsp",
        "category": "cross_reference",
        "makes": [],
        "description": "Part number interchange search across manufacturers",
    },
    {
        "name": "Pull-A-Part Interchange",
        "url": "https://www.pullapart.com/inventory/interchangeable-parts/",
        "category": "cross_reference",
        "makes": [],
        "description": "Free Hollander-powered vehicle-to-vehicle part interchange",
    },
    # ── YouTube Channels ───────────────────────────────────────────────
    {
        "name": "1A Auto",
        "url": "https://www.youtube.com/@1AAuto",
        "category": "youtube",
        "makes": [],
        "description": "Thousands of model-specific repair videos with exact procedures",
    },
    {
        "name": "ChrisFix",
        "url": "https://www.youtube.com/@ChrisFix",
        "category": "youtube",
        "makes": [],
        "description": "High production quality, fundamentals and common repairs",
    },
    {
        "name": "South Main Auto Repair",
        "url": "https://www.youtube.com/@SouthMainAutoRepairAvoca",
        "category": "youtube",
        "makes": [],
        "description": "Real shop diagnostics, teaches diagnostic thinking",
    },
    {
        "name": "Scanner Danner",
        "url": "https://www.youtube.com/@ScannerDanner",
        "category": "youtube",
        "makes": [],
        "description": "Deep electrical/diagnostic education",
    },
    {
        "name": "FordTechMakuloco",
        "url": "https://www.youtube.com/@FordTechMakuloco",
        "category": "youtube",
        "makes": ["Ford"],
        "description": "Ford specialist, universal diagnostic principles",
    },
    {
        "name": "Humble Mechanic",
        "url": "https://www.youtube.com/@HumbleMechanic",
        "category": "youtube",
        "makes": ["Volkswagen", "VW", "Audi"],
        "description": "VW/Audi specialist, former dealer tech",
    },
    {
        "name": "50sKid",
        "url": "https://www.youtube.com/@50sKid",
        "category": "youtube",
        "makes": ["BMW"],
        "description": "BMW specialist, very detailed DIY content",
    },
    {
        "name": "FCP Euro",
        "url": "https://www.youtube.com/@FCPEuro",
        "category": "youtube",
        "makes": ["Volkswagen", "VW", "Audi", "BMW", "Volvo"],
        "description": "European car DIY repair content",
    },
    {
        "name": "Weber Auto",
        "url": "https://www.youtube.com/@WeberAuto",
        "category": "youtube",
        "makes": [],
        "description": "Professor John Kelly's automotive technology lectures — college-level free education",
    },
    # ── Forums ─────────────────────────────────────────────────────────
    {
        "name": "Bimmerforums",
        "url": "https://www.bimmerforums.com/",
        "category": "forum",
        "makes": ["BMW"],
        "description": "BMW enthusiast community — deep technical knowledge",
    },
    {
        "name": "E46Fanatics",
        "url": "https://www.e46fanatics.com/",
        "category": "forum",
        "makes": ["BMW"],
        "description": "BMW E46 generation specialist forum",
    },
    {
        "name": "VWVortex",
        "url": "https://www.vwvortex.com/",
        "category": "forum",
        "makes": ["Volkswagen", "VW", "Audi"],
        "description": "VW/Audi enthusiast community",
    },
    {
        "name": "Audizine",
        "url": "https://www.audizine.com/",
        "category": "forum",
        "makes": ["Audi"],
        "description": "Audi enthusiast community",
    },
    {
        "name": "Bob Is The Oil Guy",
        "url": "https://www.bobistheoilguy.com/",
        "category": "forum",
        "makes": [],
        "description": "Fluids, filtration, and maintenance deep-dives",
    },
    # ── Specialty Reference ────────────────────────────────────────────
    {
        "name": "aa1car.com",
        "url": "https://www.aa1car.com/",
        "category": "reference",
        "makes": [],
        "description": "250+ free diagnostic articles covering OBD-II codes and system troubleshooting",
    },
    {
        "name": "Chilton Library",
        "url": "https://www.chiltonlibrary.com/",
        "category": "reference",
        "makes": [],
        "description": "Full Chilton database — free with many US library cards. 1940 to current.",
    },
    {
        "name": "NASTF OEM Portal Directory",
        "url": "https://www.nastf.org/",
        "category": "reference",
        "makes": [],
        "description": "Master list of every OEM service information website with pricing",
    },
]


def get_resources_for_make(make: str | None) -> list[dict]:
    """Get repair resources relevant to a specific make, plus universal resources."""
    if not make:
        return [r for r in REPAIR_RESOURCES if not r["makes"]]

    make_lower = make.lower().strip()
    results = []
    for r in REPAIR_RESOURCES:
        if not r["makes"]:
            results.append(r)
        elif any(m.lower() == make_lower for m in r["makes"]):
            results.append(r)
    return results


def get_resources_by_category(category: str) -> list[dict]:
    """Get all resources in a category."""
    return [r for r in REPAIR_RESOURCES if r["category"] == category]
