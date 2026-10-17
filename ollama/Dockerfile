# Private Ollama service for Render: Gemma 3 (vision) baked into the image, so nothing is downloaded at start.
FROM ollama/ollama:latest
ENV OLLAMA_HOST=0.0.0.0:10000 OLLAMA_KEEP_ALIVE=-1
RUN bash -c 'ollama serve & pid=$!; \
    until ollama list >/dev/null 2>&1; do sleep 1; done; \
    ollama pull gemma3:4b; kill $pid; wait $pid || true'
ENTRYPOINT ["ollama", "serve"]
