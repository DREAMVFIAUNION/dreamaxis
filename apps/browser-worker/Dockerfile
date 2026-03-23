FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY apps/browser-worker /app
RUN pip install --upgrade pip && pip install -e .

EXPOSE 8200
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8200"]
