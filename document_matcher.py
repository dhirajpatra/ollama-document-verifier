import ollama
import os
import json
from typing import Dict, List
from data_extractor import DocumentExtractor # Changed import to data_extractor
from dateutil.parser import parse
from datetime import datetime
from fuzzywuzzy import fuzz # Added for fuzzy matching


class DocumentMatcher:
    def __init__(self):
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.model = 'gemma:2b'
        self.extractor = DocumentExtractor() # Initialize the extractor here
    
    def verify_documents(self, cv_text: str, pf_text: str) -> Dict:
        """Main verification function"""
        try:
            # Extract structured information using the new DocumentExtractor
            cv_info = self.extractor.extract_cv_data(cv_text)
            pf_info = self.extractor.extract_pf_data(pf_text)
            
            # Perform static (Step 1) matching
            matches = self.match_employment_records(cv_info, pf_info)
            
            # Get AI (Step 2) analysis
            ai_analysis = self.get_ai_analysis(cv_text, pf_text)
            
            # Determine overall match based on static matches
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
                'ai_analysis': f"Error during verification: {str(e)}"
            }

    def match_employment_records(self, cv_info: Dict, pf_info: Dict) -> List[Dict]:
        """Match employment records between CV and PF information."""
        matches = []
        cv_employment = cv_info.get('employment_history', [])
        pf_employment = pf_info.get('employment_records', [])

        matched_pf_indices = set()

        for cv_entry in cv_employment:
            cv_company = cv_entry.get('company', '').lower()
            cv_start_date = cv_entry.get('start_date')
            cv_end_date = cv_entry.get('end_date')

            found_match = False
            for i, pf_entry in enumerate(pf_employment):
                if i in matched_pf_indices:
                    continue

                pf_company = pf_entry.get('employer_name', '').lower()
                pf_start_date = pf_entry.get('start_date')
                pf_end_date = pf_entry.get('end_date')

                company_match_score = fuzz.ratio(cv_company, pf_company)

                # Consider a match if company names are very similar and dates overlap
                if company_match_score > 80 and self._check_date_overlap(cv_start_date, cv_end_date, pf_start_date, pf_end_date):
                    matches.append({
                        'employer': cv_entry.get('company'),
                        'period': f"{cv_start_date} - {cv_end_date}",
                        'status': 'matched',
                        'match_score': company_match_score,
                        'cv_entry': cv_entry,
                        'pf_entry': pf_entry
                    })
                    matched_pf_indices.add(i)
                    found_match = True
                    break
            
            if not found_match:
                matches.append({
                    'employer': cv_entry.get('company'),
                    'period': f"{cv_start_date} - {cv_end_date}",
                    'status': 'no PF entry found',
                    'issue': 'No matching PF entry found or significant discrepancy in company/dates',
                    'cv_entry': cv_entry,
                    'pf_entry': None
                })
        
        # Add PF entries that were not matched by any CV entry
        for i, pf_entry in enumerate(pf_employment):
            if i not in matched_pf_indices:
                matches.append({
                    'employer': pf_entry.get('employer_name'),
                    'period': f"{pf_entry.get('start_date')} - {pf_entry.get('end_date')}",
                    'status': 'no CV entry found',
                    'issue': 'PF entry exists without a matching CV entry',
                    'cv_entry': None,
                    'pf_entry': pf_entry
                })

        return matches

    def _check_date_overlap(self, cv_start_str: str, cv_end_str: str, pf_start_str: str, pf_end_str: str) -> bool:
        """Check for overlap between two date ranges (YYYY-MM format)."""
        try:
            # Handle 'Present' by using the current year (or a future placeholder)
            current_year = datetime.now().year
            
            cv_start = parse(cv_start_str)
            cv_end = parse(cv_end_str) if cv_end_str.lower() != 'present' else datetime(current_year, 12, 31)

            pf_start = parse(pf_start_str)
            pf_end = parse(pf_end_str) if pf_end_str.lower() != 'present' else datetime(current_year, 12, 31)

            # Check for overlap: (start1 <= end2) and (start2 <= end1)
            return (cv_start <= pf_end) and (pf_start <= cv_end)
        except Exception as e:
            print(f"Date parsing error: {e}")
            return False
    
    def get_ai_analysis(self, cv_full_text: str, pf_full_text: str) -> str:
        """Get AI analysis using Ollama for semantic comparison."""
        try:
            prompt = f"""
            You are a document verification expert. Analyze the following CV and PF (Provident Fund) documents. Focus specifically on comparing the employment history details provided in both documents to identify matches, mismatches, and any discrepancies.

            CV Content (Employment History and related sections):
            {cv_full_text}

            PF Content (Employment and Contribution History and related sections):
            {pf_full_text}

            Please provide a detailed analysis covering:
            1.  **Employment Periods Comparison:** Compare the start and end dates of each employment period mentioned in the CV with corresponding entries in the PF document.
            2.  **Company Name Matching:** Verify if company names are consistent across both documents, considering minor variations.
            3.  **Discrepancies Found:** List all specific mismatches or missing information (e.g., periods in CV not found in PF, periods in PF not found in CV, different company names for the same period, significant date differences).
            4.  **Overall Verification Result:** State whether the employment history largely matches, has minor discrepancies, or has significant mismatches.
            5.  **Recommendations:** Suggest what steps could be taken to reconcile any discrepancies.

            Respond in a clear, professional, and structured manner, ensuring you address all five points.
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