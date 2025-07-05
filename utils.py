import os
import streamlit as st
from typing import BinaryIO

def create_directories():
    """Create necessary directories"""
    directories = ['uploads', 'output', 'ollama_data']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)

def save_uploaded_file(uploaded_file: BinaryIO, filename: str) -> str:
    """Save uploaded file to uploads directory"""
    file_path = os.path.join('uploads', filename)
    
    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path

def cleanup_files():
    """Clean up uploaded files"""
    upload_dir = 'uploads'
    if os.path.exists(upload_dir):
        for file in os.listdir(upload_dir):
            file_path = os.path.join(upload_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)