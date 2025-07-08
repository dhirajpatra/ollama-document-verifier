# llm_utils.py

import json
import re
from datetime import datetime
from fuzzywuzzy import fuzz # Keeping this, as it might be useful elsewhere or for display


def safe_json_parse(json_string):
    """
    Safely parses a JSON string, handling potential LLM malformed output,
    especially JSON wrapped in markdown code blocks.
    """
    # Attempt to find JSON within markdown code blocks
    match = re.search(r"```json\s*(.*?)\s*```", json_string, re.DOTALL)
    if match:
        json_content = match.group(1)
    else:
        # If no markdown block, assume the whole string *might* be JSON (e.g., if LLM improved)
        json_content = json_string.strip()

    try:
        return json.loads(json_content)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from LLM: {e}")
        print(f"Malformed JSON string (cleaned attempt): {json_content[:500]}...")
        print(f"Original LLM output (full): {json_string}") # Print full original for debugging
        return None

def parse_date(date_string):
    """
    Attempts to parse a date string into a datetime object.
    Returns None if parsing fails or input is not a string/valid format.
    Handles common formats like YYYY-MM-DD, MM/YYYY, YYYY, etc.
    """
    if not isinstance(date_string, str):
        return None # Return None immediately if input is not a string

    date_string = date_string.strip() # Remove leading/trailing whitespace

    formats = [
        "%Y-%m-%d",    # 2021-01-15
        "%d-%m-%Y",    # 15-01-2021
        "%m/%d/%Y",    # 01/15/2021
        "%Y/%m/%d",    # 2021/01/15
        "%b %d, %Y",   # Jan 15, 2021
        "%B %d, %Y",   # January 15, 2021
        "%m/%Y",       # 07/2019 (common for PF)
        "%Y"           # 2019 (common for CV years)
    ]
    # Handle "Present" explicitly
    if date_string.lower() == "present":
        # You might want to return a specific future date, or leave it to be handled upstream
        return datetime.now() # Or datetime(2099, 12, 31) for a fixed "future" date

    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    return None # Return None if no format matches

def fuzzy_match_names(name1, name2, threshold=80):
    """
    Performs fuzzy matching between two names.
    Returns True if similarity is above threshold, False otherwise.
    """
    if not name1 or not name2:
        return False
    score = fuzz.ratio(name1.lower(), name2.lower())
    return score >= threshold