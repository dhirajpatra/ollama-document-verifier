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
   ```bash
   ./setup.sh
   ```

2. Or manually build and run:
   ```bash
   docker-compose up --build
   ```

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
