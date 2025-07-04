# verifier.py
import json
from ollama_client import OllamaClient
from config import VERIFICATION_PROMPT
from utils import safe_json_parse # Keep this for parsing LLM's JSON output
# utils functions like fuzzy_match_names and parse_date are no longer directly used for comparison here
# but can remain in utils.py if needed elsewhere or for display.

class DocumentVerifier:
    def __init__(self):
        self.ollama_client = OllamaClient()

    def verify_documents(self, cv_data, pf_data):
        """
        Sends extracted CV and PF data to the LLM for comparison and verification.
        The LLM is expected to return a structured JSON with verification results.
        """
        if not cv_data or not pf_data:
            print("Error: CV or PF data is missing for verification.")
            return None

        # Convert data to JSON strings for the LLM prompt
        cv_json_str = json.dumps(cv_data.get("employment_history", []), indent=2)
        pf_json_str = json.dumps(pf_data.get("contributions", []), indent=2)

        # Construct the prompt for the LLM
        prompt = VERIFICATION_PROMPT.format(
            cv_employment_history_json=cv_json_str,
            pf_contributions_json=pf_json_str
        )

        print("Sending verification prompt to Ollama (model: {self.ollama_client.model})...")
        print(f"Prompt sent (truncated): {prompt[:1000]}...") # Print truncated prompt for debugging

        try:
            # Send the prompt to Ollama and get the raw response
            llm_raw_response = self.ollama_client.generate_response(prompt)

            if not llm_raw_response:
                print("LLM returned an empty response for verification.")
                return None

            # Parse the LLM's response which should be a JSON object
            verification_result = safe_json_parse(llm_raw_response)

            if verification_result is None:
                print("Failed to parse LLM's verification response into JSON.")
                return None

            return verification_result

        except Exception as e:
            print(f"An error occurred during LLM verification: {e}")
            return None