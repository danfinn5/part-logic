"""
AI-powered parts advisor — supports OpenAI and Anthropic.

Takes a search query and returns structured product recommendations:
- Vehicle identification
- OEM part numbers
- Recommended brands ranked by quality/value
- Buy links generated with correct part numbers
- Consumable/salvage-appropriate classification

Provider priority: OpenAI (cheaper) > Anthropic > disabled.
Configure via OPENAI_API_KEY or ANTHROPIC_API_KEY in .env.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from urllib.parse import quote_plus

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert automotive parts advisor with deep knowledge of:
- OEM part numbers and their cross-references across brands
- Which companies manufacture parts for which automakers (e.g., Mann-Filter makes BMW oil filters)
- Aftermarket brand quality tiers (OEM, premium aftermarket, economy, budget)
- Enthusiast community consensus on best brands for specific applications
- Interchange part numbers across different manufacturers

When given a parts search query, analyze it and return a JSON object with this EXACT structure:

{
  "vehicle": {
    "make": "BMW",
    "model": "3 Series",
    "generation": "E46",
    "years": "1998-2006",
    "engine_codes": ["M54B30", "M54B25", "M52TUB28", "M52TUB25"]
  },
  "part": {
    "type": "Oil Filter",
    "is_consumable": true,
    "is_wear_item": true,
    "oem_part_numbers": ["11427512300", "11421432097"],
    "category": "filtration"
  },
  "recommendations": [
    {
      "rank": 1,
      "grade": "best_overall",
      "brand": "Mann-Filter",
      "part_number": "HU925/4x",
      "title": "Mann-Filter HU925/4x Oil Filter",
      "why": "OEM manufacturer for BMW. Identical to the dealer filter at 60% of the price. Universally recommended on Bimmerforums, E46Fanatics, and r/BMW.",
      "quality_tier": "oem",
      "quality_score": 10,
      "estimated_price_low": 8.00,
      "estimated_price_high": 13.00,
      "best_retailers": ["FCP Euro", "RockAuto", "Amazon", "ECS Tuning"]
    },
    {
      "rank": 2,
      "grade": "also_great",
      "brand": "Mahle",
      "part_number": "OX 154/1D",
      "title": "Mahle OX 154/1D Oil Filter",
      "why": "Major OE supplier to BMW. Excellent filtration, slightly different construction than Mann but equally effective.",
      "quality_tier": "premium_aftermarket",
      "quality_score": 9,
      "estimated_price_low": 7.00,
      "estimated_price_high": 11.00,
      "best_retailers": ["FCP Euro", "RockAuto", "Amazon"]
    }
  ],
  "avoid": [
    {
      "brand": "Fram",
      "reason": "Low-quality filter media. Known for cardboard endcaps that can deteriorate. Widely criticized in BMW community."
    }
  ],
  "notes": "Mann and Mahle are considered superior: both are OEM suppliers to BMW with identical quality to dealer parts. Avoid Fram and store brands (poor media, cardboard endcaps). BMW E46 uses a cartridge-style oil filter (not spin-on). Change every 7,500 miles with 7 quarts of 5W-30 synthetic; always replace the O-ring on the filter housing cap.",
  "relevant_makes": ["BMW"]
}

Rules:
1. Always include at least 3-5 recommendations spanning different quality tiers and price points.
2. Include specific part numbers that can be searched on retailer sites.
3. The "grade" field must be one of: "best_overall", "also_great", "budget_pick", "performance", "value_pick"
4. Include the "avoid" array with brands/products that have known quality issues for this application.
5. The "notes" field MUST be a short summary (2–4 sentences) that includes: (a) which brands are considered superior for this part and why (OEM vs aftermarket, enthusiast consensus), (b) practical maintenance or installation tips, (c) part-specific guidance where relevant (e.g. for oil filters: recommended oil type and change interval; for sensors: calibration or failure modes).
6. "relevant_makes" should list which car makes these parts are for (used to filter search results).
7. estimated_price_low and estimated_price_high should be realistic USD prices.
8. "best_retailers" should list 2-4 specific stores known to carry this brand/part.
9. "is_consumable" means it wears out and needs periodic replacement (filters, pads, spark plugs, fluids, wipers).
10. If the query is vague, still provide your best analysis based on the most likely interpretation.
11. ALWAYS return valid JSON. No markdown, no explanation outside the JSON."""


