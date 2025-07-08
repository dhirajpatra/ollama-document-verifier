# Document Verification System

This AI-powered document verification system assists in conducting background checks by comparing employment history data extracted from a Candidate's CV and their Provident Fund (PF) statement. It leverages a combination of Regex-based extraction for structured data and a RAG (Retrieval-Augmented Generation) model powered by Ollama for intelligent analysis and discrepancy detection.

## Key Features

* **PDF Text Extraction:** Robust extraction of text content from both CV and PF statement PDF documents.
* **Regex-based Data Extraction:** Precisely extracts structured information like employment periods, company names, and contribution details from both documents using regular expressions.
* **Employment History Matching:** Compares and identifies matching and mismatching employment periods and company names between the CV and PF statement.
* **AI-Powered Analysis (RAG-based):** Utilizes a local Large Language Model (Gemma 2B via Ollama) to:
    * Perform in-depth analysis of the extracted information.
    * Identify potential discrepancies and inconsistencies in employment records.
    * Provide an overall verification result and actionable recommendations.
* **Detailed Verification Reports:** Generates comprehensive reports outlining the matching status, extracted data, and AI-driven insights.
* **User-Friendly Interface:** A Streamlit-based web application for easy document upload and results visualization.

## How it Works

The system operates in the following steps:

1.  **Document Upload:** Users upload a CV in PDF format and an EPF (Employee Provident Fund) Statement in PDF format through the Streamlit interface.
2.  **Text Extraction:** The `pdf_extractor.py` module extracts all readable text from both uploaded PDFs.
3.  **Structured Data Extraction:** Regular expressions defined in `pdf_extractor.py` (or `data_extractor.py` in the updated structure) are applied to the extracted text to pull out key entities such as:
    * **From CV:** Employer names, job titles, employment start dates, and end dates.
    * **From PF Statement:** Employer names, establishment IDs, contribution periods (start and end dates/months), employee and employer contributions, and pension contributions.
4.  **Data Comparison & Matching:** The `document_matcher.py` (or `verification_engine.py` in the updated structure) compares the extracted employment records from the CV and PF statement, identifying overlaps, discrepancies, and confirming matching periods. Fuzzy matching techniques are employed for company names to account for minor variations.
5.  **AI Analysis (RAG-based):** The system then sends the extracted and compared information, along with the raw text, to the Ollama server. A prompt engineered for document verification tasks leverages the powerful Gemma 2B model to:
    * Provide a qualitative assessment of the employment history match.
    * Elaborate on any identified discrepancies.
    * Offer an overall conclusion and recommendations for further checks if needed.
6.  **Report Generation:** Finally, the `app.py` (or `streamlit_app.py`) displays the verification results in a structured and easy-to-understand format, including the extracted data, matching details, and the AI's analysis.

## Project Structure

```

document-verification/
├── app.py                  \# Main Streamlit application
├── data\_extractor.py       \# (New/Updated) Handles PDF text and structured data extraction (CV & PF)
├── document\_matcher.py     \# (Old) Logic for comparing CV and PF data
├── verification\_engine.py  \# (New) Core logic for matching and AI analysis
├── utils.py                \# Utility functions (file handling, directory creation)
├── requirements.txt        \# Python dependencies
├── Dockerfile              \# Dockerfile for the Streamlit application
├── docker-compose.yaml     \# Defines services (Ollama, Streamlit)
├── setup.sh                \# Script to set up the project (directories, .env, start containers)
├── .env.example            \# Example environment variables
├── .gitignore              \# Files/directories to ignore in Git
├── README.md               \# This file
├── uploads/                \# Directory for uploaded CVs and PF statements (managed by utils.py)
├── output/                 \# Directory for generated reports (if any)
└── ollama/                 \# Contains Dockerfile for Ollama with model pulling (if customized)
└── Dockerfile          \# Custom Dockerfile for Ollama (optional, for pre-pulling models)

````

## Setup and Running the System

To get the Document Verification System up and running, follow these steps:

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd document-verification
    ```

2.  **Run the Setup Script:**
    The `setup.sh` script automates the initial setup process, including creating necessary directories and preparing the Docker environment.

    ```bash
    ./setup.sh
    ```
    This script will:
    * Create the `uploads`, `output`, and `ollama_data` directories.
    * Generate a `.env` file with default Ollama URL and model name.
    * Start the Docker containers (Ollama and Streamlit) in the background.
    * Automatically pull the `gemma:2b` model into the Ollama container.
    * Verify if Ollama is ready.

3.  **Access the Application:**
    Once the `setup.sh` script completes successfully, the system will be ready.

    * **Streamlit UI:** Open your web browser and navigate to `http://localhost:8501`
    * **Ollama API:** The Ollama API will be accessible at `http://localhost:11434` (for debugging or direct interaction).

4.  **Using the Application:**
    * On the Streamlit interface, you will find sections to upload your CV PDF and PF Statement PDF.
    * Click the "Verify Documents" button.
    * The system will process the documents and display the verification results, including a detailed analysis.

## Configuration

The system can be configured using the `.env` file created by `setup.sh`. Key variables include:

* `OLLAMA_HOST`: The URL where the Ollama service is running (e.g., `http://ollama:11434` when running via Docker Compose).
* `MODEL_NAME`: The name of the Ollama model to use for AI analysis (e.g., `gemma:2b`).

## Troubleshooting

* **"Ollama not ready" or "Model pull failed":** Check the Docker logs for the `ollama` container:
    ```bash
    docker logs ollama
    ```
* **Streamlit application not accessible:** Ensure the `streamlit` container is running:
    ```bash
    docker compose ps
    ```
    And check its logs for errors:
    ```bash
    docker logs document_verifier
    ```
* **PDF Extraction Issues:** If text extraction is poor, ensure your PDF documents are text-searchable and not just scanned images. For scanned PDFs, OCR (Optical Character Recognition) might be required (though not directly integrated in the current `pdf_extractor.py`).

## Contributions

We welcome contributions to enhance and improve this Document Verification System! If you'd like to contribute, please follow these guidelines:

1.  **Fork the repository.**
2.  **Create a new branch** for your feature or bug fix: `git checkout -b feature/your-feature-name` or `git checkout -b bugfix/issue-description`.
3.  **Make your changes.** Ensure your code adheres to the existing coding style and includes appropriate tests.
4.  **Commit your changes** with a clear and concise message: `git commit -m "feat: Add new feature"`.
5.  **Push to your fork:** `git push origin feature/your-feature-name`.
6.  **Open a Pull Request** to the `main` branch of the original repository. Provide a detailed description of your changes and why they are necessary.

### Reporting Issues

If you encounter any bugs, have feature requests, or suggestions for improvement, please open an issue on the GitHub repository. When reporting a bug, provide:

* A clear and concise description of the issue.
* Steps to reproduce the behavior.
* Expected behavior.
* Screenshots or error messages, if applicable.
* Your operating system and environment details.

Thank you for helping to make this project better!
