FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /usr/local /usr/local

COPY . .

ARG USER_NAME=appuser
ARG USER_ID=1000
ARG GROUP_ID=1000

RUN groupadd -g $GROUP_ID $USER_NAME && \
    useradd -u $USER_ID -g $GROUP_ID -m $USER_NAME

RUN chown -R $USER_NAME:$USER_NAME /app

USER $USER_NAME

CMD ["python", "main.py"]
