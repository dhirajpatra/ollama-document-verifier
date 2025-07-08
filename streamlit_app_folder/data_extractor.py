import PyPDF2
import re
import pandas as pd
from datetime import datetime
import json
import requests
import os
from typing import Dict, List, Optional

class DocumentExtractor:
    def __init__(self):
        self.ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""
    
    def extract_cv_data(self, cv_text: str) -> Dict:
        """Extract structured data from CV text using AI (if available) or regex."""
        # Check if Ollama is accessible to use AI for extraction
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                # Use AI for extraction if Ollama is running
                prompt = f"""
                Extract the following information from this CV text and return as JSON:
                
                1. Personal Information (name, email, phone, location)
                2. Employment History (company, position, start_date, end_date, location)
                3. Skills (technical skills list)
                4. Education (degree, university, year)
                
                CV Text:
                {cv_text}
                
                Return only valid JSON with the extracted data.
                """
                ollama_response = requests.post(f"{self.ollama_url}/api/generate", json={
                    "model": "gemma:2b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}
                })
                ollama_response.raise_for_status()
                response_content = ollama_response.json()
                
                # Extract the actual JSON string from the 'response' field
                try:
                    # Attempt to parse the 'response' field as JSON
                    extracted_data = json.loads(response_content['response'])
                    return extracted_data
                except json.JSONDecodeError:
                    # If it's not a direct JSON string, try to find a JSON block
                    json_match = re.search(r'```json\s*(\{.*\})\s*```', response_content['response'], re.DOTALL)
                    if json_match:
                        try:
                            extracted_data = json.loads(json_match.group(1))
                            return extracted_data
                        except json.JSONDecodeError:
                            pass # Fallback to regex if JSON extraction from block fails

        except requests.exceptions.ConnectionError:
            print("Ollama not running, falling back to regex for CV data extraction.")
        except Exception as e:
            print(f"AI extraction failed: {e}, falling back to regex for CV data extraction.")

        # Fallback to regex-based extraction if AI fails or is not available
        employment_info = []
        # Adjusted regex to be more robust for different date formats (e.g., "YYYY - YYYY" or "MM/YYYY - MM/YYYY")
        # and to capture the company and position correctly.
        employment_pattern = r'(?P<position>[A-Za-z\s&,.-]+)\s*\n?(?P<company>[A-Za-z\s,.-]+)\s*\|\s*(?P<start_date>(?:\d{2}/\d{4}|\d{4}))\s*[-–]\s*(?P<end_date>(?:\d{2}/\d{4}|\d{4}|Present))'
        
        matches = re.finditer(employment_pattern, cv_text, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            employment_info.append({
                'position': match.group('position').strip(),
                'company': match.group('company').strip(),
                'start_date': match.group('start_date').strip(),
                'end_date': match.group('end_date').strip(),
                'period': f"{match.group('start_date').strip()}-{match.group('end_date').strip()}"
            })
        
        return {'employment_history': employment_info}

    def extract_pf_data(self, pf_text: str) -> Dict:
        """Extract PF contribution information from PF statement text."""
        result = {
            "personal_info": {},
            "employment_records": []
        }

        # Extract personal information
        name_match = re.search(r'Name:\s*(.+)', pf_text)
        uan_match = re.search(r'UAN \(Universal Account Number\):\s*(\d+)', pf_text)
        pf_account_match = re.search(r'PF Account Number:\s*([A-Z]{2}/\d+/\d+)', pf_text)

        if name_match:
            result["personal_info"]["name"] = name_match.group(1).strip()
        if uan_match:
            result["personal_info"]["uan"] = uan_match.group(1).strip()
        if pf_account_match:
            result["personal_info"]["pf_account_number"] = pf_account_match.group(1).strip()

        # Pattern to match PF entries from the table-like structure.
        # This regex is more robust to variations in spacing and line breaks within cells.
        pf_pattern = re.compile(
            r'(\d{2}/\d{4}|[A-Za-z]{3}-\d{4})\s*[-–]?\s*(\d{2}/\d{4}|[A-Za-z]{3}-\d{4}|Present)\s*\n*' # Period (e.g., 07/2019-11/2021 or Oct-2019)
            r'\"?Employer\n*Name\n*([A-Za-z\s&,.-]+)\"?\s*\n*' # Employer Name
            r'(?:Establishment\n*ID\n*)?([A-Z]{2}\d{7,11})\s*\n*' # Establishment ID (e.g., MH123450009 or MH123450000081412)
            r'(?:Employee\n*Contribution\n*\(₹\)\n*)?([\d,]+)\s*\n*' # Employee Contribution
            r'(?:Employer\n*Contribution\n*\(₹\)\n*)?([\d,]+)\s*\n*' # Employer Contribution
            r'(?:Pension\n*\(EPS\)\s*\(?\)?\n*)?([\d,]+)\s*\n*' # Pension Contribution
            r'(?:Status\n*)?(Active\s*\(Closed\)|\s*Missing|\s*Active)' # Status
        , re.IGNORECASE | re.DOTALL)


        # This pattern is specifically for the PF content that comes in a more structured, almost CSV-like format
        # where fields are sometimes separated by '",\"'
        pf_pattern_csv_like = re.compile(
            r'\"(\d{2}/\d{4}|[A-Za-z]{3}-\d{4})\s*[-–]?\s*(\d{2}/\d{4}|[A-Za-z]{3}-\d{4}|Present)\"\s*,\s*' # Period
            r'\"?([A-Za-z\s&,.-]+)\"?\s*,\s*' # Employer Name
            r'\"?([A-Z]{2}\d{7,11})\"?\s*,\s*' # Establishment ID
            r'\"?([\d,]+)\"?\s*,\s*' # Employee Contribution
            r'\"?([\d,]+)\"?\s*,\s*' # Employer Contribution
            r'\"?([\d,]+)\"?\s*,\s*' # Pension Contribution
            r'\"?(Active\s*\(Closed\)|\s*Missing|\s*Active)\"?' # Status
        )

        matches_csv = pf_pattern_csv_like.findall(pf_text)
        for match in matches_csv:
            if len(match) >= 7:
                start_date = self.convert_date_format(match[0].strip())
                end_date = self.convert_date_format(match[1].strip()) if match[1].strip().lower() != 'present' else 'Present'
                
                result["employment_records"].append({
                    "period": f"{match[0].strip()} - {match[1].strip()}",
                    "start_date": start_date,
                    "end_date": end_date,
                    "employer_name": match[2].replace('\n', ' ').strip(),
                    "establishment_id": match[3].strip(),
                    "employee_contribution": self.parse_amount(match[4]),
                    "employer_contribution": self.parse_amount(match[5]),
                    "pension_contribution": self.parse_amount(match[6]),
                    "status": match[7].strip()
                })
                
        if not result["employment_records"]: # Fallback if CSV-like pattern doesn't match
            matches = pf_pattern.findall(pf_text)
            for match in matches:
                if len(match) >= 7:
                    start_date = self.convert_date_format(match[0].strip())
                    end_date = self.convert_date_format(match[1].strip()) if match[1].strip().lower() != 'present' else 'Present'
                    
                    result["employment_records"].append({
                        "period": f"{match[0].strip()} - {match[1].strip()}",
                        "start_date": start_date,
                        "end_date": end_date,
                        "employer_name": match[2].replace('\n', ' ').strip(),
                        "establishment_id": match[3].strip(),
                        "employee_contribution": self.parse_amount(match[4]),
                        "employer_contribution": self.parse_amount(match[5]),
                        "pension_contribution": self.parse_amount(match[6]),
                        "status": match[7].strip()
                    })

        return result
    
    def convert_date_format(self, date_str: str) -> str:
        """Convert MM/YYYY or Mon-YYYY to YYYY-MM format"""
        try:
            if re.match(r'\d{2}/\d{4}', date_str): # MM/YYYY format
                month, year = date_str.split('/')
                return f"{year}-{month.zfill(2)}"
            elif re.match(r'[A-Za-z]{3}-\d{4}', date_str): # Mon-YYYY format
                dt_obj = datetime.strptime(date_str, '%b-%Y')
                return dt_obj.strftime('%Y-%m')
            return date_str
        except:
            return date_str
    
    def parse_amount(self, amount_str: str) -> float:
        """Parse amount string to float"""
        try:
            # Remove commas and convert to float
            return float(amount_str.replace(',', ''))
        except:
            return 0.0