@dataclass
class PartRecommendation:
    rank: int
    grade: str
    brand: str
    part_number: str
    title: str
    why: str
    quality_tier: str
    quality_score: float
    estimated_price_low: float
    estimated_price_high: float
    best_retailers: list[str] = field(default_factory=list)
    buy_links: list[dict] = field(default_factory=list)


@dataclass
class AvoidItem:
    brand: str
    reason: str


@dataclass
class AIAdvisorResult:
    """Structured result from the AI advisor."""

    vehicle_make: str | None = None
    vehicle_model: str | None = None
    vehicle_generation: str | None = None
    vehicle_years: str | None = None
    part_type: str | None = None
    is_consumable: bool = False
    is_wear_item: bool = False
    oem_part_numbers: list[str] = field(default_factory=list)
    part_category: str | None = None
    recommendations: list[PartRecommendation] = field(default_factory=list)
    avoid: list[AvoidItem] = field(default_factory=list)
    notes: str | None = None
    relevant_makes: list[str] = field(default_factory=list)
    raw_response: dict | None = None
    error: str | None = None


# ── Retailer URL templates for buy links ─────────────────────────────────

_RETAILER_URLS: dict[str, str] = {
    "FCP Euro": "https://www.fcpeuro.com/products?keywords={q}",
    "ECS Tuning": "https://www.ecstuning.com/Search/{q}/",
    "RockAuto": "https://www.rockauto.com/en/partsearch/?partnum={q}",
    "Amazon": "https://www.amazon.com/s?k={q}&i=automotive",
    "eBay": "https://www.ebay.com/sch/i.html?_nkw={q}&_sacat=6028",
    "AutoZone": "https://www.autozone.com/searchresult?searchText={q}",
    "O'Reilly": "https://www.oreillyauto.com/shop/b/search?q={q}",
    "Advance Auto": "https://shop.advanceautoparts.com/find/{q}.html",
    "NAPA": "https://www.napaonline.com/en/search?q={q}",
    "Parts Geek": "https://www.partsgeek.com/search.html?query={q}",
    "Pelican Parts": "https://www.pelicanparts.com/catalog/search.php?searchString={q}",
    "Turner Motorsport": "https://www.turnermotorsport.com/Search?q={q}",
    "BimmerWorld": "https://www.bimmerworld.com/search?q={q}",
    "Summit Racing": "https://www.summitracing.com/search?SortBy=Default&SortOrder=Default&keyword={q}",
    "JEGS": "https://www.jegs.com/webapp/wcs/stores/servlet/SearchView?storeId=10001&searchTerm={q}",
    "Suncoast Parts": "https://www.suncoastparts.com/SearchResults.asp?Search={q}",
    "Stoddard": "https://www.stoddard.com/catalogsearch/result/?q={q}",
    "IPD": "https://www.ipdusa.com/search?type=product&q={q}",
    "YearOne": "https://www.yearone.com/Catalog?SearchText={q}",
    "Classic Industries": "https://www.classicindustries.com/search/?q={q}",
    "McMaster-Carr": "https://www.mcmaster.com/{q}",
    "CarParts.com": "https://www.carparts.com/search?q={q}",
    "1A Auto": "https://www.1aauto.com/search?q={q}",
}


def _generate_buy_links(part_number: str, retailers: list[str]) -> list[dict]:
    """Generate buy links for a part number at specific retailers."""
    links = []
    q = quote_plus(part_number)
    for retailer in retailers:
        template = _RETAILER_URLS.get(retailer)
        if template:
            links.append(
                {
                    "store": retailer,
                    "url": template.replace("{q}", q),
                }
            )
    # Always add eBay and Amazon if not already there
    for fallback in ["Amazon", "eBay"]:
        if fallback not in retailers:
            template = _RETAILER_URLS[fallback]
            links.append(
                {
                    "store": fallback,
                    "url": template.replace("{q}", q),
                }
            )
    return links


# ── Provider selection ───────────────────────────────────────────────────


