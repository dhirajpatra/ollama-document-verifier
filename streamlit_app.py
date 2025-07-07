import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from document_extractor import DocumentExtractor
from verification_engine import VerificationEngine
from utils import save_uploaded_file, format_verification_results
import plotly.graph_objects as go
from plotly.subplots import make_subplots
# Import the RAG verification script
from rag_employment_verification import EmploymentRAGVerifier


# Page configuration
st.set_page_config(
    page_title="Document Verification System",
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

# Function to process documents with RAG-based verification
def rag_process_documents():
    """Process uploaded documents with both string-based and RAG-based verification"""
    st.markdown("## 📊 Document Verification Results")
    
    # Save uploaded files
    cv_path = save_uploaded_file(st.session_state.cv_file)
    pf_path = save_uploaded_file(st.session_state.pf_file)
    
    # Create progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Initialize verification results
    string_results = None
    rag_results = None
    
    try:
        # Step 1: String-based verification (existing logic)
        status_text.text("🔍 Starting string-based verification...")
        progress_bar.progress(10)
        
        # Initialize RAG verifier
        rag_verifier = EmploymentRAGVerifier(
            ollama_host=os.getenv("OLLAMA_HOST", "http://ollama:11434")
        )
        
        status_text.text("📄 Processing documents with RAG...")
        progress_bar.progress(70)
        
        # Process documents with RAG
        rag_results = rag_verifier.process_documents(cv_path, pf_path)
        progress_bar.progress(90)
        
        return rag_results
        
    except Exception as e:
        st.error(f"Error during verification: {str(e)}")
        st.exception(e)
    
    finally:
        # Clean up uploaded files
        try:
            os.remove(cv_path)
            os.remove(pf_path)
        except:
            pass

def display_rag_results(results):
    """Display RAG-based verification results"""
    if not results:
        st.error("No RAG-based results available")
        return
    
    # Summary statistics
    summary = results.get("verification_summary", {})
    status_color = "green" if summary.get("status") == "VERIFIED" else "orange"
    
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
                st.write(f"- Company: {cv_record.get('company', 'N/A')}")
                st.write(f"- Duration: {cv_record.get('date_range', 'N/A')}")
                
                st.write("**EPF Record:**")
                st.write(f"- Company: {epf_record.get('company', 'N/A')}")
                st.write(f"- Month/Year: {epf_record.get('month', 'N/A')}-{epf_record.get('year', 'N/A')}")
                st.write(f"- Contribution: ₹{epf_record.get('employee_contribution', 'N/A')}")
                
                # Similarity score with color coding
                score_color = "green" if similarity > 0.8 else "orange" if similarity > 0.6 else "red"
                st.markdown(f"**Similarity Score:** <span style='color: {score_color}; font-weight: bold;'>{similarity:.3f}</span>", unsafe_allow_html=True)
    
    # Employment records breakdown
    with st.expander("📋 Detailed Employment Records"):
        if "cv_records" in results:
            st.markdown("**CV Employment Records:**")
            cv_df = pd.DataFrame(results["cv_records"])
            if not cv_df.empty:
                st.dataframe(cv_df)
        
        if "epf_records" in results:
            st.markdown("**EPF Employment Records:**")
            epf_df = pd.DataFrame(results["epf_records"])
            if not epf_df.empty:
                st.dataframe(epf_df)

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🔍 Document Verification System</h1>
        <p>AI-powered CV and PF document verification using Ollama & Gemma 2B</p>
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
        
        similarity_threshold = st.slider(
            "RAG Similarity Threshold",
            min_value=0.5,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="Minimum similarity score for RAG matching"
        )
        
        if st.button("🔍 Start Verification", type="primary"):
            if cv_file and pf_file:
                st.session_state.start_verification = True
                st.session_state.cv_file = cv_file
                st.session_state.pf_file = pf_file
            else:
                st.error("Please upload both documents first!")
    
    # Main content area
    if hasattr(st.session_state, 'start_verification') and st.session_state.start_verification:
        process_documents()
    else:
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

# Function to process documents by string comparison and display results
def process_documents():
    st.header("🔄 Processing Documents...")
    
    # Initialize progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # Save uploaded files
        status_text.text("Saving uploaded files...")
        progress_bar.progress(10)
        
        cv_path = save_uploaded_file(st.session_state.cv_file, "cv.pdf")
        pf_path = save_uploaded_file(st.session_state.pf_file, "pf.pdf")
        
        # Initialize extractors
        status_text.text("Initializing document extractors...")
        progress_bar.progress(20)
        
        extractor = DocumentExtractor()
        verification_engine = VerificationEngine()
        
        # Extract CV data
        status_text.text("Extracting CV information...")
        progress_bar.progress(40)
        
        cv_data = extractor.extract_cv_data(cv_path)
        
        # Extract PF data
        status_text.text("Extracting PF information...")
        progress_bar.progress(60)
        
        pf_data = extractor.extract_pf_data(pf_path)
        
        # Perform verification
        status_text.text("Performing AI-powered verification...")
        progress_bar.progress(80)
        
        verification_results = verification_engine.verify_documents(cv_data, pf_data)
        
        # Display results
        status_text.text("Generating verification report...")
        progress_bar.progress(100)

        # get rag results
        rag_results = rag_process_documents()
        
        combined_results = {
            "timestamp": timestamp,
            "files": {
                "cv": st.session_state.cv_file.name,
                "pf": st.session_state.pf_file.name
            },
            "string_based_results": verification_results,
            "rag_based_results": rag_results
        }

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"output/verification_results_{timestamp}.json"
        
        status_text.text("✅ Verification completed!")
        progress_bar.progress(100)
        
        # Display results
        display_results(cv_data, pf_data, combined_results)
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
    except Exception as e:
        st.error(f"Error processing documents: {str(e)}")
        st.exception(e)

def display_results(cv_data, pf_data, verification_results):
    st.header("📊 Verification Results")
    
    # Overall match score
    overall_score = verification_results.get('overall_score', 0)
    
    score_class = "score-high" if overall_score >= 80 else "score-medium" if overall_score >= 60 else "score-low"
    
    st.markdown(f"""
    <div class="match-score {score_class}">
        Overall Match Score: {overall_score}%
    </div>
    """, unsafe_allow_html=True)
    
    # Detailed results in tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Summary", "📄 CV Data", "📊 PF Data", "🔍 Detailed Analysis"])
    
    with tab1:
        display_summary(verification_results)
    
    with tab2:
        display_cv_data(cv_data)
    
    with tab3:
        display_pf_data(pf_data)
    
    with tab4:
        display_detailed_analysis(verification_results)

def display_summary(verification_results):
    st.subheader("📋 Verification Summary")
    
    # Create metrics columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Overall Score", 
            f"{verification_results.get('overall_score', 0)}%",
            delta=f"{verification_results.get('overall_score', 0) - 70}%" if verification_results.get('overall_score', 0) > 70 else None
        )
    
    with col2:
        st.metric(
            "Matched Periods", 
            verification_results.get('matched_periods', 0)
        )
    
    with col3:
        st.metric(
            "Discrepancies", 
            verification_results.get('discrepancies', 0)
        )
    
    with col4:
        st.metric(
            "Missing Records", 
            verification_results.get('missing_records', 0)
        )
    
    # Issues and recommendations
    if verification_results.get('issues'):
        st.subheader("⚠️ Issues Found")
        for issue in verification_results['issues']:
            st.warning(f"• {issue}")
    
    if verification_results.get('recommendations'):
        st.subheader("💡 Recommendations")
        for rec in verification_results['recommendations']:
            st.info(f"• {rec}")

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
    if not employment_records:
        return
    
    # Create timeline visualization
    fig = go.Figure()
    
    for i, record in enumerate(employment_records):
        fig.add_trace(go.Scatter(
            x=[record.get('start_date', ''), record.get('end_date', 'Present')],
            y=[record.get('employer_name', f'Company {i+1}')] * 2,
            mode='lines+markers',
            name=record.get('employer_name', f'Company {i+1}'),
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
    
    # AI Analysis
    if verification_results.get('ai_analysis'):
        st.write("**AI Analysis:**")
        st.text_area("Detailed AI Analysis", verification_results['ai_analysis'], height=200)

if __name__ == "__main__":
    main()