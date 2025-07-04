# utils.py
from datetime import datetime
from fuzzywuzzy import fuzz
import json
import re

def parse_date(date_string):
    """
    Attempts to parse a date string into a datetime object.
    Returns None if parsing fails or input is not a string.
    Handles common formats. Add more formats as needed.
    """
    if not isinstance(date_string, str): # Crucial check for non-string input
        return None

    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d",
        "%b %d, %Y", "%B %d, %Y", "%Y", "%b %Y", "%B %Y",
        "%m/%Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_string.strip(), fmt) # .strip() to remove whitespace
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

def date_overlap(start1, end1, start2, end2, tolerance_days=30):
    """
    Checks if two date ranges overlap, with a given tolerance.
    Dates should be datetime objects.
    """
    if not all([start1, end1, start2, end2]):
        return False

    if (max(start1, start2) <= min(end1, end2)) or \
       (abs((start1 - end2).days) <= tolerance_days) or \
       (abs((start2 - end1).days) <= tolerance_days):
        return True
    return False

def format_date_for_llm(dt_obj):
    """Formats a datetime object to YYYY-MM-DD for LLM input."""
    if isinstance(dt_obj, datetime):
        return dt_obj.strftime("%Y-%m-%d")
    return ""

def safe_json_parse(json_string):
    """
    Safely parses a JSON string, handling potential LLM malformed output,
    especially JSON wrapped in markdown code blocks.
    """
    match = re.search(r"```json\s*(.*?)\s*```", json_string, re.DOTALL)
    if match:
        json_content = match.group(1)
    else:
        json_content = json_string.strip()

    try:
        return json.loads(json_content)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from LLM: {e}")
        print(f"Malformed JSON string (cleaned attempt): {json_content[:500]}...")
        print(f"Original LLM output (full): {json_string}")
        return None