FROM python:3.12
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip3 install -r requirements.txt --no-cache-dir
COPY *.py ./
EXPOSE 8501
HEALTHCHECK --interval=600s --timeout=2s --retries=12 \
    CMD ["curl", "-f", "http://localhost:8501/"]
ENTRYPOINT ["streamlit", "run", "app.py", "--server.headless", "true", "--browser.serverAddress='0.0.0.0'", "--browser.gatherUsageStats", "false"]
USER 1001