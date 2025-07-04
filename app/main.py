# main.py
import os
from pdf_parser import extract_text_from_pdf
from data_extractor import DataExtractor
from verifier import DocumentVerifier

def main():
    print("OLLAMA-based Document Verification Tool")
    print("--------------------------------------")

    cv_path = input("Enter the path to the CV PDF file: ").strip()
    pf_path = input("Enter the path to the PF PDF file: ").strip()

    if not os.path.exists(cv_path):
        print(f"Error: CV file not found at {cv_path}")
        return
    if not os.path.exists(pf_path):
        print(f"Error: PF file not found at {pf_path}")
        return

    # 1. Extract raw text from PDFs
    print("\n--- Step 1: Extracting text from PDFs ---")
    cv_text = extract_text_from_pdf(cv_path)
    pf_text = extract_text_from_pdf(pf_path)

    if not cv_text:
        print("Failed to extract text from CV. Exiting.")
        return
    if not pf_text:
        print("Failed to extract text from PF. Exiting.")
        return

    # 2. Extract structured data using Ollama
    print("\n--- Step 2: Extracting structured data using OLLAMA ---")
    data_extractor = DataExtractor()
    cv_data = data_extractor.extract_cv_data(cv_text)
    pf_data = data_extractor.extract_pf_data(pf_text)

    if not cv_data:
        print("Failed to extract structured data from CV. Exiting.")
        return
    if not pf_data:
        print("Failed to extract structured data from PF. Exiting.")
        return

    print("\n--- Extracted CV Data ---")
    print(cv_data)
    print("\n--- Extracted PF Data ---")
    print(pf_data)

    # 3. Verify documents
    print("\n--- Step 3: Verifying documents ---")
    verifier = DocumentVerifier()

    # Optional: Perform rule-based pre-check for quick insights
    print("\n--- Performing Rule-Based Pre-Verification ---")
    rule_based_check = verifier.perform_rule_based_pre_check(cv_data, pf_data)
    print("Rule-Based Check Status:", rule_based_check['status'])
    print("Rule-Based Check Summary:", rule_based_check['summary'])
    if rule_based_check['discrepancies']:
        print("Rule-Based Discrepancies:")
        for disc in rule_based_check['discrepancies']:
            print(f"  - [{disc['type']}]: {disc['description']}")

    # Use Ollama for more nuanced verification
    print("\n--- Performing LLM-Based Verification (OLLAMA) ---")
    llm_verification_result = verifier.verify_documents(cv_data, pf_data)

    print("\n--- Verification Results (OLLAMA) ---")
    if llm_verification_result:
        print(f"Status: {llm_verification_result.get('status', 'N/A')}")
        print(f"Summary: {llm_verification_result.get('summary', 'N/A')}")
        discrepancies = llm_verification_result.get('discrepancies', [])
        if discrepancies:
            print("\nDiscrepancies Found:")
            for disc in discrepancies:
                print(f"  - Type: {disc.get('type')}")
                print(f"    Description: {disc.get('description')}")
                if disc.get('cv_entry'):
                    print(f"    CV Entry: {disc['cv_entry']}")
                if disc.get('pf_entry'):
                    print(f"    PF Entry: {disc['pf_entry']}")
        else:
            print("No discrepancies found by LLM.")

        matched_entries = llm_verification_result.get('matched_entries', [])
        if matched_entries:
            print("\nMatched Entries:")
            for match in matched_entries:
                print(f"  - CV: {match.get('cv_entry')}")
                print(f"    PF: {match.get('pf_entry')}")

    else:
        print("Failed to get verification results from OLLAMA.")

if __name__ == "__main__":
    main()