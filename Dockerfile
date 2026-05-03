# Use an official Python runtime as a parent image
FROM python:3.13-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create the non-privileged user early
RUN adduser -D dgsm

# Set work directory
WORKDIR /usr/src/app

# Update the OS without caching package indexes to save space
RUN apk upgrade --no-cache

# Copy only requirements first to leverage Docker layer caching
COPY requirements.txt ./

# Upgrade pip and install packages in a single layer to save space
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the app contents and set ownership in one step
# This prevents Docker from creating duplicate layers and doubling image size
COPY --chown=dgsm:dgsm . .

# Ensure the data directory exists with the correct permissions
RUN mkdir -p /usr/src/app/data \
    && chown dgsm:dgsm /usr/src/app/data

# Switch to the non-privileged user
USER dgsm

# Set default container start command
CMD ["python", "main.py"]
