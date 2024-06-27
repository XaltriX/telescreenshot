FROM python:3.9-slim

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN apt-get update && apt-get install -y libgl1-mesa-glx
RUN pip install -r requirements.txt
RUN pip install opencv-python

# Copy the application code
COPY . .

# Set the environment variable for the bot token
ENV TOKEN=$TOKEN

# Expose the port for the Telegram bot
EXPOSE 8443

# Run the bot when the container starts
CMD ["python", "screenshot.py"]
