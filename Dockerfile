# Use an official Python runtime as a parent image
FROM python:3.11-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /usr/src/app

# Install pip and venv
RUN pip install --upgrade pip
RUN pip install virtualenv

# Create a virtual environment and activate it
RUN python -m venv venv
ENV PATH="/usr/src/app/venv/bin:$PATH"

# Install any needed packages specified in requirements.txt
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .
