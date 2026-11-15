FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
# Cuentas, sesiones y la clave de firma viven en este volumen, nunca en la imagen ni en git.
ENV AUTH_DATA_DIR=/data/auth
VOLUME ["/data/auth"]
EXPOSE 8000
CMD ["uvicorn", "auth.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
