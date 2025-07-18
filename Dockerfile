FROM python:3.10-slim AS builder

# Set environment variables

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_VERSION=1.8.3
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/.cache

# Install system dependencies and poetry
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/opt/poetry/bin:$PATH"

WORKDIR /app

# Copy all project files
COPY . /app

# Project initialization:
RUN poetry config virtualenvs.in-project true \
    && poetry install --no-interaction --no-ansi --only main

# Final stage
FROM python:3.10-slim

WORKDIR /app


# Copy Python dependencies and project files from builder stage
COPY --from=builder /app /app
COPY --from=builder /opt/poetry /opt/poetry

ENV PATH="/opt/poetry/bin:$PATH"
ENV PYTHONPATH="/app/.venv/lib/python3.10/site-packages:$PYTHONPATH"

# Remove data folder if it exists
RUN rm -rf /app/data

# Create a volume for the data folder
VOLUME /app/applicationai

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

CMD ["poetry", "run", "streamlit", "run", "Chat.py", "--server.port=8501", "--server.address=0.0.0.0"]
