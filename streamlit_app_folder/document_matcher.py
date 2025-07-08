import ollama
import os
import json
from typing import Dict, List, Optional, Tuple
from data_extractor import DocumentExtractor
from dateutil.parser import parse
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz
import re
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentMatcher:
    """
    A comprehensive document matcher for CV and EPF employment verification.
    Combines static matching with AI analysis for robust verification.
    """
    
    def __init__(self, model: str = 'gemma:2b', ollama_url: str = None):
        """
        Initialize the DocumentMatcher.
        
        Args:
            model: Ollama model to use for AI analysis
            ollama_url: URL for Ollama service
        """
        self.ollama_url = ollama_url or os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.model = model
        self.extractor = DocumentExtractor()
        
        # Configuration constants
        self.COMPANY_NAME_THRESHOLD = 80  # Fuzzy matching threshold
        self.DATE_VARIANCE_MONTHS = 2     # Acceptable date variance
        self.MAX_CONTEXT_LENGTH = 8192    # Ollama context window
    
    def verify_documents(self, cv_text: str, pf_text: str) -> Dict:
        """
        Main verification function that combines static and AI analysis.
        
        Args:
            cv_text: Full CV text content
            pf_text: Full PF/EPF text content
            
        Returns:
            Dict containing verification results
        """
        try:
            logger.info("Starting document verification process")
            
            # Extract structured information
            cv_info = self.extractor.extract_cv_data(cv_text)
            pf_info = self.extractor.extract_pf_data(pf_text)
            
            # Perform static matching (Step 1)
            static_matches = self.match_employment_records(cv_info, pf_info)
            
            # Get AI analysis (Step 2)
            ai_analysis = self.get_ai_analysis(cv_text, pf_text)
            
            # Calculate overall verification result
            verification_result = self._calculate_overall_verification(static_matches, ai_analysis)
            
            result = {
                'verification_result': verification_result,
                'static_analysis': {
                    'matches': static_matches,
                    'summary': self._create_static_summary(static_matches)
                },
                'ai_analysis': ai_analysis,
                'extracted_data': {
                    'cv_info': cv_info,
                    'pf_info': pf_info
                },
                'metadata': {
                    'processed_at': datetime.now().isoformat(),
                    'cv_employers_count': len(cv_info.get('employment_history', [])),
                    'pf_employers_count': len(pf_info.get('employment_records', []))
                }
            }
            
            logger.info(f"Verification completed. Status: {verification_result['overall_status']}")
            return result
            
        except Exception as e:
            logger.error(f"Verification failed: {str(e)}")
            return self._create_error_response(str(e))

    def match_employment_records(self, cv_info: Dict, pf_info: Dict) -> List[Dict]:
        """
        Match employment records between CV and PF using fuzzy matching and date overlap.
        
        Args:
            cv_info: Extracted CV information
            pf_info: Extracted PF information
            
        Returns:
            List of match results with detailed information
        """
        matches = []
        cv_employment = cv_info.get('employment_history', [])
        pf_employment = pf_info.get('employment_records', [])
        
        if not cv_employment and not pf_employment:
            return matches
            
        matched_pf_indices = set()
        
        logger.info(f"Matching {len(cv_employment)} CV entries with {len(pf_employment)} PF entries")

        # Match CV entries with PF entries
        for cv_entry in cv_employment:
            best_match = self._find_best_pf_match(cv_entry, pf_employment, matched_pf_indices)
            
            if best_match:
                pf_entry, match_score, pf_index = best_match
                matches.append({
                    'employer': cv_entry.get('company'),
                    'period': f"{cv_entry.get('start_date')} - {cv_entry.get('end_date')}",
                    'status': 'matched',
                    'match_score': match_score,
                    'match_quality': self._determine_match_quality(match_score),
                    'cv_entry': cv_entry,
                    'pf_entry': pf_entry,
                    'date_variance': self._calculate_date_variance(cv_entry, pf_entry)
                })
                matched_pf_indices.add(pf_index)
            else:
                matches.append({
                    'employer': cv_entry.get('company'),
                    'period': f"{cv_entry.get('start_date')} - {cv_entry.get('end_date')}",
                    'status': 'no_pf_match',
                    'issue': 'No matching PF entry found or significant discrepancy',
                    'cv_entry': cv_entry,
                    'pf_entry': None,
                    'severity': 'high'
                })
        
        # Add unmatched PF entries
        for i, pf_entry in enumerate(pf_employment):
            if i not in matched_pf_indices:
                matches.append({
                    'employer': pf_entry.get('employer_name'),
                    'period': f"{pf_entry.get('start_date')} - {pf_entry.get('end_date')}",
                    'status': 'no_cv_match',
                    'issue': 'PF entry exists without matching CV entry',
                    'cv_entry': None,
                    'pf_entry': pf_entry,
                    'severity': 'medium'
                })

        return matches

    def _find_best_pf_match(self, cv_entry: Dict, pf_employment: List[Dict], 
                           matched_indices: set) -> Optional[Tuple[Dict, float, int]]:
        """
        Find the best matching PF entry for a CV entry.
        
        Returns:
            Tuple of (pf_entry, match_score, index) or None if no good match
        """
        best_match = None
        best_score = 0
        best_index = -1
        
        cv_company = cv_entry.get('company', '').lower().strip()
        cv_start = cv_entry.get('start_date')
        cv_end = cv_entry.get('end_date')
        
        for i, pf_entry in enumerate(pf_employment):
            if i in matched_indices:
                continue
                
            pf_company = pf_entry.get('employer_name', '').lower().strip()
            pf_start = pf_entry.get('start_date')
            pf_end = pf_entry.get('end_date')
            
            # Calculate company name similarity
            company_score = fuzz.ratio(cv_company, pf_company)
            
            # Check date overlap
            date_overlap = self._check_date_overlap(cv_start, cv_end, pf_start, pf_end)
            
            # Combined scoring: company name similarity + date overlap bonus
            total_score = company_score
            if date_overlap:
                total_score += 10  # Bonus for date overlap
                
            # Accept match if above threshold and has date overlap
            if total_score > self.COMPANY_NAME_THRESHOLD and date_overlap:
                if total_score > best_score:
                    best_match = pf_entry
                    best_score = total_score
                    best_index = i
                    
        return (best_match, best_score, best_index) if best_match else None

    def _check_date_overlap(self, cv_start_str: str, cv_end_str: str, 
                           pf_start_str: str, pf_end_str: str) -> bool:
        """
        Check for overlap between two date ranges with improved error handling.
        """
        try:
            current_date = datetime.now()
            
            # Parse dates with better handling
            cv_start = self._parse_date(cv_start_str)
            cv_end = self._parse_date(cv_end_str, default_to_current=True)
            pf_start = self._parse_date(pf_start_str)
            pf_end = self._parse_date(pf_end_str, default_to_current=True)
            
            if not all([cv_start, cv_end, pf_start, pf_end]):
                return False
                
            # Allow for reasonable variance (notice periods, etc.)
            variance = timedelta(days=self.DATE_VARIANCE_MONTHS * 30)
            
            # Check for overlap with variance tolerance
            return ((cv_start - variance) <= (pf_end + variance)) and \
                   ((pf_start - variance) <= (cv_end + variance))
                   
        except Exception as e:
            logger.warning(f"Date overlap check failed: {e}")
            return False

    def _parse_date(self, date_str: str, default_to_current: bool = False) -> Optional[datetime]:
        """
        Parse date string with multiple format support.
        """
        if not date_str:
            return None
            
        date_str = date_str.strip().lower()
        
        # Handle 'present' case
        if date_str in ['present', 'current', 'ongoing']:
            return datetime.now() if default_to_current else datetime(2099, 12, 31)
            
        try:
            # Try parsing with dateutil
            return parse(date_str, fuzzy=True)
        except Exception:
            # Try manual parsing for common formats
            date_patterns = [
                r'(\d{1,2})/(\d{4})',  # MM/YYYY
                r'(\d{4})-(\d{1,2})',  # YYYY-MM
                r'(\d{1,2})-(\d{4})',  # MM-YYYY
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, date_str)
                if match:
                    try:
                        if len(match.group(1)) == 4:  # YYYY-MM format
                            year, month = int(match.group(1)), int(match.group(2))
                        else:  # MM/YYYY or MM-YYYY format
                            month, year = int(match.group(1)), int(match.group(2))
                        return datetime(year, month, 1)
                    except ValueError:
                        continue
                        
            logger.warning(f"Could not parse date: {date_str}")
            return None

    def _calculate_date_variance(self, cv_entry: Dict, pf_entry: Dict) -> Dict:
        """Calculate variance between CV and PF dates."""
        try:
            cv_start = self._parse_date(cv_entry.get('start_date'))
            cv_end = self._parse_date(cv_entry.get('end_date'), default_to_current=True)
            pf_start = self._parse_date(pf_entry.get('start_date'))
            pf_end = self._parse_date(pf_entry.get('end_date'), default_to_current=True)
            
            if not all([cv_start, cv_end, pf_start, pf_end]):
                return {'status': 'calculation_failed'}
            
            start_diff = abs((cv_start - pf_start).days)
            end_diff = abs((cv_end - pf_end).days)
            
            return {
                'start_difference_days': start_diff,
                'end_difference_days': end_diff,
                'start_difference_months': round(start_diff / 30, 1),
                'end_difference_months': round(end_diff / 30, 1),
                'acceptable': start_diff <= (self.DATE_VARIANCE_MONTHS * 30) and 
                             end_diff <= (self.DATE_VARIANCE_MONTHS * 30)
            }
        except Exception as e:
            logger.warning(f"Date variance calculation failed: {e}")
            return {'status': 'calculation_failed', 'error': str(e)}

    def _determine_match_quality(self, match_score: float) -> str:
        """Determine match quality based on score."""
        if match_score >= 95:
            return 'excellent'
        elif match_score >= 85:
            return 'good'
        elif match_score >= 75:
            return 'fair'
        else:
            return 'poor'

    def _create_static_summary(self, matches: List[Dict]) -> Dict:
        """Create summary of static matching results."""
        total_matches = len(matches)
        successful_matches = len([m for m in matches if m['status'] == 'matched'])
        no_pf_matches = len([m for m in matches if m['status'] == 'no_pf_match'])
        no_cv_matches = len([m for m in matches if m['status'] == 'no_cv_match'])
        
        return {
            'total_entries': total_matches,
            'successful_matches': successful_matches,
            'no_pf_matches': no_pf_matches,
            'no_cv_matches': no_cv_matches,
            'match_rate': (successful_matches / total_matches * 100) if total_matches > 0 else 0,
            'overall_status': 'good' if successful_matches == total_matches else 'discrepancies_found'
        }

    def _calculate_overall_verification(self, static_matches: List[Dict], ai_analysis: Dict) -> Dict:
        """Calculate overall verification result combining static and AI analysis."""
        static_summary = self._create_static_summary(static_matches)
        ai_summary = ai_analysis.get('verification_summary', {})
        
        # Determine overall status
        if static_summary['match_rate'] == 100 and ai_summary.get('overall_status') == 'MATCH':
            overall_status = 'VERIFIED'
            confidence = 0.95
        elif static_summary['match_rate'] >= 80 and ai_summary.get('overall_status') in ['MATCH', 'MINOR_DISCREPANCY']:
            overall_status = 'MOSTLY_VERIFIED'
            confidence = 0.80
        elif static_summary['match_rate'] >= 50:
            overall_status = 'PARTIALLY_VERIFIED'
            confidence = 0.60
        else:
            overall_status = 'VERIFICATION_FAILED'
            confidence = 0.30
            
        return {
            'overall_status': overall_status,
            'confidence_score': confidence,
            'static_match_rate': static_summary['match_rate'],
            'ai_status': ai_summary.get('overall_status', 'UNKNOWN'),
            'ai_confidence': ai_summary.get('confidence_score', 0.0),
            'recommendation': self._get_recommendation(overall_status, static_summary, ai_summary)
        }

    def _get_recommendation(self, status: str, static_summary: Dict, ai_summary: Dict) -> str:
        """Get recommendation based on verification results."""
        if status == 'VERIFIED':
            return "Employment history is verified and consistent across both documents."
        elif status == 'MOSTLY_VERIFIED':
            return "Employment history is mostly consistent with minor discrepancies that may need clarification."
        elif status == 'PARTIALLY_VERIFIED':
            return "Significant discrepancies found. Manual review and additional documentation recommended."
        else:
            return "Employment history verification failed. Comprehensive manual review required."

    def get_ai_analysis(self, cv_full_text: str, pf_full_text: str) -> dict:
        """Get AI analysis with improved error handling and structured output."""
        try:
            # Pre-process documents
            cv_employment = self._extract_employment_section(cv_full_text)
            pf_employment = self._extract_pf_employment_section(pf_full_text)
            
            # Truncate if too long for context window
            cv_employment = self._truncate_text(cv_employment, self.MAX_CONTEXT_LENGTH // 2)
            pf_employment = self._truncate_text(pf_employment, self.MAX_CONTEXT_LENGTH // 2)
            
            prompt = self._create_ai_prompt(cv_employment, pf_employment)
            
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={
                    'temperature': 0.1,
                    'num_ctx': self.MAX_CONTEXT_LENGTH,
                    'top_p': 0.9,
                    'repeat_penalty': 1.1
                }
            )
            
            return self._parse_ai_response(response['response'])
            
        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}")
            return self._create_fallback_analysis(str(e))

    def _create_ai_prompt(self, cv_employment: str, pf_employment: str) -> str:
        """Create optimized prompt for AI analysis."""
        return f"""You are an expert employment verification specialist. Analyze these employment documents and provide a structured assessment.

CV Employment History:
{cv_employment}

EPF Employment Records:
{pf_employment}

RESPOND ONLY WITH VALID JSON:
{{
    "verification_summary": {{
        "overall_status": "MATCH|MINOR_DISCREPANCY|MAJOR_DISCREPANCY",
        "confidence_score": 0.85,
        "total_employers_cv": 2,
        "total_employers_epf": 2
    }},
    "employment_matches": [
        {{
            "company_name_cv": "Company Name",
            "company_name_epf": "Company Name in EPF",
            "period_cv": "MM/YYYY - MM/YYYY",
            "period_epf": "MM/YYYY - MM/YYYY",
            "match_status": "EXACT_MATCH|PARTIAL_MATCH|NO_MATCH",
            "date_variance_months": 1,
            "issues": []
        }}
    ],
    "discrepancies": [
        {{
            "type": "DATE_MISMATCH|COMPANY_NAME_MISMATCH|MISSING_ENTRY",
            "description": "Specific issue description",
            "severity": "HIGH|MEDIUM|LOW"
        }}
    ],
    "recommendations": ["Specific recommendation"],
    "analysis_notes": "Brief additional context"
}}

Rules:
- Allow 1-2 months variance for employment dates
- Consider company name variations (Ltd, Pvt Ltd, etc.)
- EPF shows monthly contributions, infer employment periods
- Focus on significant discrepancies only"""

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to fit within context window."""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "... [truncated]"

    def _parse_ai_response(self, response: str) -> dict:
        """Parse AI response with multiple fallback strategies."""
        try:
            # First try: direct JSON parsing
            return json.loads(response)
        except json.JSONDecodeError:
            try:
                # Second try: extract JSON from response
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
            
            # Third try: clean common issues
            try:
                cleaned = response.strip()
                if cleaned.startswith('```json'):
                    cleaned = cleaned[7:]
                if cleaned.endswith('```'):
                    cleaned = cleaned[:-3]
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
                
            logger.warning("Failed to parse AI response as JSON")
            return self._create_fallback_analysis("JSON parsing failed")

    def _extract_employment_section(self, cv_text: str) -> str:
        """Extract employment section from CV with improved patterns."""
        patterns = [
            r"Professional Experience\s*\n(.*?)\n---",
            r"Employment History\s*\n(.*?)\n---",
            r"Work Experience\s*\n(.*?)\n---",
            r"Experience\s*\n(.*?)(?=\n[A-Z][a-z]|\n---|$)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, cv_text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
                
        return cv_text  # Return full text if no section found

    def _extract_pf_employment_section(self, pf_text: str) -> str:
        """Extract employment section from PF with improved patterns."""
        patterns = [
            r"Employment & Contribution History\s*\n(.*?)(?=\n---|$)",
            r"Employment History\s*\n(.*?)(?=\n---|$)",
            r"Contribution History\s*\n(.*?)(?=\n---|$)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, pf_text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
                
        return pf_text  # Return full text if no section found

    def _create_fallback_analysis(self, error_msg: str) -> dict:
        """Create fallback analysis when AI fails."""
        return {
            "verification_summary": {
                "overall_status": "ANALYSIS_FAILED",
                "confidence_score": 0.0,
                "error_message": error_msg
            },
            "employment_matches": [],
            "discrepancies": [{
                "type": "ANALYSIS_ERROR",
                "description": f"AI analysis failed: {error_msg}",
                "severity": "HIGH"
            }],
            "recommendations": ["Perform manual verification"],
            "analysis_notes": "AI analysis unavailable, manual review required"
        }

    def _create_error_response(self, error_msg: str) -> Dict:
        """Create error response structure."""
        return {
            'verification_result': {
                'overall_status': 'ERROR',
                'confidence_score': 0.0,
                'error_message': error_msg
            },
            'static_analysis': {'matches': [], 'summary': {}},
            'ai_analysis': self._create_fallback_analysis(error_msg),
            'extracted_data': {'cv_info': {}, 'pf_info': {}},
            'metadata': {
                'processed_at': datetime.now().isoformat(),
                'error': error_msg
            }
        }

    def get_detailed_report(self, verification_result: Dict) -> str:
        """Generate a comprehensive human-readable report."""
        try:
            result = verification_result['verification_result']
            static_analysis = verification_result['static_analysis']
            ai_analysis = verification_result['ai_analysis']
            metadata = verification_result['metadata']
            
            report = f"""
