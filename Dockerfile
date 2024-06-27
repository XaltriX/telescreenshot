FROM python:3.9-slim

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install -r requirements.txt

# Copy the application code
COPY . .

# Set the environment variable for the bot token
ENV TOKEN=$TOKEN

# Expose the port for the Telegram bot
EXPOSE 8443

# Run the bot when the container starts
CMD ["python", "screenshot.py"]
