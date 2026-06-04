# Copyright 2026 Anna Tchijova, Olga Vasilieva, Gemini
FROM python:3.12-slim-bookworm
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["sh", "-c", "streamlit run dashboard/app.py --server.port=${PORT:-8080} --server.address=0.0.0.0"]
