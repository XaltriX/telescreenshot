#!/bin/bash

# Download FFmpeg
curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz -o ffmpeg-release-i686-static.tar.xz

# Extract the tar file
tar -xJf ffmpeg-release-i686-static.tar.xz

# Move FFmpeg binaries to a directory in the PATH
mkdir -p ~/bin
mv ffmpeg-*/ffmpeg ~/bin/
mv ffmpeg-*/ffprobe ~/bin/

# Make binaries executable
chmod +x ~/bin/ffmpeg
chmod +x ~/bin/ffprobe

# Clean up
rm -rf ffmpeg-release-i686-static.tar.xz ffmpeg-*/
