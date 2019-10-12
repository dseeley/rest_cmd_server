# rest_cmd_server
REST server that enables arbitrary commands to be scheduled, and for their status to be retrieved.

## config
For safety, it is designed to permit specific commands only.  Define these in `src/rest_cmd_server/command_defs.py`
```
CommandDefs = {"sleep_5s_linux": os.path.dirname(os.getcwd()) + "/test/sleep.sh",
               "sleep_5s_windows": os.path.dirname(os.getcwd()) + "\\test\\sleep.bat",
               "ffmpeg_linux": "/usr/bin/ffmpeg"}
``` 

## Run
+ `cd src`
+ `python3 main.py`


## Test
+ `cd test`
+ `python3 -m unittest rest_cmd_server__test.py -v`


## Examples
#### Create ffmpeg frame count job
```
curl -X POST http://127.0.0.1:8080/job \
  -H 'Content-Type: application/json' \
  -d '{
    "jobName": "framecount",
    "command": "ffmpeg_linux",
    "parameters": [
    	"-y",
    	"-v", "panic", "-stats",
    	"-i", "/mnt/c/source/test_video.mxf",
    	"-map", "0:v:0", "-c", "copy", "-f", "null", "-y", "-"
    ]
}'
```

#### Create ffmpeg transcode job
```
curl -X POST http://127.0.0.1:8080/job \
  -H 'Content-Type: application/json' \
  -d '{
    "jobName": "transcode",
    "command": "ffmpeg_linux",
    "parameters": [
    	"-y",
    	"-v", "info", "-progress", "pipe:1",
    	"-i", "/mnt/c/source/test_video.mxf",
    	"-vcodec", "libx264",
    	"/mnt/y/src/rest_cmd_server/test_video.mp4"
    ]
}'
```

#### Create sleep test job
```
curl -X POST http://127.0.0.1:8080/job \
  -H 'Content-Type: application/json' \
  -d '{
    "jobName": "SleepLinux",
    "command": "sleep_5s_linux",
    "parameters": []
}'
```

#### Cancel a job by id
```
curl -X GET http://127.0.0.1:8080/job/8888/cancel
``` 

#### Get status of all jobs
```
curl -X GET 'http://127.0.0.1:8080/job/status'
``` 

#### Get status of all active jobs
```
curl -X GET 'http://127.0.0.1:8080/job/active'
``` 
#### Get status of job by id
```
curl -X GET 'http://127.0.0.1:8080/job/7806349662268392/status'
``` 



## Dependencies 

Managed via Pipenv:
```bash
pipenv install
```
Will create a Python virtual environment with dependencies specified in the Pipfile

To active it, simply enter:
```bash
pipenv shell
```
