# ollama_client.py
import ollama
import json
from config import OLLAMA_MODEL, OLLAMA_BASE_URL
from utils import safe_json_parse

class OllamaClient:
    def __init__(self, model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL):
        self.model = model
        self.client = ollama.Client(host=base_url)

    def generate_json(self, prompt, context_data=None):
        """
        Sends a prompt to OLLAMA and attempts to get a JSON response.
        Context data can be passed to format the prompt.
        """
        try:
            formatted_prompt = prompt.format(**context_data) if context_data else prompt
            print(f"Sending prompt to Ollama (model: {self.model})...")
            # Using chat for better control and adherence to system prompts/schema
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
                    {"role": "user", "content": formatted_prompt}
                ],
                options={'temperature': 0.1} # Lower temperature for more deterministic output
            )
            # Ollama response structure: response['message']['content']
            llm_output = response['message']['content']
            return safe_json_parse(llm_output)
        except ollama.ResponseError as e:
            print(f"OLLAMA API Error: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred with OLLAMA: {e}")
            return None