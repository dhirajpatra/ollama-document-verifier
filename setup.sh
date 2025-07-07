#!/bin/bash

# Document Verification Setup Script with RAG Support

echo "🚀 Setting up Document Verification System with RAG..."

# Create project structure with existence checks
echo "📂 Creating project directories..."
for dir in uploads output ollama_data ollama models; do
    if [ -d "$dir" ]; then
        echo "   ✔ $dir already exists"
    else
        if mkdir -p "$dir"; then
            echo "   ✔ Created $dir"
        else
            echo "   ❌ Failed to create $dir"
            exit 1
        fi
    fi
done

# Create .env file if it doesn't exist
if [ -f ".env" ]; then
    echo "   ✔ .env already exists"
else
    cat > .env << EOF
OLLAMA_URL=http://ollama:11434
MODEL_NAME=gemma:2b
SENTENCE_TRANSFORMER_MODEL=all-MiniLM-L6-v2
SIMILARITY_THRESHOLD=0.7
EOF
    echo "   ✔ Created .env file"
fi

# Create .gitignore if it doesn't exist
if [ -f ".gitignore" ]; then
    echo "   ✔ .gitignore already exists"
else
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
    echo "   ✔ Created .gitignore file"
fi

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
    
    if docker exec ollama ollama list 2>/dev/null | grep -q "gemma:2b"; then
        echo "✅ gemma:2b model is already available"
        return 0
    else
        echo "⬇️  gemma:2b model not found, pulling..."
        if docker exec ollama ollama pull gemma:2b 2>/dev/null; then
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
    if docker ps 2>/dev/null | grep -q "document_verifier"; then
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
" 2>/dev/null
        
        if [ $? -eq 0 ]; then
            echo "✅ Sentence transformer model is ready"
            return 0
        else
            echo "❌ Failed to download sentence transformer model"
            return 1
        fi
    else
        echo "⚠️  Streamlit container not running - will retry later"
        return 1
    fi
}

# Function to verify system readiness
verify_system_readiness() {
    echo "🔍 Verifying system readiness..."
    
    # Check if containers are running
    if docker ps 2>/dev/null | grep -q "ollama" && docker ps 2>/dev/null | grep -q "document_verifier"; then
        echo "✅ All containers are running"
        
        # Test Ollama API
        if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo "✅ Ollama API is accessible"
        else
            echo "⚠️  Ollama API is not accessible yet - retrying..."
            sleep 5
            if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
                echo "✅ Ollama API is now accessible"
            else
                echo "❌ Ollama API is not accessible"
                return 1
            fi
        fi
        
        # Test Streamlit
        if curl -s http://localhost:8501 > /dev/null 2>&1; then
            echo "✅ Streamlit is accessible"
        else
            echo "⚠️  Streamlit may still be starting up"
            sleep 5
            if curl -s http://localhost:8501 > /dev/null 2>&1; then
                echo "✅ Streamlit is now accessible"
            else
                echo "⚠️  Streamlit still not accessible - check logs with 'docker compose logs document_verifier'"
            fi
        fi
        
        return 0
    else
        echo "⚠️  Not all containers are running yet - retrying..."
        sleep 5
        if docker ps 2>/dev/null | grep -q "ollama" && docker ps 2>/dev/null | grep -q "document_verifier"; then
            echo "✅ All containers are now running"
            return 0
        else
            echo "❌ Containers failed to start"
            return 1
        fi
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
    grep -v '^#' .env | sed '/^$/d'
    echo ""
    echo "📊 Container Status:"
    docker compose ps 2>/dev/null || echo "⚠️  Docker compose not running"
    echo ""
    echo "💾 Disk Usage:"
    docker system df 2>/dev/null || echo "⚠️  Docker not available"
}

# Function to setup and verify everything
setup_and_verify() {
    echo "🚀 Starting Docker containers..."
    
    # Start containers
    if docker compose up --build -d; then
        docker compose ps
        echo "✅ Containers started successfully in detached mode"
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
            
            # Download sentence transformer model (with retry)
            echo "🔄 Attempting to download sentence transformer model..."
            local retry_count=0
            local max_retries=3
            
            while [ $retry_count -lt $max_retries ]; do
                if download_sentence_transformer; then
                    break
                fi
                ((retry_count++))
                if [ $retry_count -lt $max_retries ]; then
                    echo "🔄 Retrying in 10 seconds... (attempt $retry_count/$max_retries)"
                    sleep 10
                fi
            done
            
            if [ $retry_count -eq $max_retries ]; then
                echo "⚠️  Failed to download sentence transformer model after $max_retries attempts"
                echo "💡 The system may still work, but with reduced performance"
            else
                echo "✅ Sentence transformer model ready"
            fi
            
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
            echo "❌ Gemma model setup failed"
            exit 1
        fi
    else
        echo "❌ Ollama setup failed"
        echo "💡 Check logs: docker compose logs ollama"
        exit 1
    fi
}

# Function to clean up system
cleanup_system() {
    echo "🧹 Cleaning up system..."
    docker compose down 2>/dev/null || echo "⚠️  No containers to stop"
    docker rmi $(docker images -f "dangling=true" -q) 2>/dev/null || echo "⚠️  No dangling images to remove"
    docker system prune -f 2>/dev/null || echo "⚠️  Docker prune failed"
    echo "✅ Cleanup completed"
}

# Main script execution
echo "✅ Project setup completed!"
echo "📁 Location: $(pwd)"
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
    echo "🧹 To cleanup, run: $0 cleanup"
fi

echo ""
echo "🎯 Setup completed! Happy document verification! 🎯"