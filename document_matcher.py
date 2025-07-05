import ollama
import os
import json
from typing import Dict, List
from pdf_extractor import extract_cv_info, extract_pf_info
from dateutil.parser import parse
from datetime import datetime

class DocumentMatcher:
    def __init__(self):
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.model = 'gemma:2b'
    
    def verify_documents(self, cv_text: str, pf_text: str) -> Dict:
        """Main verification function"""
        try:
            # Extract structured information
            cv_info = extract_cv_info(cv_text)
            pf_info = extract_pf_info(pf_text)
            
            # Perform matching
            matches = self.match_employment_records(cv_info, pf_info)
            
            # Get AI analysis
            ai_analysis = self.get_ai_analysis(cv_text, pf_text)
            
            # Determine overall match
            overall_match = all(match['status'] == 'matched' for match in matches)
            
            return {
                'overall_match': overall_match,
                'cv_info': cv_info,
                'pf_info': pf_info,
                'matches': matches,
                'ai_analysis': ai_analysis
            }
            
        except Exception as e:
            return {
                'overall_match': False,
                'error': str(e),
                'cv_info': {},
                'pf_info': {},
                'matches': [],
                'ai_analysis': f"Error in analysis: {str(e)}"
            }
    
    def match_employment_records(self, cv_info: Dict, pf_info: Dict) -> List[Dict]:
        """Match employment records between CV and PF"""
        matches = []
        
        cv_employment = cv_info.get('employment_history', [])
        pf_entries = pf_info.get('pf_entries', [])
        
        for cv_job in cv_employment:
            match_found = False
            
            for pf_entry in pf_entries:
                if self.is_employer_match(cv_job['company'], pf_entry['employer']):
                    if self.is_period_overlap(cv_job, pf_entry):
                        matches.append({
                            'employer': cv_job['company'],
                            'period': cv_job['period'],
                            'status': 'matched',
                            'cv_data': cv_job,
                            'pf_data': pf_entry
                        })
                        match_found = True
                        break
            
            if not match_found:
                matches.append({
                    'employer': cv_job['company'],
                    'period': cv_job['period'],
                    'status': 'no_match',
                    'issue': 'No corresponding PF entry found',
                    'cv_data': cv_job,
                    'pf_data': None
                })
        
        return matches
    
    def is_employer_match(self, cv_employer: str, pf_employer: str) -> bool:
        """Check if employer names match (fuzzy matching)"""
        cv_clean = cv_employer.lower().replace(' ', '').replace(',', '').replace('.', '')
        pf_clean = pf_employer.lower().replace(' ', '').replace(',', '').replace('.', '')
        
        # Check for partial matches
        return cv_clean in pf_clean or pf_clean in cv_clean or \
               any(word in pf_clean for word in cv_clean.split() if len(word) > 3)
    
    def is_period_overlap(self, cv_job: Dict, pf_entry: Dict) -> bool:
        """Check if employment periods overlap"""
        try:
            cv_start = int(cv_job['start_year'])
            cv_end = int(cv_job['end_year']) if cv_job['end_year'] != 'Present' else 2025
            
            pf_start = int(pf_entry['start_period'].split('/')[1])
            pf_end = int(pf_entry['end_period'].split('/')[1]) if pf_entry['end_period'] != 'Present' else 2025
            
            # Check for overlap
            return not (cv_end < pf_start or pf_end < cv_start)
            
        except (ValueError, IndexError):
            return False
    
    def get_ai_analysis(self, cv_text: str, pf_text: str) -> str:
        """Get AI analysis using Ollama"""
        try:
            prompt = f"""
            You are a document verification expert. Analyze the following CV and PF (Provident Fund) documents to verify if the employment history matches.

            CV Content:
            {cv_text[:2000]}

            PF Content:
            {pf_text[:2000]}

            Please provide a detailed analysis covering:
            1. Employment periods comparison
            2. Company name matching
            3. Any discrepancies found
            4. Overall verification result
            5. Recommendations

            Respond in a clear, professional manner.
            """
            
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={
                    'temperature': 0.3,
                    'num_ctx': 4096
                }
            )
            
            return response['response']
            
        except Exception as e:
            return f"AI analysis unavailable: {str(e)}"