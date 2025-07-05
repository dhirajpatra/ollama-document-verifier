FROM ollama/ollama:latest

# Create startup script
RUN echo '#!/bin/bash\n\
# Start Ollama server in background\n\
ollama serve &\n\
\n\
# Wait for server to be ready\n\
echo "Waiting for Ollama server to start..."\n\
while ! curl -s http://localhost:11434/api/tags > /dev/null; do\n\
    sleep 2\n\
done\n\
\n\
echo "Ollama server started, pulling gemma:2b model..."\n\
ollama pull gemma:2b\n\
\n\
echo "Model downloaded, ready to serve!"\n\
\n\
# Keep the server running\n\
wait\n\
' > /startup.sh && chmod +x /startup.sh

EXPOSE 11434

CMD ["/startup.sh"]