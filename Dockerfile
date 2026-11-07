FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY alembic.ini ./
RUN pip install --no-cache-dir . && \
    useradd --system --create-home --uid 10001 shortlink
USER shortlink
EXPOSE 8000
CMD ["uvicorn", "shortlink.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
