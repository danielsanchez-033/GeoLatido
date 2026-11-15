# Contexto: services/ (docker-compose.yml). Instala processor sin importarlo: se llama como programa (`run-remote`),
# igual que con `docker compose run process` (los servicios no comparten código, AGENTS.md).
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY processor /app/processor
COPY online /app/online
RUN pip install --no-cache-dir /app/processor /app/online
EXPOSE 8000
CMD ["uvicorn", "--factory", "online.main:create_app", "--host", "0.0.0.0", "--port", "8000"]
