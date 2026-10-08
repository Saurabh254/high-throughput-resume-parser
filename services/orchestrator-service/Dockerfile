FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/orchestrator-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/orchestrator-service/app ./app
COPY services/shared ./shared

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
