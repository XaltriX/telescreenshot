worker: curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-i686-static.tar.xz -o ffmpeg-release-i686-static.tar.xz && \
        tar -xJf ffmpeg-release-i686-static.tar.xz && \
        mkdir -p ~/bin && \
        mv ffmpeg-*/ffmpeg ~/bin/ && \
        mv ffmpeg-*/ffprobe ~/bin/ && \
        chmod +x ~/bin/ffmpeg && \
        chmod +x ~/bin/ffprobe && \
        rm -rf ffmpeg-release-i686-static.tar.xz ffmpeg-*/ && \
        python bot.py
