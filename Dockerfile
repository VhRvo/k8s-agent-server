FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev

COPY src/ src/

RUN mkdir -p data
VOLUME /app/data

EXPOSE 7777
CMD ["uv", "run", "uvicorn", "k8s_agent.main:app", "--host", "0.0.0.0", "--port", "7777"]