def _get_provider() -> str | None:
    """
    Determine which AI provider to use.

    Priority: Gemini (free tier) > OpenAI (cheapest paid) > Anthropic > None.
    """
    if settings.gemini_api_key:
        return "gemini"
    if settings.openai_api_key:
        return "openai"
    if settings.anthropic_api_key:
        return "anthropic"
    return None


def _user_message(query: str, vehicle_make: str | None, vehicle_model: str | None, vehicle_year: str | None) -> str:
    """Build the user prompt, optionally including vehicle context for personalization."""
    parts = [f'Analyze this auto parts search query and provide recommendations: "{query}"']
    if vehicle_make or vehicle_model or vehicle_year:
        v = " ".join(filter(None, [vehicle_year, vehicle_make, vehicle_model]))
        parts.append(f"The user's vehicle (use for fit and recommendations): {v}.")
    return " ".join(parts)


async def get_ai_recommendations(
    query: str,
    vehicle_make: str | None = None,
    vehicle_model: str | None = None,
    vehicle_year: str | None = None,
) -> AIAdvisorResult:
    """
    Call the AI advisor to analyze a parts search query.

    Optionally pass the user's vehicle make/model/year for personalized notes.
    Automatically selects the best available provider.
    """
    if not settings.ai_synthesis_enabled:
        return AIAdvisorResult(error="AI synthesis is disabled")

    provider = _get_provider()
    if not provider:
        return AIAdvisorResult(
            error="No AI API key configured. Set GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY in .env"
        )

    user_msg = _user_message(query, vehicle_make, vehicle_model, vehicle_year)
    try:
        if provider == "gemini":
            return await _call_gemini(user_msg)
        elif provider == "openai":
            return await _call_openai(user_msg)
        else:
            return await _call_anthropic(user_msg)
    except Exception as e:
        logger.error(f"AI advisor ({provider}) failed: {e}")
        return AIAdvisorResult(error=str(e))


# ── Gemini provider (free tier) ──────────────────────────────────────────


async def _call_gemini(user_message: str) -> AIAdvisorResult:
    """Call Google Gemini REST API and parse the structured JSON response."""
    model = settings.gemini_model
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url,
            headers={
                "x-goog-api-key": settings.gemini_api_key,
                "Content-Type": "application/json",
            },
            json={
                "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\n---\n\n{user_message}"}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.3,
                    "maxOutputTokens": 4096,
                },
            },
        )

    if response.status_code != 200:
        error_text = response.text[:500]
        logger.error(f"Gemini API error {response.status_code}: {error_text}")
        return AIAdvisorResult(error=f"AI API error: HTTP {response.status_code}")

    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        return AIAdvisorResult(error="Empty AI response")

    # Extract text from Gemini response format
    parts = candidates[0].get("content", {}).get("parts", [])
    text = parts[0].get("text", "") if parts else ""

    usage = data.get("usageMetadata", {})
    logger.info(
        f"Gemini ({model}): {usage.get('promptTokenCount', '?')} prompt + "
        f"{usage.get('candidatesTokenCount', '?')} completion tokens"
    )
    return _parse_ai_response(text)


# ── OpenAI provider ─────────────────────────────────────────────────────


async def _call_openai(user_message: str) -> AIAdvisorResult:
    """Call OpenAI Chat Completions API and parse the structured response."""
    model = settings.openai_model

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0.3,
                "max_tokens": 4096,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            },
        )

    if response.status_code != 200:
        error_text = response.text[:500]
        logger.error(f"OpenAI API error {response.status_code}: {error_text}")
        return AIAdvisorResult(error=f"AI API error: HTTP {response.status_code}")

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        return AIAdvisorResult(error="Empty AI response")

    text = choices[0].get("message", {}).get("content", "")
    usage = data.get("usage", {})
    logger.info(
        f"OpenAI ({model}): {usage.get('prompt_tokens', '?')} prompt + "
        f"{usage.get('completion_tokens', '?')} completion tokens"
    )
    return _parse_ai_response(text)


# ── Anthropic provider ──────────────────────────────────────────────────


