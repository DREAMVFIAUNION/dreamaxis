FROM python:3.12-slim

WORKDIR /app

COPY apps/desktop-worker/pyproject.toml /app/pyproject.toml
RUN pip install --upgrade pip && pip install .

COPY apps/desktop-worker/app /app/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8300"]
