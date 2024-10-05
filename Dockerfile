# Use an official Python runtime as a parent image
FROM python:3.11-slim AS base

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Separate stage for testing
FROM base AS test

# Install testing dependencies (pytest, etc.)
RUN pip install pytest pytest-asyncio

# Copy all code into the test container
COPY . .

# Run the tests
CMD ["pytest", "--maxfail=1", "--disable-warnings", "-v"]

# Final production stage
FROM base AS production

# Copy the current directory contents into the container
COPY . .

# Define the command to start the bot
CMD ["python", "maestro_bot.py"]
