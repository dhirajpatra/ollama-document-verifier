# config.py

import os

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma:2b") # Default to gemma:2b if not set
OLLAMA_BASE_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Prompts for OLLAMA (these are examples, will need fine-tuning)

# Prompt for CV data extraction
CV_EXTRACTION_PROMPT = """
You are an expert resume parser. Extract the following information from the provided CV text into a JSON object.
Focus on employment history. If a field is not found, use an empty string or null for non-string types.

CV Text:
{cv_text}

Expected JSON Schema:
```json
{{
    "name": "string",
    "email": "string",
    "phone": "string",
    "total_experience_years": "float",
    "employment_history": [
        {{
            "company_name": "string",
            "job_title": "string",
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD"
        }}
    ]
}}
````

Output only the JSON object.
"""

# Prompt for PF data extraction (PF statements are highly variable, this is a generic example)

PF_EXTRACTION_PROMPT = """
You are an expert at parsing Provident Fund (PF) statements. Extract the following information from the provided PF document text into a JSON object.
Focus on employment periods and associated employers.

PF Document Text:
{pf_text}

Expected JSON Schema:

```json
{{
    "pf_account_number": "string",
    "contributions": [
        {{
            "employer_name": "string",
            "period_start": "YYYY-MM-DD",
            "period_end": "YYYY-MM-DD",
            "employee_share_contribution": "float",
            "employer_share_contribution": "float"
        }}
    ]
}}
```

Output only the JSON object. Be precise with dates and names.
"""

# NEW/UPDATED Prompt for verification using OLLAMA

VERIFICATION_PROMPT = """
You are a highly skilled document verification assistant.
Your task is to compare employment history data extracted from a Candidate's CV and their Provident Fund (PF) document.
You need to identify matches and discrepancies based on company names and employment periods.

Here is the extracted data:

--- CV Employment History ---
{cv_employment_history_json}

--- PF Contributions (Employment Periods) ---
{pf_contributions_json}

Carefully compare each entry from the CV with each entry from the PF contributions.
Consider the following for comparison:

1.  **Company Name Similarity:** Companies like "ABC Tech Solutions" and "ABC Tech" or "XYZ Software" and "XYZ Software Pvt. Ltd." should be considered a match if they refer to the same entity. Use common sense for abbreviations and legal suffixes.
2.  **Employment Period Overlap/Alignment:** Dates should align closely. A small gap (e.g., a month) or overlap is acceptable for transitions between jobs. Consider periods like "2021 - Present" from CV matching "03/2021-Present" from PF.
3.  **Missing Entries:** Note if a company or period is present in one document but completely absent from the other, after considering reasonable matches.

Provide your analysis in a structured JSON object.

Expected JSON Schema for output:

```json
{{
    "summary": "string",
    "status": "PASS/FAIL/PARTIAL_PASS",
    "discrepancies": [
        {{
            "type": "COMPANY_MISMATCH/DATE_MISMATCH/MISSING_IN_CV/MISSING_IN_PF",
            "description": "string",
            "cv_entry": {{}},
            "pf_entry": {{}}
        }}
    ],
    "matched_entries": [
        {{
            "cv_entry": {{}},
            "pf_entry": {{}}
        }}
    ],
    "analysis_details": "string"
}}
```

  - `summary`: A high-level conclusion (e.g., "All employment history matches.", "Some discrepancies found in dates.", "Significant mismatches.").
  - `status`: "PASS" if all entries match perfectly or with minor, acceptable variations. "PARTIAL\_PASS" if some entries match but others have discrepancies. "FAIL" if major discrepancies or no matches are found.
  - `discrepancies`: List of objects for each inconsistency. `cv_entry` and `pf_entry` should be the *original extracted JSON objects* for easy reference. Set one to `{}` if missing in that document.
  - `matched_entries`: List of objects for each pair of matching entries.
  - `analysis_details`: A narrative string explaining your reasoning for the status and summary.

Output only the JSON object.
"""
