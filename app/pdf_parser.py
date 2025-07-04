# pdf_parser.py
from PyPDF2 import PdfReader

def extract_text_from_pdf(pdf_path):
    """
    Extracts all text from a PDF file.
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or "" # Handle pages with no extractable text
        return text
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        return None