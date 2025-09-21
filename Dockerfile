FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

FROM python:3.11-slim

WORKDIR /app
 
COPY --from=builder /usr/local /usr/local

COPY . .

CMD ["python", "main.py"]
