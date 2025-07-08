# Use a slim Python base image
FROM python:3.9-slim-buster

# Set the working directory inside the container
WORKDIR /app

# Install system tools (if needed)
RUN apt-get update && apt-get install -y \
    curl \
    cmake \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy the app-specific requirements.txt into the container
COPY ./requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files into /app
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Launch Streamlit app
CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
