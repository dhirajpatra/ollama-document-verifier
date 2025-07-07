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
                    extracted_page_text = page.extract_text()
                    if extracted_page_text:
                        text += extracted_page_text + "\n" # Add newline for better separation
                return text
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {e}")
            return "" # Ensure an empty string is returned on error
    
    def parse_cv_employment(self, cv_text: str) -> List[Dict[str, Any]]:
        """Parse employment history from CV text"""
        employment_records = []
        if not cv_text: # Handle empty input
            print("CV text is empty, cannot parse employment.")
            return employment_records
            
        # Look for employment section patterns (made more flexible)
        # This regex tries to capture content that could be an employment section
        # It looks for common headers like "Experience", "Employment History", "Professional Experience"
        # and tries to capture content until another major section or end of document.
        employment_section_match = re.search(
            r'(?:Professional Experience|Employment History|Work Experience)\s*\n*(.*?)(?=\n\n(?:Education|Certifications|Projects|Skills|Awards|Personal Details|$))', 
            cv_text, 
            re.DOTALL | re.IGNORECASE
        )
        
        employment_text = ""
        if employment_section_match:
            employment_text = employment_section_match.group(1)
        else:
            # Fallback: if no specific section found, try to parse the whole text, but less reliably
            employment_text = cv_text
            
        if not employment_text:
            print("No employment section found in CV text.")
            return employment_records

        # Refined pattern to match job entries. More flexible for various CV formats.
        # It looks for:
        # Company Name: Often on its own line or at the start of a block.
        # Date Range: (e.g., "MM/YYYY - MM/YYYY", "Month XXXX – Present", "YYYY – YYYY")
        # Role: Often before or after the company.
        # This pattern is a bit more generic and might require post-processing.
        # It prioritizes company and date range as key identifiers.

        # Regex to find potential job blocks. It looks for a sequence of lines that
        # typically represent a job entry (company, title, dates, responsibilities).
        # We will iterate through these blocks and then extract details.
        
        # This is a general pattern that tries to capture a block that starts with a potential company name
        # followed by dates. This is highly heuristic.
        job_block_pattern = re.compile(
            r'([A-Za-z0-9\s&,.-]+?)\s*\n+'  # Company Name (potentially multi-line if job title is below it)
            r'(?:[A-Za-z0-9\s&,.-]+?\s*\n+)?' # Optional Job Title line
            r'((?:\d{1,2}/\d{4}|\d{4}|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*(?:-|–|to)\s*(?:\d{1,2}/\d{4}|\d{4}|Present|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))\s*', # Date Range
            re.IGNORECASE | re.DOTALL
        )
        
        # Split the employment text into potential blocks or lines for easier parsing
        lines = employment_text.split('\n')
        
        current_company = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # Attempt to find company and date range in the current line or subsequent lines
            # This is a simplified approach, a more robust parser might use NLP or more complex regex
            
            # Pattern for "Company Name | StartDate - EndDate" or "Company Name, Location | Dates"
            company_date_pattern_1 = re.search(r'([A-Za-z\s&,.-]+)\s*\|\s*(\d{1,2}/\d{4}|\d{4}|[A-Za-z]{3,}\s*\d{4})\s*(?:-|–|to)\s*(\d{1,2}/\d{4}|\d{4}|Present|[A-Za-z]{3,}\s*\d{4})', line, re.IGNORECASE)
            if company_date_pattern_1:
                company = company_date_pattern_1.group(1).strip()
                start_date_str = company_date_pattern_1.group(2).strip()
                end_date_str = company_date_pattern_1.group(3).strip()
                
                start_date, end_date = self.parse_date_range(f"{start_date_str} - {end_date_str}")
                
                employment_records.append({
                    'company': company,
                    'start_date': start_date,
                    'end_date': end_date,
                    'date_range': f"{start_date_str} - {end_date_str}",
                    'source': 'CV'
                })
                continue # Move to next line

            # Pattern for "Company Name" often on its own line, followed by "Start Date - End Date" on subsequent line
            # This is more heuristic and less precise, relying on line proximity.
            
            # Heuristic check for potential company line (e.g., all caps, common company suffixes)
            if re.search(r'^[A-Z0-9\s.,&()-]+(LLC|INC|LTD|PVT|CORP|SOLUTIONS|TECHNOLOGIES|SYSTEMS|GLOBAL)\.?$', line, re.IGNORECASE) or \
               (line.isupper() and len(line) > 3) or \
               (re.match(r'^[A-Z][a-zA-Z\s]*$', line) and i+1 < len(lines) and re.search(r'(\d{1,2}/\d{4}|\d{4}|[A-Za-z]{3,}\s*\d{4})\s*(?:-|–|to)\s*(\d{1,2}/\d{4}|\d{4}|Present|[A-Za-z]{3,}\s*\d{4})', lines[i+1])):
                
                current_company = line.strip()
                # Look for dates in the next few lines
                for j in range(i + 1, min(i + 4, len(lines))):
                    next_line = lines[j].strip()
                    date_match = re.search(r'(\d{1,2}/\d{4}|\d{4}|[A-Za-z]{3,}\s*\d{4})\s*(?:-|–|to)\s*(\d{1,2}/\d{4}|\d{4}|Present|[A-Za-z]{3,}\s*\d{4})', next_line, re.IGNORECASE)
                    if date_match:
                        start_date_str = date_match.group(1).strip()
                        end_date_str = date_match.group(2).strip()
                        
                        start_date, end_date = self.parse_date_range(f"{start_date_str} - {end_date_str}")
                        
                        if current_company:
                            employment_records.append({
                                'company': current_company,
                                'start_date': start_date,
                                'end_date': end_date,
                                'date_range': f"{start_date_str} - {end_date_str}",
                                'source': 'CV'
                            })
                            current_company = None # Reset for next entry
                            break # Found dates for this company
        
        return employment_records
    
    def parse_epf_employment(self, epf_text: str) -> List[Dict[str, Any]]:
        """Parse employment history from EPF statement"""
        employment_records = []
        if not epf_text: # Handle empty input
            print("EPF text is empty, cannot parse employment.")
            return employment_records

        lines = epf_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # EPF statement often has structured data, or repeating patterns.
            # Look for lines that contain a period (e.g., "MM/YYYY - MM/YYYY" or "Month-Year")
            # and then try to find company and contribution details in the same or nearby lines.

            # Pattern for a full EPF record line, assuming comma or pipe separated values, or fixed width.
            # Example from pdf_extractor.py: "03/2021 – Present","ABC Tech Solutions","E12345","132500","15000","5000","Active"
            # Use re.findall for quoted fields as in pdf_extractor.py
            quoted_fields = re.findall(r'"([^"]*?)"', line, re.DOTALL)

            if len(quoted_fields) >= 7: # Assuming the structure from pdf_extractor.py for EPF
                try:
                    period_raw = quoted_fields[0].replace('\n', ' ').strip()
                    employer = quoted_fields[1].replace('\n', ' ').strip()
                    # establishment_id = quoted_fields[2].replace('\n', ' ').strip() # Not directly used for matching, but can keep
                    employee_contribution = quoted_fields[3].replace('\n', ' ').strip()
                    employer_contribution = quoted_fields[4].replace('\n', ' ').strip()
                    pension = quoted_fields[5].replace('\n', ' ').strip()
                    # status = quoted_fields[6].replace('\n', ' ').strip() # Not directly used for matching, but can keep

                    start_date, end_date = self.parse_date_range(period_raw)
                    
                    # EPF records are typically monthly, so for verification we might need to aggregate
                    # or treat each monthly entry as a distinct record associated with a company.
                    # For simplicity, if a company appears across many months, we'll just record each entry.
                    employment_records.append({
                        'company': employer,
                        'start_date': start_date, 
                        'end_date': end_date,     
                        'date_range': period_raw,
                        'employee_contribution': employee_contribution,
                        'employer_contribution': employer_contribution,
                        'pension': pension,
                        'source': 'EPF'
                    })
                except Exception as e:
                    print(f"Error parsing EPF line (skipping): {line} - Error: {str(e)}")
                    continue
            else:
                # Fallback for less structured EPF data: Look for month-year and company
                month_year_pattern = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*-\s*(\d{4})' # e.g., "Jan - 2023"
                month_match = re.search(month_year_pattern, line, re.IGNORECASE)
                
                if month_match:
                    month_year_str = month_match.group(0).strip() # Get the full month-year string
                    
                    # Extract company name from the line (can be made more specific)
                    # This pattern is highly generalized and might need refinement based on actual EPF formats.
                    company_match = re.search(r'([A-Za-z\s&,.-]+? (?:Pvt|Ltd|Inc|LLC|Corp)\.?)\s*', line, re.IGNORECASE)
                    if not company_match:
                         # A more general company name match if specific suffixes are not present
                        company_match = re.search(r'([A-Z][a-zA-Z\s,.-]{3,})', line) # Starts with Capital, at least 3 chars
                    
                    company = company_match.group(1).strip() if company_match else "Unknown Company"
                    
                    # Parse contribution amounts (simplified, assumes numeric values are contributions)
                    amount_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)' # Matches numbers like 1,234.56 or 1234
                    amounts = re.findall(amount_pattern, line)
                    
                    employee_contribution = amounts[0].replace(',', '') if len(amounts) > 0 else '0'
                    employer_contribution = amounts[1].replace(',', '') if len(amounts) > 1 else '0'
                    pension = amounts[2].replace(',', '') if len(amounts) > 2 else '0'
                    
                    try:
                        date_obj = datetime.strptime(month_year_str, "%b - %Y") # Try to parse "Jan - 2023"
                        employment_records.append({
                            'company': company,
                            'start_date': date_obj,
                            'end_date': date_obj, # Assuming single month record
                            'date_range': month_year_str,
                            'employee_contribution': employee_contribution,
                            'employer_contribution': employer_contribution,
                            'pension': pension,
                            'source': 'EPF'
                        })
                    except ValueError:
                        try: # Try another format for month-year
                            date_obj = datetime.strptime(month_year_str, "%b-%Y")
                            employment_records.append({
                                'company': company,
                                'start_date': date_obj,
                                'end_date': date_obj, # Assuming single month record
                                'date_range': month_year_str,
                                'employee_contribution': employee_contribution,
                                'employer_contribution': employer_contribution,
                                'pension': pension,
                                'source': 'EPF'
                            })
                        except ValueError:
                            print(f"Could not parse date from line: {line}")
                            continue # Skip if date parsing fails
        return employment_records
    
    def parse_date_range(self, date_range: str) -> tuple:
        """Parse date range string to extract start and end dates"""
        date_range = date_range.replace('–', '-').replace('—', '-')
        
        start_date = None
        end_date = None

        parts = [p.strip() for p in date_range.split('-')]
        
        if len(parts) >= 1:
            start_date = self.parse_date(parts[0])
        if len(parts) >= 2:
            end_date_str = parts[1]
            end_date = self.parse_date(end_date_str) if end_date_str.lower() != 'present' else None
            
        return start_date, end_date
    
    def parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object"""
        date_str = date_str.strip()
        if not date_str or date_str.lower() == 'present':
            return None # Return None for empty or 'Present' dates
            
        # Handle different date formats (expanded list for robustness)
        formats = [
            '%m/%Y',      # 03/2021
            '%m-%Y',      # 03-2021
            '%b/%Y',      # Mar/2021
            '%b-%Y',      # Mar-2021
            '%B %Y',      # March 2021
            '%Y-%m',      # 2021-03
            '%Y',         # 2021 (just year)
            '%d %b %Y',   # 01 Jan 2021
            '%d-%b-%Y',   # 01-Jan-2021
            '%b %d, %Y',  # Jan 01, 2021
            '%Y/%m/%d',   # 2021/03/15
            '%Y-%m-%d',   # 2021-03-15
            '%b %Y'       # Jan 2021
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
                
        # If no format matches, try to extract year at least
        year_match = re.search(r'(\d{4})', date_str)
        if year_match:
            try:
                return datetime(int(year_match.group(1)), 1, 1) # Default to Jan 1st of the year
            except ValueError:
                pass # Continue if year extraction itself fails
            
        return None # Return None if date cannot be parsed
    
    def create_embeddings(self, employment_records: List[Dict[str, Any]]) -> List[np.ndarray]:
        """Create embeddings for employment records"""
        embeddings = []
        
        for record in employment_records:
            # Create text representation of the employment record
            if record['source'] == 'CV':
                text = f"Company: {record.get('company', 'N/A')}, Start Date: {record.get('start_date', 'N/A')}, End Date: {record.get('end_date', 'N/A')}, Duration: {record.get('date_range', 'N/A')}"
            else:  # EPF
                text = f"Company: {record.get('company', 'N/A')}, Period: {record.get('date_range', 'N/A')}, Employee Contribution: {record.get('employee_contribution', 'N/A')}"
            
            # Generate embedding
            embedding = self.model.encode(text)
            embeddings.append(embedding)
            
        return embeddings
    
    def find_similar_employment(self, cv_records: List[Dict[str, Any]], epf_records: List[Dict[str, Any]], 
                               threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Find similar employment records between CV and EPF using semantic similarity"""
        
        if not cv_records or not epf_records:
            print("No CV or EPF records to compare.")
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
        cv_context = f"CV Employment: Company: {cv_record.get('company', 'N/A')}, Duration: {cv_record.get('date_range', 'N/A')}"
        epf_context = "EPF Records:\n" + "\n".join([
            f"- {record.get('company', 'N/A')} ({record.get('date_range', 'N/A')}): Employee Contribution: ₹{record.get('employee_contribution', 'N/A')}"
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
                    "model": "llama3.2",  # Ensure this model is available in your Ollama setup
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                # Attempt to parse the LLM's response if it's a JSON string
                try:
                    llm_parsed_response = json.loads(result.get('response', '{}'))
                except json.JSONDecodeError:
                    llm_parsed_response = {'raw_llm_response': result.get('response', '')} # Store raw if not valid JSON
                return {
                    'llm_response': llm_parsed_response,
                    'verification_method': 'LLM'
                }
            else:
                return {
                    'llm_response': f'Error: LLM API returned status code {response.status_code} - {response.text}',
                    'verification_method': 'LLM'
                }
        except requests.exceptions.ConnectionError:
            return {
                'llm_response': 'Error: Could not connect to Ollama host. Is Ollama running and accessible at http://ollama:11434?',
                'verification_method': 'LLM'
            }
        except Exception as e:
            print(f"Error calling LLM: {e}")
            
        return {
            'llm_response': f'General error calling LLM: {str(e)}',
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
        
        # Use set comprehension with conditional checks for 'company' key and non-empty company names
        total_cv_companies = len(set(record['company'] for record in cv_records if 'company' in record and record['company']))
        total_epf_companies = len(set(record['company'] for record in epf_records if 'company' in record and record['company']))
        
        verified_companies = len(set(match['cv_record']['company'] for match in matches if 'cv_record' in match and 'company' in match['cv_record'] and match['cv_record']['company']))
        
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
    # Ensure 'uploads' and 'output' directories exist
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('output', exist_ok=True)

    verifier = EmploymentRAGVerifier()
    
    # Create dummy PDF files for testing if they don't exist
    dummy_cv_path = 'uploads/cv.pdf'
    dummy_epf_path = 'uploads/EPF_Statement.pdf'

    if not os.path.exists(dummy_cv_path):
        print(f"Creating dummy CV file at {dummy_cv_path}")
        # Create a simple dummy PDF content for testing
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(dummy_cv_path, pagesize=letter)
        c.drawString(100, 750, "Professional Experience")
        c.drawString(100, 730, "Software Engineer")
        c.drawString(120, 715, "ABC Tech Solutions | 01/2020 – 12/2022")
        c.drawString(100, 690, "Senior Developer")
        c.drawString(120, 675, "XYZ Software | 01/2023 – Present")
        c.drawString(100, 650, "Education")
        c.save()

    if not os.path.exists(dummy_epf_path):
        print(f"Creating dummy EPF Statement file at {dummy_epf_path}")
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(dummy_epf_path, pagesize=letter)
        c.drawString(50, 750, "Employment & Contribution History")
        c.drawString(50, 730, '"01/2020 - 12/2022","ABC Tech Solutions","EST123","15000","1800","500","CLOSED"')
        c.drawString(50, 710, '"01/2023 - Present","XYZ Software","EST456","20000","2400","700","ACTIVE"')
        c.save()

    # Process documents
    results = verifier.process_documents(dummy_cv_path, dummy_epf_path)
    
    # Save results
    with open('output/verification_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("Verification completed. Results saved to output/verification_results.json")