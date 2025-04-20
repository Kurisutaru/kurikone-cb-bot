# Stage 1: Build stage
FROM python:3.12-alpine AS builder

# Install build dependencies
RUN apk add --no-cache build-base mariadb-dev gcc

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.12-alpine
# Install runtime dependencies
RUN apk add --no-cache \
    mariadb-connector-c \
    tzdata

# Set timezone to JST
ENV TZ=Asia/Tokyo

RUN ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime \
    && echo "Asia/Tokyo" > /etc/timezone

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

# Environment variables
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV LD_LIBRARY_PATH=/usr/lib

# Start chronyd in foreground mode (non-privileged)
RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
CMD ["python", "main.py"]