EMPLOYMENT VERIFICATION REPORT
{'=' * 50}

OVERALL ASSESSMENT:
Status: {result['overall_status']}
Confidence Score: {result['confidence_score']:.2%}
Processed: {metadata.get('processed_at', 'Unknown')}

STATIC ANALYSIS RESULTS:
{'-' * 30}
Total Entries Analyzed: {static_analysis['summary'].get('total_entries', 0)}
Successful Matches: {static_analysis['summary'].get('successful_matches', 0)}
Match Rate: {static_analysis['summary'].get('match_rate', 0):.1f}%

EMPLOYMENT MATCHES:
"""
            
            for i, match in enumerate(static_analysis['matches'], 1):
                report += f"\n{i}. {match['employer']} ({match['status']})\n"
                report += f"   Period: {match['period']}\n"
                if match.get('match_score'):
                    report += f"   Match Score: {match['match_score']:.1f}%\n"
                if match.get('issue'):
                    report += f"   Issue: {match['issue']}\n"
            
            # Add AI analysis if available
            if ai_analysis.get('discrepancies'):
                report += "\n\nAI ANALYSIS FINDINGS:\n"
                for disc in ai_analysis['discrepancies']:
                    report += f"• {disc['type']} ({disc['severity']}): {disc['description']}\n"
            
            # Add recommendations
            recommendations = ai_analysis.get('recommendations', [])
            if recommendations:
                report += "\n\nRECOMMENDATIONS:\n"
                for i, rec in enumerate(recommendations, 1):
                    report += f"{i}. {rec}\n"
            
            report += f"\n\nFINAL RECOMMENDATION:\n{result.get('recommendation', 'No recommendation available')}\n"
            
            return report
            
        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}")
            return f"Report generation failed: {str(e)}"