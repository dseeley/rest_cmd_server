import os

CommandDefs = {"sleep_5s_linux": os.path.dirname(os.getcwd()) + "/test/sleep.sh",
               "sleep_5s_windows": os.path.dirname(os.getcwd()) + "\\test\\sleep.bat",
               "ffmpeg_linux": "/usr/bin/ffmpeg"}
