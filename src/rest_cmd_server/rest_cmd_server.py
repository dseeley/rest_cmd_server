from http.server import BaseHTTPRequestHandler
import socketserver
import threading
import subprocess
import sys
import ssl
import posixpath
import re
import os
import json
import random
from urllib.parse import urlparse, parse_qs
from .jobdb import *
from .command_defs import *

import logging.handlers

logging.getLogger(__name__).setLevel(logging.INFO)
logging.getLogger(__name__).addHandler(logging.StreamHandler())
if os.name == 'nt':
    logging.getLogger(__name__).addHandler(logging.handlers.NTEventLogHandler('rest_cmd_server'))
else:
    logging.getLogger(__name__).addHandler(logging.handlers.SysLogHandler())
_logger = logging.getLogger(__name__)

jobDB = JobDB()
MAXJOBS = 1


class rest_cmd_server(object):
    def __init__(self, srv_port=8080, pemFile=None):
        self.srv_port = srv_port
        self.pemFile = pemFile

        # If this is not a windows box, allow TCP address reuse
        if os.name != 'nt':
            socketserver.ThreadingTCPServer.allow_reuse_address = True

        self.server = socketserver.ThreadingTCPServer(("", self.srv_port), ServerHandler)

        # If a certificate chain file is included, assume we're running over ssl.
        if self.pemFile:
            self.server.socket = ssl.wrap_socket(self.httpd.socket, certfile=self.pemFile, server_side=True)

    # Start server (needed for threading, which is needed for testing)
    def Start(self):
        _logger.info("Started on port " + str(self.srv_port) + "...")
        self.server.serve_forever()

    # Stop server
    def Stop(self):
        _logger.info("Stopping server...")
        self.server.server_close()
        self.server.shutdown()
        _logger.info("...server stopped")


class ServerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.pathElemArr = ServerHandler.pathParse(self.path)

        ## /job
        if len(self.pathElemArr) > 0 and 'pathElem' in self.pathElemArr[0] and self.pathElemArr[0]['pathElem'] == 'job':
            ## /job/status
            if self.pathElemArr[1]['pathElem'] == 'status':
                self.serverReply(200, json.dumps(jobDB.getAllJobs(), sort_keys=True, indent=2))

            ## /job/active
            elif self.pathElemArr[1]['pathElem'] == 'active':
                self.serverReply(200, json.dumps(jobDB.getActiveJobs(), sort_keys=True, indent=2))

            ## /job/1234/status
            elif self.pathElemArr[2]['pathElem'] == 'status':
                jobID = self.pathElemArr[1]['pathElem']

                if jobDB.getJobByID(jobID) is not None:
                    self.serverReply(200, json.dumps(jobDB.getJobByID(jobID).json(), sort_keys=True, indent=2))
                else:
                    self.serverReply(400, json.dumps({"Error": "No job found with ID: " + jobID}, sort_keys=True, indent=2))

            ## /job/1234/cancel
            elif self.pathElemArr[2]['pathElem'] == 'cancel':
                jobID = self.pathElemArr[1]['pathElem']

                if jobDB.getJobByID(jobID) is not None:
                    if jobDB.getJobByID(jobID).state == 'IN PROGRESS':
                        jobDB.getJobByID(jobID).jobRunnerInstance.kill()
                        self.serverReply(200, json.dumps(jobDB.getJobByID(jobID).json(), sort_keys=True, indent=2))
                    else:
                        self.serverReply(400, json.dumps({"Error": "Job already finished (state: " + jobDB.getJobByID(jobID).state + ")"}, sort_keys=True, indent=2))
                else:
                    self.serverReply(400, json.dumps({"Error": "No job found with ID: " + jobID}, sort_keys=True, indent=2))

            else:
                self.serverReply(501, json.dumps({"Error": "Unrecognised API call"}, sort_keys=True, indent=2))
        else:
            self.serverReply(501, json.dumps({"Error": "Unrecognised API call"}, sort_keys=True, indent=2))

    def do_POST(self):
        self.processNewJobRequest()

    def do_PUT(self):
        self.processNewJobRequest()

    def processNewJobRequest(self):
        _logger.debug("urlparse.parse_qsl: " + str(urlparse(self.path)))
        _logger.debug("pathParse: " + str(ServerHandler.pathParse(self.path)))
        restPath = ServerHandler.pathParse(self.path)
        restDataJson = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        _logger.debug(restDataJson)

        if len(restPath) >= 1 and 'pathElem' in restPath[0] and restPath[0]['pathElem'] == 'job':
            if ('jobId' in restDataJson and len(restPath) >= 2 and 'pathElem' in restPath[1] and restPath[1]['pathElem'].isdigit()) and restDataJson['jobId'] != restPath[1]['pathElem']:
                self.serverReply(400, json.dumps({"Error": "jobID mismatch between request body data (" + restDataJson['jobId'] + ") and uri(" + restPath[1]['pathElem'] + ")"}, sort_keys=True, indent=2))
            else:
                if 'jobName' not in restDataJson or 'command' not in restDataJson:
                    self.serverReply(400, json.dumps({"Error": "jobName and command both required"}, sort_keys=True, indent=2))
                elif restDataJson['command'] not in CommandDefs:
                    self.serverReply(400, json.dumps({"Error": restDataJson['command'] + " is not a supported command"}, sort_keys=True, indent=2))
                else:
                    if 'jobId' in restDataJson:
                        jobID = restDataJson['jobId']
                    elif len(restPath) >= 2 and 'pathElem' in restPath[1] and restPath[1]['pathElem'].isdigit():
                        jobID = restPath[1]['pathElem']
                    else:
                        jobID = ''.join(["%s" % random.randint(0, 9) for num in range(0, 16)])  # 16 digit random number

                    ## If there are already more than MAXJOBS active jobs, don't start another, return fail.
                    if len(jobDB.getActiveJobs()) >= MAXJOBS:
                        self.serverReply(503, json.dumps({"Error": "More than maximum jobs (" + str(MAXJOBS) + ") already in progress.  " + str(jobDB.getActiveJobs())}, sort_keys=True, indent=2))
                    else:
                        jobCmd = [CommandDefs[restDataJson['command']]]
                        if 'parameters' in restDataJson:
                            jobCmd = jobCmd + restDataJson['parameters']

                        jobRunnerInstance = JobRunner(jobCmd, jobID, self.cbJobProgress)
                        newJob = jobDB.job(jobID, jobRunnerInstance)
                        try:
                            jobDB.addJob(newJob)
                        except ValueError as e:
                            self.serverReply(400, json.dumps({"Error": "Error adding Job " + jobID + ": " + str(e)}, sort_keys=True, indent=2))
                        else:
                            newJob.jobRunnerInstance.start()
                            self.serverReply(202, json.dumps(jobDB.getJobByID(jobID).json(), sort_keys=True, indent=2))
        else:
            self.serverReply(501, json.dumps({"Error": "Unrecognised API call"}, sort_keys=True, indent=2))

    def serverReply(self, code, jsonMsg):
        """Boilerplate reply code"""
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(bytes(str(jsonMsg), 'utf-8'))

    def cbJobProgress(self, jobID, returncode, res_stdout, res_stderr):
        """Callback from the JobRunner thread"""
        _logger.debug("job " + jobID + " progress.\n\n" + "returncode:" + str(returncode) + "\n\nstdout:\n" + str(res_stdout) + "\n\nstderr:\n" + str(res_stderr))
        if returncode is None:
            jobDB.getJobByID(jobID).state = 'IN PROGRESS'
        elif returncode == 0:
            jobDB.getJobByID(jobID).state = 'COMPLETE'
        else:
            jobDB.getJobByID(jobID).state = 'FAILED'
        jobDB.getJobByID(jobID).result = {"returncode": returncode, "duration_s": time.time() - jobDB.getJobByID(jobID).submitTimestamp, "stdout": str(res_stdout), "stderr": str(res_stderr)}

    @staticmethod
    def pathParse(path_string):
        result = []
        tmp = posixpath.normpath(path_string)  # Prevent dodgy characters causing issues
        while tmp != "/":
            (tmp, item) = posixpath.split(tmp)
            itemQueryStr = re.search(r"^(.*?)\?(.*)$", item)
            if itemQueryStr:
                result.insert(0, {'pathElem': itemQueryStr.groups()[0], 'queryStr': parse_qs(itemQueryStr.groups()[1])})
            else:
                result.insert(0, {'pathElem': item, 'queryStr': ''})
        return result


class JobRunner(threading.Thread):
    def __init__(self, cmd, jobID, jobCallBack):
        self.cmd = cmd
        self.jobID = jobID
        self.jobCallBack = jobCallBack
        self.process = None
        self.stdout = ""
        self.stderr = ""

        _logger.debug("JobRunner command (jobID=" + self.jobID + "): " + str(cmd))
        threading.Thread.__init__(self)

    def kill(self):
        self.process.kill()

    def run(self):
        try:
            if os.name == 'nt':
                self.process = subprocess.Popen(self.cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, creationflags=0x00004000)  # 0x00004000 == BELOW_NORMAL_PRIORITY_CLASS
            else:
                self.process = subprocess.Popen(self.cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        except OSError as e:
            _logger.error("Error starting job with ID: %s", self.jobID)
            self.jobCallBack(self.jobID, 1, self.stdout, "Error starting job: " + str(e))
        else:
            ## process.communicate is a blocking call that only returns after the process is finished - so we can't see the incremental progress on stdout.
            # (self.stdout, self.stderr) = self.process.communicate()

            ## Poll the process output so we can get the incremental stdout in the status response.
            while self.process.poll() is None:
                self.stdout += self.process.stdout.readline()
                self.stderr += self.process.stderr.readline()
                sys.stdout.flush()

                self.jobCallBack(self.jobID, self.process.returncode, self.stdout, self.stderr)

            ## We often miss the last readline and callback due to race condition.  Call again - does no harm.
            self.stdout += self.process.stdout.readline()
            self.stderr += self.process.stderr.readline()
            self.jobCallBack(self.jobID, self.process.returncode, self.stdout, self.stderr)
