# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set persistent environment variables
ENV ENV=production

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install gunicorn
RUN pip install gunicorn

# Copy the current directory contents into the container
COPY . .

# Define the command to start the bot
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8080", "maestro_bot:app"]