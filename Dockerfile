# Use an official Python runtime as a parent image
FROM python:3.12-alpine

# Install system dependencies for MariaDB
RUN apk update && \
    apk add --no-cache \
    build-base \
    mariadb-client \
    mariadb-dev \
    gcc \
    && rm -rf /var/cache/apk/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
# EXPOSE 80

# Define environment variable
ENV PYTHONUNBUFFERED=1

# Make the script executable
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]

# Run the application when the container launches
CMD ["python", "main.py"]