FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Create synthetic DB at build time (keeps container self-contained)
RUN python -m app.db.seed && python -m app.db.validate_seed

EXPOSE 8000

CMD ["uvicorn", "app.web.server:app", "--host", "0.0.0.0", "--port", "8000"]
