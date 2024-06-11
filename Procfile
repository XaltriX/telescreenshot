worker: curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz -o ffmpeg-release-i686-static.tar.xz && \
        tar -xJf ffmpeg-release-i686-static.tar.xz && \
        mkdir -p /app/bin && \
        mv ffmpeg-*/ffmpeg /app/bin/ && \
        mv ffmpeg-*/ffprobe /app/bin/ && \
        chmod +x /app/bin/ffmpeg && \
        chmod +x /app/bin/ffprobe && \
        rm -rf ffmpeg-release-i686-static.tar.xz ffmpeg-*/ && \
        export PATH=$PATH:/app/bin && \
        python bot.py

