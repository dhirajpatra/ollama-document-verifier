# Dockerfile for your Python application
FROM python:3.9-slim-buster

WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application files
COPY . .

# Make sure the documents directory exists in the container
# This is mainly for allowing the app to reference a consistent path
# The actual files will be mounted from the host.
RUN mkdir -p /app/documents

# Expose the port Streamlit runs on
EXPOSE 8501

# Command to run your Streamlit application
CMD ["streamlit", "run", "streamlit_app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]