"""
Part number extraction and normalization utilities.
"""
import re
from typing import List


def normalize_query(query: str) -> str:
    """
    Normalize a search query for consistent processing.
    - Strip whitespace
    - Convert to uppercase
    - Remove excessive spaces
    """
    if not query:
        return ""
    normalized = " ".join(query.upper().split())
    return normalized.strip()


def extract_part_numbers(text: str) -> List[str]:
    """
    Extract potential part numbers from text using regex and heuristics.
    
    Part number patterns:
    - Alphanumeric codes with dashes (e.g., "12345-ABC", "ABC-123")
    - Codes with dots (e.g., "123.456")
    - OEM-style codes (e.g., "12345ABC", "ABC123")
    - Common formats: 5-10 chars, may include dashes, dots, or be continuous
    
    Returns a list of normalized part numbers (uppercase, spaces removed, dashes preserved).
    """
    if not text:
        return []
    
    # Common part number patterns
    patterns = [
        # Pattern 1: Alphanumeric with dashes (e.g., "12345-ABC", "ABC-123-X")
        r'\b[A-Z0-9]{2,}-[A-Z0-9-]{1,}\b',
        # Pattern 2: Alphanumeric with dots (e.g., "123.456", "ABC.123")
        r'\b[A-Z0-9]{2,}\.[A-Z0-9]{1,}\b',
        # Pattern 3: Continuous alphanumeric (5-15 chars, at least 1 letter and 1 digit)
        r'\b(?=[A-Z]*[0-9])(?=[0-9]*[A-Z])[A-Z0-9]{5,15}\b',
    ]
    
    part_numbers = set()
    
    # First, normalize text to uppercase
    text_upper = text.upper()
    
    # Extract using each pattern
    for pattern in patterns:
        matches = re.findall(pattern, text_upper)
        for match in matches:
            # Normalize: remove spaces, preserve dashes and dots
            normalized = match.strip().replace(" ", "")
            # Filter out very short or very long matches
            if 3 <= len(normalized.replace("-", "").replace(".", "")) <= 20:
                part_numbers.add(normalized)
    
    # Additional heuristic: look for common OEM patterns
    # e.g., "OEM 12345" or "Part # ABC123"
    oem_patterns = [
        r'(?:OEM|PART\s*#?|PN|P/N)\s*([A-Z0-9-]{3,15})',
        r'#\s*([A-Z0-9-]{3,15})',
    ]
    
    for pattern in oem_patterns:
        matches = re.findall(pattern, text_upper)
        for match in matches:
            normalized = match.strip().replace(" ", "")
            if 3 <= len(normalized.replace("-", "").replace(".", "")) <= 20:
                part_numbers.add(normalized)
    
    return sorted(list(part_numbers))


def normalize_part_number(part_num: str) -> str:
    """
    Normalize a single part number.
    - Convert to uppercase
    - Remove spaces
    - Preserve dashes and dots
    """
    if not part_num:
        return ""
    normalized = part_num.upper().strip().replace(" ", "")
    return normalized
