# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN apt-get update && \
    apt-get install -y ffmpeg libsm6 libxext6 libglib2.0-0 libfontconfig1 && \
    apt-get install -y fonts-dejavu-core && \
    apt-get clean

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Run bot.py when the container launches
CMD ["python", "screenshot.py"]
