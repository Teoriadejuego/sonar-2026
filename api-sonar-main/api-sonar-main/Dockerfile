FROM python:3.11-slim

WORKDIR /app

COPY api-sonar-main/api-sonar-main/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api-sonar-main/api-sonar-main/ .
COPY project_parameters.json /app/project_parameters.json

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=10 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3)"

CMD ["sh", "-c", "python migrate.py && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
