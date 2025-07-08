import PyPDF2
import re
from typing import Dict, List
from dateutil.parser import parse # Import parse from dateutil for robust date parsing
from datetime import datetime

def extract_pdf_text(pdf_path: str) -> str:
    """Extract text from PDF file"""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {str(e)}") # Added print for debugging
        return ""
    return text

def extract_cv_info(cv_text: str) -> Dict:
    """Extract employment information from CV text."""
    employment_info = []

    # Find the Professional Experience section
    section_match = re.search(
        r"Professional Experience\s*\n(.*?)(?=\n---|$)",
        cv_text,
        re.DOTALL | re.IGNORECASE
    )
    print(f"Section match: {section_match}")  # Debugging line to check section match
    if section_match:
        experience_text = section_match.group(1).strip()

        # Look for blocks of 2 lines: title, then "Company, City | Date – Date"
        pattern = re.compile(
            r"(?P<position>.+?)\s*\n\s*(?P<company>[^,]+),?\s+[^|]*\|\s+(?P<start>\d{2}/\d{4}|\d{4})\s*[-–]\s*(?P<end>Present|\d{2}/\d{4}|\d{4})",
            re.IGNORECASE
        )

        matches = pattern.finditer(experience_text)

        for match in matches:
            position = match.group("position").strip()
            company = match.group("company").strip()
            start = match.group("start").strip()
            end = match.group("end").strip()

            if end.lower() == "present":
                end = datetime.now().strftime("%m/%Y")

            employment_info.append({
                "position": position,
                "company": company,
                "start_period": start,
                "end_period": end,
                "period": f"{start}-{end}"
            })

    return {
        "employment_history": employment_info,
        "total_positions": len(employment_info)
    }

def extract_pf_info(pf_text: str) -> Dict:
    """Extract PF contribution information"""
    pf_entries = []

    # Split the text into lines/records. The sample PF text uses "\r\n" as record delimiters.
    pf_lines = pf_text.split('\r\n')

    # Iterate through lines, skipping the header and any empty lines.
    # We look for lines that start with a quoted string (indicating a data row).
    for line in pf_lines:
        line = line.strip()
        if not line.startswith('"') or "Period" in line: # Skip header and non-data lines
            continue

        # Regex to extract fields that are enclosed in double quotes.
        # `[^"]*?` matches any character except a double quote, non-greedily.
        # `re.DOTALL` is crucial here to allow `.` to match newline characters inside quoted fields.
        quoted_fields = re.findall(r'"([^"]*?)"', line, re.DOTALL)

        # There are 7 expected fields in each PF entry
        if len(quoted_fields) >= 7:
            try:
                # Clean up newlines and extra spaces within each captured field
                period_raw = quoted_fields[0].replace('\n', ' ').strip()
                employer = quoted_fields[1].replace('\n', ' ').strip()
                establishment_id = quoted_fields[2].replace('\n', ' ').strip()
                employee_contribution = quoted_fields[3].replace('\n', ' ').strip()
                employer_contribution = quoted_fields[4].replace('\n', ' ').strip()
                pension = quoted_fields[5].replace('\n', ' ').strip()
                status = quoted_fields[6].replace('\n', ' ').strip()

                # Parse the period (e.g., "MM/YYYY - MM/YYYY" or "MM/YYYY - Present")
                period_parts = period_raw.split('-')
                start_period = period_parts[0].strip()
                end_period = period_parts[1].strip() if len(period_parts) > 1 else "" # Handle cases where end period might be missing or malformed

                pf_entries.append({
                    'start_period': start_period,
                    'end_period': end_period,
                    'employer': employer,
                    'establishment_id': establishment_id,
                    'employee_contribution': employee_contribution,
                    'employer_contribution': employer_contribution,
                    'pension': pension,
                    'status': status
                })
            except Exception as e:
                print(f"Error parsing PF line (skipping): {line} - Error: {str(e)}")
                continue # Skip line if parsing fails

    return {
        'pf_entries': pf_entries,
        'total_entries': len(pf_entries)
    }