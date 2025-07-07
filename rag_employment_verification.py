# rag_employment_verification.py
import os
import json
import PyPDF2
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
import requests
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import re

class EmploymentRAGVerifier:
    def __init__(self, ollama_host: str = "http://ollama:11434"):
        self.ollama_host = ollama_host
        self.model = SentenceTransformer('all-MiniLM-L6-v2')  # Lightweight embedding model
        self.employment_data = {
            'cv_employment': [],
            'epf_employment': []
        }
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()
                return text
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {e}")
            return ""
    
    def parse_cv_employment(self, cv_text: str) -> List[Dict[str, Any]]:
        """Parse employment history from CV text"""
        employment_records = []
        
        # Look for employment section patterns
        employment_section = re.search(r'Professional Experience(.*?)(?=Education|Certifications|Projects|$)', 
                                     cv_text, re.DOTALL | re.IGNORECASE)
        
        if employment_section:
            employment_text = employment_section.group(1)
            
            # Pattern to match job entries
            job_pattern = r'([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*(?:–|-)?\s*([^|]*)'
            
            # Split by lines and process each potential job entry
            lines = employment_text.split('\n')
            current_job = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Check if line contains company and date pattern
                if '|' in line and any(month in line for month in ['01/', '02/', '03/', '04/', '05/', '06/', 
                                                                  '07/', '08/', '09/', '10/', '11/', '12/', 
                                                                  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                                                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                    parts = line.split('|')
                    if len(parts) >= 3:
                        company = parts[1].strip()
                        date_range = parts[2].strip()
                        
                        # Extract start and end dates
                        start_date, end_date = self.parse_date_range(date_range)
                        
                        employment_records.append({
                            'company': company,
                            'start_date': start_date,
                            'end_date': end_date,
                            'date_range': date_range,
                            'source': 'CV'
                        })
                        
                # Also check for company names directly mentioned in the text
                elif any(company in line for company in ['ABC Tech Solutions', 'XYZ Software']):
                    # Extract company name and try to find associated dates
                    for company in ['ABC Tech Solutions', 'XYZ Software']:
                        if company in line:
                            # Look for dates in nearby lines
                            date_pattern = r'(\d{2}/\d{4})\s*(?:–|-)?\s*(\d{2}/\d{4}|Present)'
                            date_match = re.search(date_pattern, line)
                            if date_match:
                                start_date = self.parse_date(date_match.group(1))
                                end_date = self.parse_date(date_match.group(2)) if date_match.group(2) != 'Present' else None
                                
                                employment_records.append({
                                    'company': company,
                                    'start_date': start_date,
                                    'end_date': end_date,
                                    'date_range': f"{date_match.group(1)} - {date_match.group(2)}",
                                    'source': 'CV'
                                })
        
        return employment_records
    
    def parse_epf_employment(self, epf_text: str) -> List[Dict[str, Any]]:
        """Parse employment history from EPF statement"""
        employment_records = []
        
        # Look for the employment table
        lines = epf_text.split('\n')
        current_company = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for month-year pattern (EPF records)
            month_year_pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-(\d{4})'
            month_match = re.search(month_year_pattern, line)
            
            if month_match:
                month = month_match.group(1)
                year = month_match.group(2)
                
                # Extract company name from the line
                company_match = re.search(r'(XYZ Software|ABC Tech Solutions)', line)
                if company_match:
                    company = company_match.group(1)
                    
                    # Parse contribution amounts
                    amount_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
                    amounts = re.findall(amount_pattern, line)
                    
                    if amounts:
                        employee_contribution = amounts[0].replace(',', '') if len(amounts) > 0 else '0'
                        employer_contribution = amounts[1].replace(',', '') if len(amounts) > 1 else '0'
                        pension = amounts[2].replace(',', '') if len(amounts) > 2 else '0'
                        
                        employment_records.append({
                            'company': company,
                            'month': month,
                            'year': year,
                            'date': f"{month}-{year}",
                            'employee_contribution': employee_contribution,
                            'employer_contribution': employer_contribution,
                            'pension': pension,
                            'source': 'EPF'
                        })
        
        return employment_records
    
    def parse_date_range(self, date_range: str) -> tuple:
        """Parse date range string to extract start and end dates"""
        # Handle various date formats
        date_range = date_range.replace('–', '-').replace('—', '-')
        
        if '-' in date_range:
            parts = date_range.split('-')
            start_date = self.parse_date(parts[0].strip())
            end_date = self.parse_date(parts[1].strip()) if len(parts) > 1 and parts[1].strip() != 'Present' else None
        else:
            start_date = self.parse_date(date_range.strip())
            end_date = None
            
        return start_date, end_date
    
    def parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object"""
        date_str = date_str.strip()
        
        # Handle different date formats
        formats = [
            '%m/%Y',  # 03/2021
            '%m-%Y',  # 03-2021
            '%b/%Y',  # Mar/2021
            '%b-%Y',  # Mar-2021
            '%B %Y',  # March 2021
            '%Y-%m',  # 2021-03
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
                
        # If no format matches, try to extract year at least
        year_match = re.search(r'(\d{4})', date_str)
        if year_match:
            return datetime(int(year_match.group(1)), 1, 1)
            
        return None
    
    def create_embeddings(self, employment_records: List[Dict[str, Any]]) -> List[np.ndarray]:
        """Create embeddings for employment records"""
        embeddings = []
        
        for record in employment_records:
            # Create text representation of the employment record
            if record['source'] == 'CV':
                text = f"Company: {record['company']}, Start: {record['start_date']}, End: {record['end_date']}, Duration: {record['date_range']}"
            else:  # EPF
                text = f"Company: {record['company']}, Month: {record['month']}, Year: {record['year']}, Contribution: {record['employee_contribution']}"
            
            # Generate embedding
            embedding = self.model.encode(text)
            embeddings.append(embedding)
            
        return embeddings
    
    def find_similar_employment(self, cv_records: List[Dict[str, Any]], epf_records: List[Dict[str, Any]], 
                               threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Find similar employment records between CV and EPF using semantic similarity"""
        
        if not cv_records or not epf_records:
            return []
        
        # Create embeddings
        cv_embeddings = self.create_embeddings(cv_records)
        epf_embeddings = self.create_embeddings(epf_records)
        
        matches = []
        
        # Compare each CV record with each EPF record
        for i, cv_record in enumerate(cv_records):
            for j, epf_record in enumerate(epf_records):
                # Calculate cosine similarity
                similarity = cosine_similarity([cv_embeddings[i]], [epf_embeddings[j]])[0][0]
                
                if similarity >= threshold:
                    matches.append({
                        'cv_record': cv_record,
                        'epf_record': epf_record,
                        'similarity_score': float(similarity),
                        'match_type': 'semantic'
                    })
        
        return matches
    
    def verify_employment_with_llm(self, cv_record: Dict[str, Any], epf_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use LLM to verify employment details"""
        
        # Prepare context for LLM
        cv_context = f"CV Employment: Company: {cv_record['company']}, Duration: {cv_record['date_range']}"
        epf_context = "EPF Records:\n" + "\n".join([
            f"- {record['company']} ({record['month']} {record['year']}): ₹{record['employee_contribution']}"
            for record in epf_records
        ])
        
        prompt = f"""
        You are an employment verification expert. Please analyze the following employment records:

        {cv_context}

        {epf_context}

        Please provide:
        1. Verification status (VERIFIED/PARTIALLY_VERIFIED/NOT_VERIFIED)
        2. Confidence score (0-100)
        3. Discrepancies found (if any)
        4. Summary of findings

        Respond in JSON format.
        """
        
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": "llama3.2",  # or whatever model you have
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'llm_response': result.get('response', ''),
                    'verification_method': 'LLM'
                }
        except Exception as e:
            print(f"Error calling LLM: {e}")
            
        return {
            'llm_response': 'Error calling LLM',
            'verification_method': 'LLM'
        }
    
    def process_documents(self, cv_path: str, epf_path: str) -> Dict[str, Any]:
        """Main function to process both documents and perform verification"""
        
        # Extract text from PDFs
        cv_text = self.extract_text_from_pdf(cv_path)
        epf_text = self.extract_text_from_pdf(epf_path)
        
        # Parse employment records
        cv_records = self.parse_cv_employment(cv_text)
        epf_records = self.parse_epf_employment(epf_text)
        
        # Find similar employment records
        matches = self.find_similar_employment(cv_records, epf_records)
        
        # Prepare verification results
        verification_results = {
            'cv_employment_count': len(cv_records),
            'epf_employment_count': len(epf_records),
            'matches_found': len(matches),
            'cv_records': cv_records,
            'epf_records': epf_records,
            'matches': matches,
            'verification_summary': self.generate_verification_summary(cv_records, epf_records, matches)
        }
        
        return verification_results
    
    def generate_verification_summary(self, cv_records: List[Dict[str, Any]], 
                                    epf_records: List[Dict[str, Any]], 
                                    matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary of verification results"""
        
        total_cv_companies = len(set(record['company'] for record in cv_records))
        total_epf_companies = len(set(record['company'] for record in epf_records))
        
        verified_companies = len(set(match['cv_record']['company'] for match in matches))
        
        verification_percentage = (verified_companies / total_cv_companies * 100) if total_cv_companies > 0 else 0
        
        return {
            'total_cv_companies': total_cv_companies,
            'total_epf_companies': total_epf_companies,
            'verified_companies': verified_companies,
            'verification_percentage': round(verification_percentage, 2),
            'status': 'VERIFIED' if verification_percentage >= 80 else 'PARTIALLY_VERIFIED' if verification_percentage >= 50 else 'NOT_VERIFIED'
        }

# Example usage
if __name__ == "__main__":
    verifier = EmploymentRAGVerifier()
    
    # Process documents
    results = verifier.process_documents('uploads/cv.pdf', 'uploads/EPF_Statement.pdf')
    
    # Save results
    with open('output/verification_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("Verification completed. Results saved to output/verification_results.json")