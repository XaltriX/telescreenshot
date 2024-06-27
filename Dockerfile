# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Download necessary NLTK data
RUN apt-get update && apt-get install -y libglib2.0-0 libsm6 libxext6 libxrender-dev && apt-get clean
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# Run the bot script when the container launches
CMD ["python", "screenshot.py"]
