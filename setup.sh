#!/bin/bash

# Document Verification Setup Script with RAG Support

echo "🚀 Setting up Document Verification System with RAG..."

# Create project structure
mkdir -p document-verification/{uploads,output,ollama_data,ollama,models}
cd document-verification

# Create .env file
cat > .env << EOF
OLLAMA_URL=http://ollama:11434
MODEL_NAME=gemma:2b
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
SIMILARITY_THRESHOLD=0.7
EOF

# Create .gitignore
cat > .gitignore << EOF
uploads/
output/
ollama_data/
models/
__pycache__/
*.pyc
*.pyo
*.pyd
.env
.venv/
venv/
*.log
.DS_Store
EOF

# Create README
cat > README.md << EOF
# Document Verification System with RAG

AI-powered document verification system using Ollama, Streamlit, and RAG (Retrieval Augmented Generation).

## Features

- PDF text extraction and parsing
- Employment history matching using semantic similarity
- RAG-based verification with sentence transformers
- AI-powered analysis using Gemma 2B
- Detailed verification reports with confidence scores
- Semantic search instead of simple string matching

## Setup

1. Run the setup script:
   \`\`\`bash
   ./setup.sh
   \`\`\`

2. Or manually build and run:
   \`\`\`bash
   docker-compose up --build
   \`\`\`

3. Access the application:
   - Streamlit UI: http://localhost:8501
   - Ollama API: http://localhost:11434

## Usage

1. Upload CV PDF
2. Upload PF Statement PDF
3. Click "Verify Documents"
4. View matching results and AI analysis with similarity scores

## Technical Stack

- **Frontend**: Streamlit
- **LLM**: Ollama with Gemma 2B
- **Embeddings**: SentenceTransformers (all-MiniLM-L6-v2)
- **Similarity**: Cosine similarity with configurable threshold
- **Containerization**: Docker & Docker Compose

## Models Used

- **LLM Model**: gemma:2b (for text generation and analysis)
- **Embedding Model**: all-MiniLM-L6-v2 (for semantic similarity)
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

# Function to pre-download sentence transformer model
download_sentence_transformer() {
    echo "🔍 Checking for sentence transformer model..."
    
    # Check if the streamlit container is running
    if docker ps | grep -q "document_verifier"; then
        echo "⬇️  Pre-downloading sentence transformer model (all-MiniLM-L6-v2)..."
        echo "📝 This may take a few minutes on first run..."
        
        # Run python script to download the model
        docker exec document_verifier python3 -c "
import os
from sentence_transformers import SentenceTransformer
print('🔄 Downloading sentence transformer model...')
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print('✅ Sentence transformer model downloaded successfully')
    print(f'📦 Model cached at: {model.cache_folder}')
except Exception as e:
    print(f'❌ Error downloading model: {e}')
    exit(1)
"
        
        if [ $? -eq 0 ]; then
            echo "✅ Sentence transformer model is ready"
            return 0
        else
            echo "❌ Failed to download sentence transformer model"
            return 1
        fi
    else
        echo "❌ Streamlit container not running"
        return 1
    fi
}

# Function to verify system readiness
verify_system_readiness() {
    echo "🔍 Verifying system readiness..."
    
    # Check if containers are running
    if docker ps | grep -q "ollama" && docker ps | grep -q "document_verifier"; then
        echo "✅ All containers are running"
        
        # Test Ollama API
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo "✅ Ollama API is accessible"
        else
            echo "❌ Ollama API is not accessible"
            return 1
        fi
        
        # Test Streamlit
        if curl -s http://localhost:8501 > /dev/null 2>&1; then
            echo "✅ Streamlit is accessible"
        else
            echo "⚠️  Streamlit may still be starting up"
        fi
        
        return 0
    else
        echo "❌ Not all containers are running"
        return 1
    fi
}

# Function to show system information
show_system_info() {
    echo ""
    echo "📊 System Information:"
    echo "===================="
    echo "🌐 Streamlit UI: http://localhost:8501"
    echo "🤖 Ollama API: http://localhost:11434"
    echo "📁 Upload Directory: ./uploads/"
    echo "📄 Output Directory: ./output/"
    echo ""
    echo "🔧 Configuration:"
    echo "- LLM Model: gemma:2b"
    echo "- Embedding Model: all-MiniLM-L6-v2"
    echo "- Similarity Threshold: 0.7"
    echo ""
    echo "📊 Container Status:"
    docker compose ps
    echo ""
    echo "💾 Disk Usage:"
    docker system df
}

# Function to setup and verify everything
setup_and_verify() {
    echo "🚀 Starting Docker containers..."
    
    # Start containers
    if docker compose up -d --build; then
        echo "✅ Containers started successfully"
    else
        echo "❌ Failed to start containers"
        exit 1
    fi
    
    # Wait a bit for containers to fully initialize
    echo "⏳ Waiting for containers to initialize..."
    sleep 10
    
    # Check if Ollama is ready
    if check_ollama_ready; then
        # Check/pull gemma model
        if check_gemma_model; then
            echo "✅ Ollama and Gemma model ready"
            
            # Download sentence transformer model
            if download_sentence_transformer; then
                echo "✅ Sentence transformer model ready"
                
                # Final system verification
                if verify_system_readiness; then
                    echo ""
                    echo "🎉 System is fully ready!"
                    show_system_info
                    
                    echo ""
                    echo "🚀 You can now:"
                    echo "  1. Open http://localhost:8501 in your browser"
                    echo "  2. Upload CV and EPF documents"
                    echo "  3. Run RAG-based verification"
                    echo ""
                    echo "📝 Logs:"
                    echo "  - View logs: docker compose logs -f"
                    echo "  - Stop system: docker compose down"
                    
                else
                    echo "❌ System verification failed"
                    exit 1
                fi
            else
                echo "❌ Sentence transformer setup failed"
                echo "💡 The system may still work, but with reduced performance"
                show_system_info
            fi
        else
            echo "❌ Gemma model setup failed"
            exit 1
        fi
    else
        echo "❌ Ollama setup failed"
        echo "💡 Check logs: docker logs ollama"
        exit 1
    fi
}

# Function to clean up system
cleanup_system() {
    echo "🧹 Cleaning up system..."
    docker compose down
    docker system prune -f
    echo "✅ Cleanup completed"
}

# Main script execution
echo "✅ Project structure created!"
echo "📁 Location: document-verification/"
echo ""

# Check if cleanup is requested
if [[ "$1" == "cleanup" ]]; then
    cleanup_system
    exit 0
fi

# Ask user if they want to start the system
read -p "🚀 Do you want to start the RAG-enhanced system now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    setup_and_verify
else
    echo "💡 To start later, run: docker compose up --build"
    echo "🌐 Then access: http://localhost:8501"
    echo "🧹 To cleanup, run: ./setup.sh cleanup"
fi

echo ""
echo "🎯 Setup completed! Happy document verification! 🎯"