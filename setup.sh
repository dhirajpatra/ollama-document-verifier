#!/bin/bash

# Document Verification Setup Script

echo "🚀 Setting up Document Verification System..."

# Create project structure
mkdir -p document-verification/{uploads,output,ollama_data}
cd document-verification

# Create .env file
cat > .env << EOF
OLLAMA_URL=http://ollama:11434
MODEL_NAME=gemma:2b
EOF

# Create .gitignore
cat > .gitignore << EOF
uploads/
output/
ollama_data/
__pycache__/
*.pyc
*.pyo
*.pyd
.env
.venv/
venv/
*.log
EOF

# Create README
cat > README.md << EOF
# Document Verification System

AI-powered document verification system using Ollama and Streamlit.

## Setup

1. Build and run with Docker Compose:
   \`\`\`bash
   docker-compose up --build
   \`\`\`

2. Access the application:
   - Streamlit UI: http://localhost:8501
   - Ollama API: http://localhost:11434

## Usage

1. Upload CV PDF
2. Upload PF Statement PDF
3. Click "Verify Documents"
4. View matching results and AI analysis

## Features

- PDF text extraction
- Employment history matching
- AI-powered analysis using Gemma 2B
- Detailed verification reports
EOF

echo "✅ Setup complete!"
echo "📁 Project structure created in: document-verification/"
echo "🐳 Run: docker-compose up --build"
echo "🌐 Access: http://localhost:8501"