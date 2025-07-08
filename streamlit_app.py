import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import pdf_extractor
from document_matcher import DocumentMatcher
from utils import save_uploaded_file, format_verification_results # Assuming save_uploaded_file handles target filename
import plotly.graph_objects as go
from plotly.subplots import make_subplots
# Import the RAG verification script
from rag_employment_verification import EmploymentRAGVerifier

import logger

# Page configuration
st.set_page_config(
    page_title="Document Verification System For Employment BG Checks",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .verification-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin: 1rem 0;
    }
    
    .match-score {
        font-size: 2rem;
        font-weight: bold;
        text-align: center;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .score-high { background: #d4edda; color: #155724; }
    .score-medium { background: #fff3cd; color: #856404; }
    .score-low { background: #f8d7da; color: #721c24; }
    
    .info-box {
        background: #e3f2fd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Function to display RAG-based verification results
def display_rag_results(results):
    """Display RAG-based verification results"""
    if not results:
        st.error("No RAG-based results available.")
        return
    
    # Summary statistics
    summary = results.get("verification_summary", {})
    status_color = "green" if summary.get("status") == "VERIFIED" else "orange" if summary.get("status") == "PARTIALLY_VERIFIED" else "red"
    
    st.markdown(f"""
    <div style="padding: 10px; border-left: 4px solid {status_color}; background-color: #f0f2f6; margin: 10px 0;">
        <strong>Status:</strong> {summary.get("status", "Unknown")}<br>
        <strong>Verification %:</strong> {summary.get("verification_percentage", 0)}%<br>
        <strong>Matches Found:</strong> {results.get("matches_found", 0)}<br>
        <strong>CV Companies:</strong> {summary.get("total_cv_companies", 0)}<br>
        <strong>EPF Companies:</strong> {summary.get("total_epf_companies", 0)}
    </div>
    """, unsafe_allow_html=True)
    
    # Similarity matches
    if "matches" in results and results["matches"]:
        st.markdown("**Semantic Similarity Matches:**")
        for i, match in enumerate(results["matches"]):
            cv_record = match.get("cv_record", {})
            epf_record = match.get("epf_record", {})
            similarity = match.get("similarity_score", 0)
            
            with st.expander(f"Match {i+1}: {cv_record.get('company', 'Unknown')} (Similarity: {similarity:.3f})"):
                st.write("**CV Record:**")
                # Using .get for safe access
                st.write(f"- Company: {cv_record.get('company', 'N/A')}")
                st.write(f"- Duration: {cv_record.get('date_range', 'N/A')}")
                
                st.write("**EPF Record:**")
                st.write(f"- Company: {epf_record.get('company', 'N/A')}")
                # Handling month and year for EPF record
                epf_date_info = ""
                if 'date_range' in epf_record and epf_record['date_range']:
                    epf_date_info = epf_record['date_range']
                elif 'month' in epf_record and 'year' in epf_record:
                    epf_date_info = f"{epf_record['month']}-{epf_record['year']}"

                st.write(f"- Period: {epf_date_info}")
                st.write(f"- Employee Contribution: ₹{epf_record.get('employee_contribution', 'N/A')}")
                
                # Similarity score with color coding
                score_color = "green" if similarity > 0.8 else "orange" if similarity > 0.6 else "red"
                st.markdown(f"**Similarity Score:** <span style='color: {score_color}; font-weight: bold;'>{similarity:.3f}</span>", unsafe_allow_html=True)
    
    # Employment records breakdown
    with st.expander("📋 Detailed Employment Records"):
        if "cv_records" in results and results["cv_records"]:
            st.markdown("**CV Employment Records:**")
            # Convert datetime objects to string for DataFrame display
            cv_df_display = [{k: str(v) if isinstance(v, datetime) else v for k, v in record.items()} for record in results["cv_records"]]
            cv_df = pd.DataFrame(cv_df_display)
            st.dataframe(cv_df, use_container_width=True)
        else:
            st.info("No CV employment records parsed by RAG.")
        
        if "epf_records" in results and results["epf_records"]:
            st.markdown("**EPF Employment Records:**")
            # Convert datetime objects to string for DataFrame display
            epf_df_display = [{k: str(v) if isinstance(v, datetime) else v for k, v in record.items()} for record in results["epf_records"]]
            epf_df = pd.DataFrame(epf_df_display)
            st.dataframe(epf_df, use_container_width=True)
        else:
            st.info("No EPF employment records parsed by RAG.")

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🔍 Document Verification System With RAG and Intelligent REGEx For Employment BG Check</h1>
        <p>AI-powered CV and PF document verification using Ollama & Gemma 2B</p>
        <p>Upload CV and PF documents to start verification. Due to RAG and intelligent string regex process can take considerable amount of time depends on CV and PF pdf size.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("📂 Upload Documents")
        st.markdown("Upload both CV and PF documents to start verification")
        
        cv_file = st.file_uploader(
            "Upload CV (PDF)", 
            type=['pdf'], 
            help="Upload the candidate's CV in PDF format"
        )
        
        pf_file = st.file_uploader(
            "Upload PF Statement (PDF)", 
            type=['pdf'], 
            help="Upload the PF statement in PDF format"
        )

        # Verification settings
        st.markdown("---")
        st.subheader("⚙️ Verification Settings")
        
        # Note: Similarity threshold is configured in rag_employment_verification.py
        # If you want it dynamic from UI, you would pass it to EmploymentRAGVerifier
        # For now, it's hardcoded in the verifier.
        
        if st.button("🔍 Start Verification", type="primary"):
            if cv_file and pf_file:
                st.session_state.start_verification = True
                st.session_state.cv_file = cv_file
                st.session_state.pf_file = pf_file
            else:
                st.error("Please upload both documents first!")
                logger.warning("One or both files missing when button clicked.")
    
    # Main content area
    if hasattr(st.session_state, 'start_verification') and st.session_state.start_verification:
        logger.info("Session state 'start_verification' is True. Calling process_documents().")
        process_documents()
        # Reset the session state to prevent re-running on refresh
        st.session_state.start_verification = False 
    else:
        logger.info("Session state 'start_verification' is not True or not set. Showing welcome screen.")
        show_welcome_screen()

def show_welcome_screen():
    st.markdown("""
    <div class="info-box">
        <h3>🚀 Welcome to Document Verification System</h3>
        <p>This system uses AI to verify employment history by comparing CV and PF documents:</p>
        <ul>
            <li><strong>CV Analysis:</strong> Extracts employment history, dates, and company information</li>
            <li><strong>PF Verification:</strong> Cross-references with official PF records</li>
            <li><strong>Smart Matching:</strong> Uses AI to identify discrepancies and calculate match scores</li>
        </ul>
        <p>📋 <strong>Instructions:</strong> Upload both documents using the sidebar to begin verification.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show sample data structure
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 Expected CV Format")
        st.code("""
        Professional Experience:
        - Company Name, Location | Duration
        - Job responsibilities and achievements
        
        Example:
        Java Developer
        ABC Tech Solutions, City | 2021 – Present
        - Developed RESTful microservices...
        """)
    
    with col2:
        st.subheader("📊 Expected PF Format")
        st.code("""
        Employment & Contribution History:
        Period | Employer Name | Contributions
        
        Example:
        03/2021 – Present | ABC Tech Solutions
        Employee Contribution: ₹1,32,500
        """)

# Function to process documents with both string and RAG comparison
def process_documents():
    st.header("🔄 Processing Documents...")

    progress_bar = st.progress(0)
    status_text = st.empty()

    cv_local_path = None
    pf_local_path = None

    try:
        # Step 0: Save uploaded files
        status_text.text("Saving uploaded files...")
        progress_bar.progress(10)

        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)

        cv_local_path = os.path.join(upload_dir, st.session_state.cv_file.name)
        pf_local_path = os.path.join(upload_dir, st.session_state.pf_file.name)

        save_uploaded_file(st.session_state.cv_file, cv_local_path)
        save_uploaded_file(st.session_state.pf_file, pf_local_path)
        logger.info(f"Files saved: {cv_local_path}, {pf_local_path}")

        # Step 1: Initialize verification engines
        status_text.text("Initializing verification engines...")
        progress_bar.progress(20)

        verification_engine = DocumentMatcher()
        rag_verifier = EmploymentRAGVerifier(
            ollama_host=os.getenv("OLLAMA_HOST", "http://ollama:11434")
        )

        # Step 2: Extract plain text from PDF files
        status_text.text("Extracting raw text from PDFs...")
        progress_bar.progress(30)

        cv_data_text = pdf_extractor.extract_pdf_text(cv_local_path)
        pf_data_text = pdf_extractor.extract_pdf_text(pf_local_path)

        # Step 3: Extract structured CV and PF data (for UI display only)
        status_text.text("Parsing structured CV and PF data...")
        progress_bar.progress(40)

        cv_data = pdf_extractor.extract_cv_info(cv_data_text)
        pf_data = pdf_extractor.extract_pf_info(pf_data_text)

        # Step 4: Perform string-based document verification
        status_text.text("Performing string-based verification...")
        progress_bar.progress(60)

        string_based_results = verification_engine.verify_documents(cv_data, pf_data)
        string_based_results = format_verification_results(string_based_results)
        logger.info("String-based verification completed.")

        # Step 5: Perform RAG-based semantic verification
        status_text.text("Performing RAG-based verification...")
        progress_bar.progress(80)

        rag_based_results = rag_verifier.process_documents(cv_local_path, pf_local_path)
        logger.info("RAG-based verification completed.")

        # Step 6: Prepare combined results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        combined_results = {
            "timestamp": timestamp,
            "files": {
                "cv": st.session_state.cv_file.name,
                "pf": st.session_state.pf_file.name
            },
            "string_based_results": string_based_results,
            "rag_based_results": rag_based_results
        }

        # Step 7: Save combined results to JSON
        os.makedirs("output", exist_ok=True)
        results_file = f"output/verification_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(combined_results, f, indent=4, default=str)

        # Step 8: Display results
        status_text.text("✅ Verification completed!")
        progress_bar.progress(100)
        display_results(cv_data, pf_data, combined_results)

        # Clean up progress indicators
        progress_bar.empty()
        status_text.empty()

    except Exception as e:
        st.error(f"Error processing documents: {str(e)}")
        st.exception(e)
    finally:
        try:
            if cv_local_path and os.path.exists(cv_local_path):
                os.remove(cv_local_path)
            if pf_local_path and os.path.exists(pf_local_path):
                os.remove(pf_local_path)
        except Exception as e:
            st.warning(f"Could not clean up temporary files: {e}")


def display_results(cv_data, pf_data, combined_results):
    st.header("📊 Verification Results")
    
    # Overall match score - now from string_based_results
    string_based_overall_score = combined_results.get('string_based_results', {}).get('overall_score', 0)
    
    score_class = "score-high" if string_based_overall_score >= 80 else "score-medium" if string_based_overall_score >= 60 else "score-low"
    
    st.markdown(f"""
    <div class="match-score {score_class}">
        String-based Overall Match Score: {string_based_overall_score}%
    </div>
    """, unsafe_allow_html=True)
    
    # Detailed results in tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Summary", "📄 CV Data", "📊 PF Data", "🔍 String-based Analysis", "🧠 RAG-based Analysis"])
    
    with tab1:
        # Assuming display_summary handles string_based_results
        display_summary(combined_results.get('string_based_results', {}))
    
    with tab2:
        display_cv_data(cv_data)
    
    with tab3:
        display_pf_data(pf_data)
    
    with tab4:
        display_detailed_analysis(combined_results.get('string_based_results', {}))

    with tab5:
        display_rag_results(combined_results.get('rag_based_results', {})) # Call the RAG display function

def display_summary(verification_results):
    from datetime import datetime

    st.subheader("📋 String-based Verification Summary")

    # Show main metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Overall Score", f"{verification_results.get('overall_score', 0)}%")
    with col2:
        st.metric("Matched Periods", verification_results.get("matched_periods", 0))
    with col3:
        st.metric("Discrepancies", verification_results.get("discrepancies", 0))
    with col4:
        st.metric("Missing Records", verification_results.get("missing_records", 0))

    # Show detailed mismatch report if available
    if "period_analysis" in verification_results:
        st.subheader("📆 Period Gap & Overlap Report")
        for period in verification_results["period_analysis"]:
            cv_start = period.get("cv_start")
            cv_end = period.get("cv_end")
            pf_start = period.get("pf_start")
            pf_end = period.get("pf_end")

            # Handle "Present"
            if cv_end and cv_end.lower() == "present":
                cv_end = datetime.now().strftime("%m/%Y")
            if pf_end and pf_end.lower() == "present":
                pf_end = datetime.now().strftime("%m/%Y")

            with st.expander(f"Period: {period.get('period', 'Unknown')}"):
                st.write(f"**CV Company:** {period.get('cv_company', 'N/A')}")
                st.write(f"**PF Company:** {period.get('pf_company', 'N/A')}")
                st.write(f"**Match Score:** {period.get('match_score', 0)}%")
                st.write(f"**CV Duration:** {cv_start} to {cv_end}")
                st.write(f"**PF Duration:** {pf_start} to {pf_end}")

                if period.get("discrepancies"):
                    st.warning("Discrepancies:")
                    for d in period["discrepancies"]:
                        st.write(f"- {d}")

    # AI insights if available
    if verification_results.get("ai_analysis"):
        st.subheader("🧠 AI Insights")
        st.info(verification_results["ai_analysis"])

    # Recommendations
    if verification_results.get("recommendations"):
        st.subheader("💡 Recommendations")
        for rec in verification_results["recommendations"]:
            st.success(f"• {rec}")


def display_cv_data(cv_data):
    st.subheader("📄 Extracted CV Information")
    
    # Personal Information
    if cv_data.get('personal_info'):
        st.write("**Personal Information:**")
        st.json(cv_data['personal_info'])
    
    # Employment History
    if cv_data.get('employment_history'):
        st.write("**Employment History:**")
        df = pd.DataFrame(cv_data['employment_history'])
        st.dataframe(df, use_container_width=True)
    
    # Skills
    if cv_data.get('skills'):
        st.write("**Skills:**")
        st.write(", ".join(cv_data['skills']))

def display_pf_data(pf_data):
    st.subheader("📊 Extracted PF Information")
    
    # Account Information
    if pf_data.get('account_info'):
        st.write("**Account Information:**")
        st.json(pf_data['account_info'])
    
    # Employment Records
    if pf_data.get('employment_records'):
        st.write("**Employment Records:**")
        df = pd.DataFrame(pf_data['employment_records'])
        st.dataframe(df, use_container_width=True)
        
        # Create visualization
        create_pf_visualization(pf_data['employment_records'])

def create_pf_visualization(employment_records):
    # Ensure all date fields are convertible to datetime objects for plotting
    plot_records = []
    for record in employment_records:
        start_date = None
        end_date = None
        try:
            if 'start_period' in record and record['start_period']:
                # Attempt to parse common date formats like MM/YYYY, YYYY
                if re.match(r'\d{2}/\d{4}', record['start_period']):
                    start_date = datetime.strptime(record['start_period'], '%m/%Y')
                elif re.match(r'\d{4}', record['start_period']):
                    start_date = datetime.strptime(record['start_period'], '%Y')
                else:
                    # Fallback for other formats, use a more flexible parser if available
                    pass # Keep as None or handle
        except ValueError:
            pass

        try:
            if 'end_period' in record and record['end_period'].lower() != 'present' and record['end_period']:
                if re.match(r'\d{2}/\d{4}', record['end_period']):
                    end_date = datetime.strptime(record['end_period'], '%m/%Y')
                elif re.match(r'\d{4}', record['end_period']):
                    end_date = datetime.strptime(record['end_period'], '%Y')
                else:
                    pass # Keep as None or handle
            elif record.get('end_period', '').lower() == 'present':
                end_date = datetime.now() # Use current date for 'Present'
        except ValueError:
            pass

        if start_date: # Only add if we have a valid start date
            plot_records.append({
                'start_date': start_date,
                'end_date': end_date,
                'employer_name': record.get('employer', 'Unknown Company')
            })

    if not plot_records:
        st.info("Not enough valid date data in PF records to create a timeline visualization.")
        return
    
    # Create timeline visualization
    fig = go.Figure()
    
    for i, record in enumerate(plot_records):
        # Handle cases where end_date might be None (e.g., "Present" or unparseable)
        x_values = [record['start_date']]
        if record['end_date']:
            x_values.append(record['end_date'])
        else:
            # If end date is 'Present' or unparseable, extend to current time or a reasonable future date for visualization
            x_values.append(datetime.now()) # Or a fixed future date like `datetime(datetime.now().year + 1, 1, 1)`

        fig.add_trace(go.Scatter(
            x=x_values,
            y=[record['employer_name']] * len(x_values), # Repeat employer name for start and end points
            mode='lines+markers',
            name=record['employer_name'],
            line=dict(width=6),
            marker=dict(size=8)
        ))
    
    fig.update_layout(
        title="Employment Timeline from PF Records",
        xaxis_title="Period",
        yaxis_title="Employer",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_detailed_analysis(verification_results):
    st.subheader("🔍 Detailed Analysis")
    
    # Period-wise comparison
    if verification_results.get('period_analysis'):
        st.write("**Period-wise Comparison:**")
        for period in verification_results['period_analysis']:
            with st.expander(f"Period: {period.get('period', 'Unknown')}"):
                st.write(f"**Match Score:** {period.get('match_score', 0)}%")
                st.write(f"**CV Company:** {period.get('cv_company', 'Not found')}")
                st.write(f"**PF Company:** {period.get('pf_company', 'Not found')}")
                if period.get('discrepancies'):
                    st.write("**Discrepancies:**")
                    for disc in period['discrepancies']:
                        st.write(f"• {disc}")
    
    # AI Analysis (from string-based)
    if verification_results.get('ai_analysis'):
        st.write("**AI Analysis:**")
        st.text_area("Detailed AI Analysis", verification_results['ai_analysis'], height=200)

if __name__ == "__main__":
    main()