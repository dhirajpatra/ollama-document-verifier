# data_extractor.py
import json
from ollama_client import OllamaClient
from config import CV_EXTRACTION_PROMPT, PF_EXTRACTION_PROMPT
from utils import safe_json_parse, parse_date # Ensure parse_date is here

class DataExtractor:
    def __init__(self):
        self.ollama_client = OllamaClient()

    def extract_cv_data(self, cv_text):
        prompt = CV_EXTRACTION_PROMPT.format(cv_text=cv_text)
        print("Sending CV extraction prompt to Ollama...")
        llm_raw_response = self.ollama_client.generate_response(prompt)
        if llm_raw_response:
            cv_data = safe_json_parse(llm_raw_response)
            if cv_data:
                # Post-process dates to ensure they are parsed into proper datetime objects
                # or handle 'null' gracefully if they come from LLM
                if "employment_history" in cv_data and isinstance(cv_data["employment_history"], list):
                    for entry in cv_data["employment_history"]:
                        # Ensure start_date and end_date are strings or None
                        if entry.get("start_date"):
                            entry["start_date_parsed"] = parse_date(str(entry["start_date"]))
                        else:
                            entry["start_date_parsed"] = None
                        if entry.get("end_date"):
                            entry["end_date_parsed"] = parse_date(str(entry["end_date"]))
                        else:
                            entry["end_date_parsed"] = None
                return cv_data
        return None

    def extract_pf_data(self, pf_text):
        prompt = PF_EXTRACTION_PROMPT.format(pf_text=pf_text)
        print("Sending PF extraction prompt to Ollama...")
        llm_raw_response = self.ollama_client.generate_response(prompt)
        if llm_raw_response:
            pf_data = safe_json_parse(llm_raw_response)
            if pf_data:
                if "contributions" in pf_data and isinstance(pf_data["contributions"], list):
                    for entry in pf_data["contributions"]:
                        if entry.get("period_start"):
                            entry["period_start_parsed"] = parse_date(str(entry["period_start"]))
                        else:
                            entry["period_start_parsed"] = None
                        if entry.get("period_end"):
                            entry["period_end_parsed"] = parse_date(str(entry["period_end"]))
                        else:
                            entry["period_end_parsed"] = None
                return pf_data
        return None