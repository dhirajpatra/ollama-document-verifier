import PyPDF2
import re
from typing import Dict, List
from dateutil.parser import parse # Import parse from dateutil for robust date parsing
from datetime import datetime
from logger import logger

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
    if not isinstance(cv_text, str):
        raise TypeError(f"cv_text must be a string, got {type(cv_text)}")
    
    employment_info = []

    # Find the Professional Experience section
    section_match = re.search(
        r"Professional Experience\s*\n+(.*?)(?=\n+(Education|Certifications|Projects|Skills|---|$))",
        cv_text,
        re.DOTALL | re.IGNORECASE
    )
    logger.info(f"Section match: {section_match}")  # Debugging line to check section match

    if section_match:
        experience_text = section_match.group(1).strip()
        logger.info(f"Extracted experience text: {experience_text[:100]}...")  # Log first 100 chars for debugging

        pattern = re.compile(
            r"""
            (?P<position>[^\n]+?)                      # Position/title (first line, non-greedy up to newline)
            \s*\n                                      # Newline after position, with optional whitespace
            (?P<company>[^|\n]+?),\s*(?P<city>[^|]+?)\s*\|\s* # Company name before comma, then city before |, non-greedy
            (?P<start>\d{2}/\d{4}|\d{4})\s*[-–]\s* # Start date (DD/YYYY or YYYY)
            (?P<end>Present|\d{2}/\d{4}|\d{4})         # End date (Present, DD/YYYY, or YYYY)
            \s*\n                                      # Newline after dates
            (?P<details>(?:(?!---|\n{2,}).*\n?)*)      # Description lines until two newlines or '---'
            """,
            re.IGNORECASE | re.VERBOSE
        )

        employment_info = []
        matches = list(pattern.finditer(experience_text))
        logger.info(f"Found {len(matches)} matches in experience text")

        for match in matches:
            position = match.group("position").strip()
            company = match.group("company").strip()
            city = match.group("city").strip() # New: Extract city
            start = match.group("start").strip()
            end = match.group("end").strip()
            details = match.group("details").strip() # New: Extract details

            # Handle 'Present' for the end date
            if end.lower() == "present":
                end = datetime.now().strftime("%m/%Y") # Format as MM/YYYY

            employment_info.append({
                "position": position,
                "company": company,
                "city": city, # New: Add city to dictionary
                "start_period": start,
                "end_period": end,
                "period": f"{start}-{end}",
                "details": details # New: Add details to dictionary
            })

    return {
        "employment_history": employment_info,
        "total_positions": len(employment_info)
    }

def extract_pf_info(pf_text: str) -> Dict:
    if not isinstance(pf_text, str):
        raise TypeError(f"pf_text must be a string, got {type(pf_text)}")

    pf_data = {
        'name': '',
        'uan': '',
        'pf_account_number': '',
        'date_generated': '',
        'pf_entries': [],
        'total_entries': 0
    }

    lines = pf_text.split('\n')
    
    name_re = re.compile(r"Name:\s*(.+)", re.IGNORECASE)
    uan_re = re.compile(r"UAN \(Universal Account Number\):\s*(\d+)", re.IGNORECASE)
    pf_acc_re = re.compile(r"PF Account Number:\s*([A-Z]{2}/[0-9]{5}/[0-9]{7})", re.IGNORECASE)
    date_gen_re = re.compile(r"Date Generated:\s*(.+)", re.IGNORECASE)

    in_table_data_section = False
    current_record_buffer = []

    new_record_start_pattern = re.compile(r"^[A-Za-z]{3}-\d{4}\s+")
    
    for line in lines:
        line = line.strip()

        if not in_table_data_section:
            name_match = name_re.match(line)
            if name_match: pf_data['name'] = name_match.group(1).strip(); continue
            uan_match = uan_re.match(line)
            if uan_match: pf_data['uan'] = uan_match.group(1).strip(); continue
            pf_acc_match = pf_acc_re.match(line)
            if pf_acc_match: pf_data['pf_account_number'] = pf_acc_match.group(1).strip(); continue
            date_gen_match = date_gen_re.match(line)
            if date_gen_match: pf_data['date_generated'] = date_gen_match.group(1).strip(); continue
            
            if "Employment & Contribution History" in line or ("Period" in line and "Employe" in line):
                in_table_data_section = True
                continue
            continue

        if not line or line.startswith('---'):
            if current_record_buffer:
                parsed_entry = _parse_consolidated_pf_record(" ".join(current_record_buffer))
                if parsed_entry:
                    pf_data['pf_entries'].append(parsed_entry)
                current_record_buffer = []
            continue

        if new_record_start_pattern.match(line):
            if current_record_buffer:
                parsed_entry = _parse_consolidated_pf_record(" ".join(current_record_buffer))
                if parsed_entry:
                    pf_data['pf_entries'].append(parsed_entry)
            current_record_buffer = [line]
        else:
            current_record_buffer.append(line)

    if current_record_buffer:
        parsed_entry = _parse_consolidated_pf_record(" ".join(current_record_buffer))
        if parsed_entry:
            pf_data['pf_entries'].append(parsed_entry)

    pf_data['total_entries'] = len(pf_data['pf_entries'])
    return pf_data


def _parse_consolidated_pf_record(consolidated_line: str) -> Dict:
    try:
        record_parser_re = re.compile(
            r"^\s*([A-Za-z]{3}-\d{4})\s+" +
            r"(.+?)\s*" +
            r"(\d{1,3}(?:,\d{3})*)\s+" +
            r"(\d{1,3}(?:,\d{3})*)\s+" +
            r"(\d{1,3}(?:,\d{3})*)\s+" +
            r"(.+)$"
        )

        match = record_parser_re.match(consolidated_line)

        if not match:
            logger.warning(f"Failed to parse consolidated record line: {consolidated_line}")
            return None

        period_raw = match.group(1).strip()
        employer_id_combined = match.group(2).strip()
        employee_contribution = match.group(3).replace(',', '').strip()
        employer_contribution = match.group(4).replace(',', '').strip()
        pension = match.group(5).replace(',', '').strip()
        status = match.group(6).strip()

        establishment_id = ""
        employer = employer_id_combined

        tokens = employer_id_combined.split()
        
        potential_id_tokens = []
        employer_name_tokens = []

        for token in reversed(tokens):
            if re.fullmatch(r"([A-Z]{2}\d{4,}|^\d{4,})", token):
                potential_id_tokens.insert(0, token)
            else:
                employer_name_tokens.insert(0, token)
        
        if potential_id_tokens:
            establishment_id = " ".join(potential_id_tokens).strip()
            employer = " ".join(employer_name_tokens).strip()
        else:
            employer = employer_id_combined.strip()
            establishment_id = ""

        employer = employer.strip()
        
        return {
            'start_period': period_raw,
            'end_period': period_raw,
            'employer': employer,
            'establishment_id': establishment_id,
            'employee_contribution': employee_contribution,
            'employer_contribution': employer_contribution,
            'pension': pension,
            'status': status
        }
    except Exception as e:
        logger.error(f"Error in _parse_consolidated_pf_record for '{consolidated_line}': {e}")
        return None