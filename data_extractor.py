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
    
    def extract_cv_data(self, cv_path: str) -> Dict:
        """Extract structured data from CV PDF"""
        text = self.extract_text_from_pdf(cv_path)
        
        if not text:
            return {}
        
        # Use AI to extract structured data
        prompt = f"""
        Extract the following information from this CV text and return as JSON:
        
        1. Personal Information (name, email, phone, location)
        2. Employment History (company, position, start_date, end_date, location)
        3. Skills (technical skills list)
        4. Education (degree, university, year)
        
        CV Text:
        {text}
        
        Return only valid JSON with the structure:
        {{
            "personal_info": {{
                "name": "string",
                "email": "string", 
                "phone": "string",
                "location": "string"
            }},
            "employment_history": [
                {{
                    "company": "string",
                    "position": "string",
                    "start_date": "YYYY-MM or YYYY",
                    "end_date": "YYYY-MM or YYYY or Present",
                    "location": "string"
                }}
            ],
            "skills": ["skill1", "skill2"],
            "education": [
                {{
                    "degree": "string",
                    "university": "string",
                    "year": "YYYY"
                }}
            ]
        }}
        """
        
        try:
            response = self.call_ollama(prompt)
            return json.loads(response)
        except Exception as e:
            print(f"Error extracting CV data: {e}")
            return self.extract_cv_data_fallback(text)
    
    def extract_pf_data(self, pf_path: str) -> Dict:
        """Extract structured data from PF PDF"""
        text = self.extract_text_from_pdf(pf_path)
        
        if not text:
            return {}
        
        # Use AI to extract structured data
        prompt = f"""
        Extract the following information from this PF statement text and return as JSON:
        
        1. Account Information (UAN, PF Account Number, Name)
        2. Employment Records (period, employer_name, establishment_id, contributions, status)
        
        PF Statement Text:
        {text}
        
        Return only valid JSON with the structure:
        {{
            "account_info": {{
                "name": "string",
                "uan": "string",
                "pf_account_number": "string",
                "date_generated": "string"
            }},
            "employment_records": [
                {{
                    "period": "MM/YYYY - MM/YYYY",
                    "start_date": "YYYY-MM",
                    "end_date": "YYYY-MM or Present",
                    "employer_name": "string",
                    "establishment_id": "string",
                    "employee_contribution": "number",
                    "employer_contribution": "number",
                    "pension_contribution": "number",
                    "status": "string"
                }}
            ]
        }}
        """
        
        try:
            response = self.call_ollama(prompt)
            return json.loads(response)
        except Exception as e:
            print(f"Error extracting PF data: {e}")
            return self.extract_pf_data_fallback(text)
    
    def call_ollama(self, prompt: str) -> str:
        """Make API call to Ollama"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "gemma:2b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9
                    }
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            raise
    
    def extract_cv_data_fallback(self, text: str) -> Dict:
        """Fallback method for CV extraction using regex"""
        result = {
            "personal_info": {},
            "employment_history": [],
            "skills": [],
            "education": []
        }
        
        # Extract name (first line usually)
        lines = text.split('\n')
        if lines:
            result["personal_info"]["name"] = lines[0].strip()
        
        # Extract email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            result["personal_info"]["email"] = email_match.group()
        
        # Extract phone
        phone_match = re.search(r'[\+]?[1-9]?[0-9]{7,15}', text)
        if phone_match:
            result["personal_info"]["phone"] = phone_match.group()
        
        # Extract employment history (basic pattern)
        job_patterns = [
            r'([A-Za-z\s]+)\n([A-Za-z\s,]+)\s*\|\s*(\d{4})\s*[–-]\s*(\d{4}|Present)',
            r'([A-Za-z\s]+)\n([A-Za-z\s,]+),\s*([A-Za-z\s]+)\s*\|\s*(\d{4})\s*[–-]\s*(\d{4}|Present)'
        ]
        
        for pattern in job_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                if len(match) >= 4:
                    result["employment_history"].append({
                        "position": match[0].strip(),
                        "company": match[1].strip(),
                        "start_date": match[2] if len(match) > 2 else "",
                        "end_date": match[3] if len(match) > 3 else "",
                        "location": match[4] if len(match) > 4 else ""
                    })
        
        # Extract skills (look for common sections)
        skills_section = re.search(r'(?:Skills|Technical Skills|Technologies)[:\s]*\n(.*?)(?:\n\n|\n---|\nExperience)', text, re.DOTALL | re.IGNORECASE)
        if skills_section:
            skills_text = skills_section.group(1)
            # Extract skills from bullet points or comma-separated
            skills = re.findall(r'[-•]\s*([^-•\n]+)', skills_text)
            if not skills:
                skills = [skill.strip() for skill in skills_text.split(',')]
            result["skills"] = [skill.strip() for skill in skills if skill.strip()]
        
        return result
    
    def extract_pf_data_fallback(self, text: str) -> Dict:
        """Fallback method for PF extraction using regex"""
        result = {
            "account_info": {},
            "employment_records": []
        }
        
        # Extract UAN
        uan_match = re.search(r'UAN[:\s]*(\d+)', text)
        if uan_match:
            result["account_info"]["uan"] = uan_match.group(1)
        
        # Extract PF Account Number
        pf_match = re.search(r'PF Account Number[:\s]*([A-Z0-9/]+)', text)
        if pf_match:
            result["account_info"]["pf_account_number"] = pf_match.group(1)
        
        # Extract Name
        name_match = re.search(r'Name[:\s]*([A-Za-z\s]+)', text)
        if name_match:
            result["account_info"]["name"] = name_match.group(1).strip()
        
        # Extract employment records
        # Pattern for employment records
        employment_pattern = r'(\d{2}/\d{4})\s*[–-]\s*(\d{2}/\d{4}|Present)\s+([A-Za-z\s&.,]+)\s+([A-Z0-9]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+(\w+)'
        
        matches = re.findall(employment_pattern, text)
        for match in matches:
            if len(match) >= 8:
                # Convert MM/YYYY to YYYY-MM format
                start_date = self.convert_date_format(match[0])
                end_date = self.convert_date_format(match[1]) if match[1] != 'Present' else 'Present'
                
                result["employment_records"].append({
                    "period": f"{match[0]} - {match[1]}",
                    "start_date": start_date,
                    "end_date": end_date,
                    "employer_name": match[2].strip(),
                    "establishment_id": match[3].strip(),
                    "employee_contribution": self.parse_amount(match[4]),
                    "employer_contribution": self.parse_amount(match[5]),
                    "pension_contribution": self.parse_amount(match[6]),
                    "status": match[7].strip()
                })
        
        return result
    
    def convert_date_format(self, date_str: str) -> str:
        """Convert MM/YYYY to YYYY-MM format"""
        try:
            if '/' in date_str:
                month, year = date_str.split('/')
                return f"{year}-{month.zfill(2)}"
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