# streamlit_app.py
import streamlit as st
import os
import json
from io import BytesIO

# Import your existing modules
from pdf_parser import extract_text_from_pdf
from data_extractor import DataExtractor
from verifier import DocumentVerifier # This will now trigger LLM for comparison

# --- Initialize Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "cv_file" not in st.session_state:
    st.session_state.cv_file = None
if "pf_file" not in st.session_state:
    st.session_state.pf_file = None
if "processing" not in st.session_state:
    st.session_state.processing = False

# --- UI Components ---
st.set_page_config(page_title="OLLAMA Document Verifier", layout="wide")

st.title("📄 OLLAMA Document Verifier")
st.markdown("Upload a CV and a PF document, and I'll verify employment details using a local LLM.")

# Sidebar for file uploads
with st.sidebar:
    st.header("Upload Documents")
    cv_upload = st.file_uploader("Upload CV (PDF)", type=["pdf"], key="cv_uploader")
    pf_upload = st.file_uploader("Upload PF (PDF)", type=["pdf"], key="pf_uploader")

    if cv_upload:
        st.session_state.cv_file = cv_upload
        st.success(f"CV '{cv_upload.name}' uploaded!")
    if pf_upload:
        st.session_state.pf_file = pf_upload
        st.success(f"PF '{pf_upload.name}' uploaded!")

    st.markdown("---")
    if st.button("Clear Chat", type="secondary"):
        st.session_state.messages = []
        st.session_state.cv_file = None
        st.session_state.pf_file = None
        st.rerun()

# --- Display Chat History ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["type"] == "text":
            st.markdown(message["content"])
        elif message["type"] == "data":
            st.json(message["content"])
        elif message["type"] == "error":
            st.error(message["content"])

# --- Main Interaction Logic ---
def run_verification():
    if not st.session_state.cv_file or not st.session_state.pf_file:
        st.session_state.messages.append({"role": "assistant", "type": "error", "content": "Please upload both CV and PF PDF files to proceed."})
        st.session_state.processing = False
        st.rerun()
        return

    st.session_state.processing = True
    st.session_state.messages.append({"role": "assistant", "type": "text", "content": "Processing documents... This might take a moment."})

    temp_cv_path = "/app/documents/uploaded_cv.pdf"
    temp_pf_path = "/app/documents/uploaded_pf.pdf"

    try:
        with open(temp_cv_path, "wb") as f:
            f.write(st.session_state.cv_file.getvalue())
        with open(temp_pf_path, "wb") as f:
            f.write(st.session_state.pf_file.getvalue())

        # 1. Extract raw text from PDFs
        st.session_state.messages.append({"role": "assistant", "type": "text", "content": "Extracting text from PDFs..."})
        with st.spinner("Extracting text..."):
            cv_text = extract_text_from_pdf(temp_cv_path)
            pf_text = extract_text_from_pdf(temp_pf_path)

        if not cv_text:
            st.session_state.messages.append({"role": "assistant", "type": "error", "content": "Failed to extract text from CV."})
            st.session_state.processing = False
            return
        if not pf_text:
            st.session_state.messages.append({"role": "assistant", "type": "error", "content": "Failed to extract text from PF."})
            st.session_state.processing = False
            return

        # 2. Extract structured data using Ollama
        st.session_state.messages.append({"role": "assistant", "type": "text", "content": "Extracting structured data using OLLAMA..."})
        data_extractor = DataExtractor()
        with st.spinner("Extracting structured data (CV)..."):
            cv_data = data_extractor.extract_cv_data(cv_text)
        with st.spinner("Extracting structured data (PF)..."):
            pf_data = data_extractor.extract_pf_data(pf_text)

        if not cv_data:
            st.session_state.messages.append({"role": "assistant", "type": "error", "content": "Failed to extract structured data from CV."})
            st.session_state.processing = False
            return
        if not pf_data:
            st.session_state.messages.append({"role": "assistant", "type": "error", "content": "Failed to extract structured data from PF."})
            st.session_state.processing = False
            return

        st.session_state.messages.append({"role": "assistant", "type": "text", "content": "Extracted CV Data:"})
        st.session_state.messages.append({"role": "assistant", "type": "data", "content": cv_data})
        st.session_state.messages.append({"role": "assistant", "type": "text", "content": "Extracted PF Data:"})
        st.session_state.messages.append({"role": "assistant", "type": "data", "content": pf_data})

        # 3. Verify documents using LLM directly
        st.session_state.messages.append({"role": "assistant", "type": "text", "content": "Performing LLM-Based Verification (OLLAMA) for full analysis..."})
        verifier = DocumentVerifier()
        with st.spinner("Running LLM-based verification..."):
            llm_verification_result = verifier.verify_documents(cv_data, pf_data)

        if llm_verification_result:
            st.session_state.messages.append({"role": "assistant", "type": "text", "content": "--- Final Verification Results (OLLAMA) ---"})
            st.session_state.messages.append({"role": "assistant", "type": "data", "content": llm_verification_result})

            # Provide more user-friendly status feedback
            status = llm_verification_result.get('status', 'N/A')
            if status == "PASS":
                st.session_state.messages.append({"role": "assistant", "type": "text", "content": "✅ **Verification successful! Documents appear to be consistent.**"})
            elif status == "PARTIAL_PASS":
                st.session_state.messages.append({"role": "assistant", "type": "text", "content": "⚠️ **Verification found some inconsistencies but also matched entries.** Please review the discrepancies carefully."})
            elif status == "FAIL":
                st.session_state.messages.append({"role": "assistant", "type": "text", "content": "❌ **Verification failed! Significant discrepancies found.** Please review the details."})
            else:
                st.session_state.messages.append({"role": "assistant", "type": "text", "content": f"Status: {status}. Please review the raw results."})

        else:
            st.session_state.messages.append({"role": "assistant", "type": "error", "content": "Failed to get detailed verification results from OLLAMA."})

    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "type": "error", "content": f"An error occurred during verification: {e}"})
    finally:
        st.session_state.processing = False
        # Clean up temporary files
        if os.path.exists(temp_cv_path):
            os.remove(temp_cv_path)
        if os.path.exists(temp_pf_path):
            os.remove(temp_pf_path)
        st.rerun() # Rerun to update chat history


# Chat input for user prompts
if prompt := st.chat_input("Start verification or ask a question...", disabled=st.session_state.processing):
    st.session_state.messages.append({"role": "user", "type": "text", "content": prompt})

    if "verify" in prompt.lower() or "run check" in prompt.lower():
        st.session_state.messages.append({"role": "assistant", "type": "text", "content": "Initiating document verification..."})
        run_verification()
    else:
        st.session_state.messages.append({"role": "assistant", "type": "text", "content": "I can only perform document verification for now. Please upload files and type 'verify' to start the process."})
        st.rerun()