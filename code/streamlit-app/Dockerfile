FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip3 install -r requirements.txt --no-cache-dir
COPY *.py ./
COPY images/ ./images/
EXPOSE 8501
HEALTHCHECK --interval=600s --timeout=2s --retries=12 \
    CMD ["curl", "-f", "http://localhost:8501/"]
USER 1001
ENTRYPOINT ["streamlit", "run", "app.py", "--server.headless", "true", "--browser.serverAddress='0.0.0.0'", "--browser.gatherUsageStats", "false"]
