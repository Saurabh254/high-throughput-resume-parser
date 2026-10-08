FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY services/worker-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/worker-service/app ./app
COPY services/shared ./shared

CMD ["python", "-m", "app.worker"]
