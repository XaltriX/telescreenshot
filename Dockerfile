# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire project directory
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variable for bot token (to be set in Koyeb deployment settings)
ENV TELEGRAM_BOT_TOKEN=""

# Expose port 8080
EXPOSE 8080

# Run the bot
CMD ["python", "screenshot.py"]
