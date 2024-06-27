FROM python:3.9-buster

WORKDIR /app

# Install OpenGL dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-dev \
    libglu1-mesa-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create a volume mount to share a directory from your local machine
RUN mkdir -p /app/video_files && docker run -d --name video_volume railway/railway:v1 volume create /app/video_files

CMD ["python", "screenshot.py"]