async def _call_anthropic(user_message: str) -> AIAdvisorResult:
    """Call Anthropic Messages API and parse the structured response."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4096,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_message}],
            },
        )

    if response.status_code != 200:
        error_text = response.text[:500]
        logger.error(f"Anthropic API error {response.status_code}: {error_text}")
        return AIAdvisorResult(error=f"AI API error: HTTP {response.status_code}")

    data = response.json()
    content = data.get("content", [])
    if not content:
        return AIAdvisorResult(error="Empty AI response")

    text = content[0].get("text", "")
    usage = data.get("usage", {})
    logger.info(
        f"Anthropic (claude-sonnet-4): {usage.get('input_tokens', '?')} input + "
        f"{usage.get('output_tokens', '?')} output tokens"
    )
    return _parse_ai_response(text)


# ── Response parsing (shared) ───────────────────────────────────────────


def _try_repair_json(text: str) -> dict | None:
    """
    Attempt to repair truncated JSON by closing open strings, arrays, and objects.

    Returns the parsed dict on success, or None if repair fails.
    """
    # Strip trailing comma or whitespace
    repaired = text.rstrip()
    repaired = re.sub(r",\s*$", "", repaired)

    # Track nesting to figure out what needs closing
    in_string = False
    escape_next = False
    stack = []  # '[' or '{'

    for ch in repaired:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            if in_string:
                escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ("{", "["):
            stack.append(ch)
        elif ch == "}":
            if stack and stack[-1] == "{":
                stack.pop()
        elif ch == "]":
            if stack and stack[-1] == "[":
                stack.pop()

    # If we're inside a string, close it
    if in_string:
        repaired += '"'

    # Strip any trailing incomplete key-value (e.g. `"key": "val` after closing the string)
    # Re-strip trailing comma
    repaired = re.sub(r",\s*$", "", repaired.rstrip())

    # Close open brackets/braces in reverse order
    for bracket in reversed(stack):
        if bracket == "{":
            repaired += "}"
        else:
            repaired += "]"

    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        return None


def _parse_ai_response(text: str) -> AIAdvisorResult:
    """Parse the AI's JSON response into an AIAdvisorResult."""
    # Strip markdown code fences if present (handles ```json, ```JSON, bare ```)
    text = text.strip()
    if text.startswith("```"):
        # Remove opening fence line (e.g. "```json\n" or "```\n")
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[: text.rfind("```")]
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse failed, attempting repair: {e}")
        data = _try_repair_json(text)
        if data is None:
            logger.error(f"JSON repair also failed.\nText: {text[:500]}")
            return AIAdvisorResult(error="Failed to parse AI response")

    result = AIAdvisorResult(raw_response=data)

    # Parse vehicle info
    vehicle = data.get("vehicle", {})
    result.vehicle_make = vehicle.get("make")
    result.vehicle_model = vehicle.get("model")
    result.vehicle_generation = vehicle.get("generation")
    result.vehicle_years = vehicle.get("years")

    # Parse part info
    part = data.get("part", {})
    result.part_type = part.get("type")
    result.is_consumable = part.get("is_consumable", False)
    result.is_wear_item = part.get("is_wear_item", False)
    result.oem_part_numbers = part.get("oem_part_numbers", [])
    result.part_category = part.get("category")

    # Parse recommendations
    for rec in data.get("recommendations", []):
        part_number = rec.get("part_number", "")
        retailers = rec.get("best_retailers", [])
        buy_links = _generate_buy_links(part_number, retailers)

        result.recommendations.append(
            PartRecommendation(
                rank=rec.get("rank", 0),
                grade=rec.get("grade", ""),
                brand=rec.get("brand", ""),
                part_number=part_number,
                title=rec.get("title", ""),
                why=rec.get("why", ""),
                quality_tier=rec.get("quality_tier", "unknown"),
                quality_score=rec.get("quality_score", 0),
                estimated_price_low=rec.get("estimated_price_low", 0),
                estimated_price_high=rec.get("estimated_price_high", 0),
                best_retailers=retailers,
                buy_links=buy_links,
            )
        )

    # Parse avoid list
    for item in data.get("avoid", []):
        result.avoid.append(AvoidItem(brand=item.get("brand", ""), reason=item.get("reason", "")))

    result.notes = data.get("notes")
    result.relevant_makes = data.get("relevant_makes", [])

    return result
