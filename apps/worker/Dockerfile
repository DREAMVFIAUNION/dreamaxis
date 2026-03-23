FROM mcr.microsoft.com/powershell:7.4-ubuntu-22.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends git nodejs python3 python3-pip \
    && corepack enable \
    && corepack prepare pnpm@10.8.1 --activate \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --no-cache-dir fastapi httpx pydantic-settings "uvicorn[standard]"

WORKDIR /workspace

COPY apps/worker /workspace/apps/worker

RUN python3 -m pip install --no-cache-dir /workspace/apps/worker

ENV PYTHONPATH=/workspace/apps/worker

EXPOSE 8100

CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
