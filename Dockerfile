# Stage 1: Build stage
FROM python:3.12-alpine AS builder

# Install build dependencies only for building wheels
RUN apk add --no-cache \
    build-base \
    mariadb-dev \
    gcc \
    libffi-dev \
    musl-dev

WORKDIR /app
COPY requirements.txt .

# Install dependencies into a temporary location
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Final runtime stage
FROM python:3.12-alpine

# Only install runtime dependencies
RUN apk add --no-cache \
    mariadb-connector-c \
    tzdata \
    && rm -rf /var/cache/apk/*

# Timezone setup
ENV TZ=Asia/Tokyo
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime \
 && echo $TZ > /etc/timezone

WORKDIR /app

# Copy installed python packages
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Environment optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Reduce image size by removing cache and dev files
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
CMD ["python", "main.py"]