import PyPDF2
import re
from typing import Dict, List

def extract_pdf_text(pdf_path: str) -> str:
    """Extract text from PDF file"""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        raise Exception(f"Error reading PDF: {str(e)}")
    
    return text

def extract_cv_info(cv_text: str) -> Dict:
    """Extract employment information from CV"""
    employment_info = []
    
    # Pattern to match employment entries
    employment_pattern = r'([A-Za-z\s&,.-]+)\s*\n?([A-Za-z\s,.-]+)\s*\|\s*(\d{4})\s*[-–]\s*(\d{4}|Present)'
    
    matches = re.findall(employment_pattern, cv_text, re.MULTILINE | re.DOTALL)
    
    for match in matches:
        position = match[0].strip()
        company = match[1].strip()
        start_year = match[2].strip()
        end_year = match[3].strip()
        
        employment_info.append({
            'position': position,
            'company': company,
            'start_year': start_year,
            'end_year': end_year,
            'period': f"{start_year}-{end_year}"
        })
    
    return {
        'employment_history': employment_info,
        'total_positions': len(employment_info)
    }

def extract_pf_info(pf_text: str) -> Dict:
    """Extract PF contribution information"""
    pf_entries = []
    
    # Pattern to match PF entries
    pf_pattern = r'(\d{2}/\d{4})\s*[-–]\s*(\d{2}/\d{4}|Present)\s+([A-Za-z\s&,.-]+)\s+([A-Z]{2}\d+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+(Active|Closed|Missing)'
    
    matches = re.findall(pf_pattern, pf_text, re.MULTILINE)
    
    for match in matches:
        start_period = match[0].strip()
        end_period = match[1].strip()
        employer = match[2].strip()
        establishment_id = match[3].strip()
        emp_contribution = match[4].strip()
        employer_contribution = match[5].strip()
        pension = match[6].strip()
        status = match[7].strip()
        
        pf_entries.append({
            'start_period': start_period,
            'end_period': end_period,
            'employer': employer,
            'establishment_id': establishment_id,
            'employee_contribution': emp_contribution,
            'employer_contribution': employer_contribution,
            'pension': pension,
            'status': status,
            'period': f"{start_period}-{end_period}"
        })
    
    return {
        'pf_entries': pf_entries,
        'total_entries': len(pf_entries)
    }