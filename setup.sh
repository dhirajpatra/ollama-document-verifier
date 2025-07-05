#!/bin/bash

# Document Verification Setup Script

echo "🚀 Setting up Document Verification System..."

# Create project structure
mkdir -p document-verification/{uploads,output,ollama_data,ollama}
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

# Function to check if Ollama is ready
check_ollama_ready() {
    local max_attempts=30
    local attempt=1
    
    echo "🔍 Checking if Ollama is ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo "✅ Ollama API is responding"
            return 0
        else
            echo "⏳ Attempt $attempt/$max_attempts - Waiting for Ollama..."
            sleep 2
            ((attempt++))
        fi
    done
    
    echo "❌ Ollama failed to start after $max_attempts attempts"
    return 1
}

# Function to check if gemma:2b model exists
check_gemma_model() {
    echo "🔍 Checking for gemma:2b model..."
    
    if docker exec ollama ollama list | grep -q "gemma:2b"; then
        echo "✅ gemma:2b model is already available"
        return 0
    else
        echo "⬇️  gemma:2b model not found, pulling..."
        if docker exec ollama ollama pull gemma:2b; then
            echo "✅ gemma:2b model downloaded successfully"
            return 0
        else
            echo "❌ Failed to download gemma:2b model"
            return 1
        fi
    fi
}

# Function to setup and verify everything
setup_and_verify() {
    echo "🚀 Starting Docker containers..."
    
    # Start containers
    if docker compose up -d; then
        echo "✅ Containers started"
    else
        echo "❌ Failed to start containers"
        exit 1
    fi
    
    # Check if Ollama is ready
    if check_ollama_ready; then
        # Check/pull gemma model
        if check_gemma_model; then
            echo "🎉 System is ready!"
            echo "🌐 Access Streamlit at: http://localhost:8501"
            echo "🤖 Ollama API at: http://localhost:11434"
            
            # Show container status
            echo ""
            echo "📊 Container Status:"
            docker compose ps
            
        else
            echo "❌ Model setup failed"
            exit 1
        fi
    else
        echo "❌ Ollama setup failed"
        echo "💡 Check logs: docker logs ollama"
        exit 1
    fi
}

echo "✅ Project structure created!"
echo "📁 Location: document-verification/"
echo ""

# Ask user if they want to start the system
read -p "🚀 Do you want to start the system now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    setup_and_verify
else
    echo "💡 To start later, run: docker-compose up --build"
    echo "🌐 Then access: http://localhost:8501"
fi