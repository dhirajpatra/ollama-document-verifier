import streamlit as st
import os
from pdf_extractor import extract_pdf_text
from document_matcher import DocumentMatcher
from utils import save_uploaded_file, create_directories

def main():
    st.set_page_config(page_title="Document Verification", page_icon="📄", layout="wide")
    
    st.title("🔍 Document Verification System")
    st.markdown("Upload CV and PF PDF to verify employment history matching")
    
    # Create necessary directories
    create_directories()
    
    # File upload section
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 CV Upload")
        cv_file = st.file_uploader("Upload CV PDF", type=['pdf'], key="cv")
        
    with col2:
        st.subheader("📄 PF Statement Upload")
        pf_file = st.file_uploader("Upload PF PDF", type=['pdf'], key="pf")
    
    if cv_file and pf_file:
        if st.button("🔍 Verify Documents", type="primary"):
            with st.spinner("Processing documents..."):
                try:
                    # Save uploaded files
                    cv_path = save_uploaded_file(cv_file, "cv.pdf")
                    pf_path = save_uploaded_file(pf_file, "pf.pdf")
                    
                    # Extract text from PDFs
                    cv_text = extract_pdf_text(cv_path)
                    pf_text = extract_pdf_text(pf_path)
                    
                    # Initialize document matcher
                    matcher = DocumentMatcher()
                    
                    # Perform verification
                    result = matcher.verify_documents(cv_text, pf_text)
                    
                    # Display results
                    display_results(result)
                    
                except Exception as e:
                    st.error(f"Error processing documents: {str(e)}")

def display_results(result):
    st.header("📊 Verification Results")
    
    # Overall status
    if result['overall_match']:
        st.success("✅ Documents Match Successfully!")
    else:
        st.error("❌ Document Mismatch Detected!")
    
    # Detailed results
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 CV Information")
        st.json(result['cv_info'])
    
    with col2:
        st.subheader("📋 PF Information")
        st.json(result['pf_info'])
    
    # Matching details
    st.subheader("🔍 Matching Details")
    for match in result['matches']:
        if match['status'] == 'matched':
            st.success(f"✅ {match['employer']} - {match['period']}")
        else:
            st.error(f"❌ {match['employer']} - {match['period']} - {match['issue']}")
    
    # AI Analysis
    st.subheader("🤖 AI Analysis")
    st.write(result['ai_analysis'])

if __name__ == "__main__":
    main()