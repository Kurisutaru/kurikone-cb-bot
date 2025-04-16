# Stage 1: Build stage
FROM python:3.12-alpine as builder

# Install build dependencies
RUN apk add --no-cache build-base mariadb-dev gcc

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.12-alpine

# Install runtime dependencies
# mariadb-connector-c provides libmariadb.so.3
RUN apk add --no-cache mariadb-connector-c

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

# Ensure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
# Add library path to environment
ENV LD_LIBRARY_PATH=/usr/lib

RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
CMD ["python", "main.py"]