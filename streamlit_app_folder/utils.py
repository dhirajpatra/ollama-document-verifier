import os
import streamlit as st
from typing import BinaryIO

def create_directories():
    """Create necessary directories"""
    directories = ['uploads', 'output', 'ollama_data']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)

def save_uploaded_file(uploaded_file: BinaryIO, file_path: str) -> str:
    """Save uploaded file to the given full file path"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path

def cleanup_files(directory='uploads'):
    """Safely delete all files in the specified uploads directory"""
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"✅ Deleted: {file_path}")
            except Exception as e:
                print(f"⚠️ Could not delete {file_path}: {e}")
    else:
        print(f"⚠️ Directory does not exist: {directory}")

def format_verification_results(result: dict) -> dict:
    # Basic scoring logic or a placeholder
    # Fill this logic based on your matcher output schema
    result['overall_score'] = result.get('overall_score', 75)
    result['matched_periods'] = result.get('matched_periods', 1)
    result['discrepancies'] = result.get('discrepancies', 1)
    result['missing_records'] = result.get('missing_records', 1)
    result['issues'] = result.get('issues', ["Some mismatch found"])
    result['recommendations'] = result.get('recommendations', ["Verify missing months with HR"])
    return result
