# STAGE 1: Builder
FROM python:3.13-slim AS builder

# Prevent python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Prevent python from buffering stdout/stderr (real time logs)
ENV PYTHONUNBUFFERED=1

WORKDIR /build

COPY requirements.txt .

# Install to a specific path using --prefix to make copying clean
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install -r requirements.txt


# STAGE 2: Runtime
FROM python:3.13-slim

# OCI metadata 
LABEL org.opencontainers.image.source="https://github.com/yarosazonov/krisa-remna-tg-bot"
LABEL org.opencontainers.image.description="Krisa tg bot for Remnawave"
LABEL org.opencontainers.image.authors="yarosazonov"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Build arguments with default values
ARG USER_NAME=appuser
ARG USER_ID=1000
ARG GROUP_ID=1000

# Create a dedicated system user
RUN groupadd -g $GROUP_ID $USER_NAME && \
    useradd -u $USER_ID -g $GROUP_ID -m $USER_NAME

# Copy only the compiled/installed libraries from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=$USER_NAME:$USER_NAME . .

USER $USER_NAME

CMD ["python", "main.py"]
