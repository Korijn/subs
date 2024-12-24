# subs


ffmpeg -i '.\[Trix] FLCL (2000) - 01 (BD 1080p AV1) [821409C9].mkv' -map 0:v:0 -map 0:a -map 0:s -map -0:t -c:v libx264 -pix_fmt yuv420p -preset ultrafast -crf 23 -c:a ac3 -b:a 192 -c:s copy -t 10 flcl-1.mkv
