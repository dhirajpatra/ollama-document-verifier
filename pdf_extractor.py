import PyPDF2
import re
from typing import Dict, List
from dateutil.parser import parse # Import parse from dateutil for robust date parsing

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
    """Extract employment information from CV"""
    employment_info = []

    # Attempt to find the "Professional Experience" section
    # This regex captures everything between "Professional Experience" and the next major section (Education, Certifications, Projects) or end of document.
    professional_experience_section_match = re.search(
        r'Professional Experience\n\n(.+?)(?=\n\nEducation|\n\nCertifications|\n\nProjects|\n\n$)',
        cv_text,
        re.DOTALL
    )

    if professional_experience_section_match:
        section_text = professional_experience_section_match.group(1)
        # Refined pattern to capture Position, Company, Start Date, End Date within the section
        # It looks for:
        # 1. Position: (Group 1) - starts a line, contains letters/spaces/symbols. Made non-greedy.
        # 2. Company: (Group 2) - appears on subsequent lines, followed by ", City | ". Made non-greedy.
        # 3. Start Date: (Group 3) - MM/YYYY or YYYY format.
        # 4. End Date: (Group 4) - MM/YYYY, YYYY, or "Present".
        # Uses re.MULTILINE to allow `^` to match start of lines within `section_text`.
        # Uses re.DOTALL to allow `.` to match newlines within position/company names.
        employment_pattern_simple = re.compile(
            r'^\s*([A-Za-z0-9\s&,.-]+?)\s*\n+'  # Position (Group 1) - allows multi-line, non-greedy
            r'([A-Za-z\s&,.-]+?),\\s*City\\s*\\|\\s*'  # Company (Group 2) - including ", City |"
            r'(\d{2}/\d{4}|\d{4})\\s*[-–]\\s*'  # Start Date (Group 3) and separator
            r'(\d{2}/\d{4}|\d{4}|Present)'  # End Date (Group 4)
            r'\s*$', # End of entry, with optional spaces
            re.MULTILINE | re.DOTALL
        )
        matches = employment_pattern_simple.findall(section_text)

        for match in matches:
            position = match[0].strip()
            company = match[1].strip()
            start_period = match[2].strip()
            end_period = match[3].strip()

            employment_info.append({
                'position': position,
                'company': company,
                'start_period': start_period,
                'end_period': end_period,
                'period': f"{start_period}-{end_period}"
            })

    return {
        'employment_history': employment_info,
        'total_positions': len(employment_info)
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