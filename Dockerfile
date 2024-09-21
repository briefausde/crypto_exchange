FROM python:3.11-slim-bullseye

ENV PDM_VERSION=2.9.1
ENV PDM_USE_VENV=no
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc git && \
    rm -rf /var/lib/apt/lists/*

RUN pip install pdm==${PDM_VERSION}

COPY pyproject.toml pdm.lock README.md ./

RUN pdm install --prod --no-lock --no-editable

COPY . .

EXPOSE 8080

CMD ["pdm", "run", "python3", "-m", "crypto_exchange"]
