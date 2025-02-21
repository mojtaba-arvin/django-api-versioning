FROM python:3.9-slim

RUN apt-get update && apt-get install -y git

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY .pre-commit-config.yaml .
RUN git init . && pre-commit install-hooks

COPY . .
ENV PYTHONPATH=/app

RUN chmod +x ./entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
