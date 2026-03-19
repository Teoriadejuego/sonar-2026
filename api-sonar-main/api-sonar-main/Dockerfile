FROM python:3.11-slim

WORKDIR /app
ENV PORT=8000

COPY api-sonar-main/api-sonar-main/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY api-sonar-main/api-sonar-main/ .
COPY project_parameters.json /app/project_parameters.json

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 CMD sh -c "python -c \"import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.getenv(\\\"PORT\\\", \\\"8000\\\")}/health/live')\""

CMD ["sh", "-c", "python migrate.py && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
