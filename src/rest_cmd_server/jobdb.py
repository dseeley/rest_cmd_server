import time
from datetime import datetime
import os

import logging, logging.handlers

logging.getLogger(__name__).setLevel(logging.INFO)
logging.getLogger(__name__).addHandler(logging.StreamHandler())
if os.name == 'nt':
    logging.getLogger(__name__).addHandler(logging.handlers.NTEventLogHandler('rest_cmd_server'))
else:
    logging.getLogger(__name__).addHandler(logging.handlers.SysLogHandler())
_logger = logging.getLogger(__name__)


class JobDB(object):
    """Database of jobs, past and present.  Limited to MAXSIZE (20) items via a circular buffer."""

    def __init__(self):
        self.MAXSIZE = 20
        self.insertIdx = 0
        self._data = []

    def getActiveJobs(self):
        return [element.json() for element in self._data if element.state == 'IN PROGRESS']

    def getAllJobs(self):
        return [element.json() for element in self._data]

    def getJobByID(self, jobId):
        jobsWithId = [element for element in self._data if element.jobID == jobId]
        if len(jobsWithId) > 1:
            _logger.error("More than one job exists with ID: %s", jobId)
            raise ValueError('More than one job exists with ID: ' + jobId)
        elif len(jobsWithId) == 1:
            return jobsWithId[0]
        else:
            return None

    def addJob(self, job):
        if self.getJobByID(job.jobID):
            raise ValueError("Duplicate jobID: " + job.jobID)

        if len(self._data) == self.MAXSIZE:
            self._data[self.insertIdx] = job
        else:
            self._data.append(job)
        self.insertIdx = (self.insertIdx + 1) % self.MAXSIZE

    def __getitem__(self, key):
        """Get element by index, relative to the current insertIdx"""
        if len(self._data) == self.MAXSIZE:
            return (self._data[(key + self.insertIdx) % self.MAXSIZE])
        else:
            return (self._data[key])

    def __repr__(self):
        """Return string representation"""
        return self._data.__repr__() + ' (' + str(len(self._data)) + ' items)'

    class job(object):
        def __init__(self, jobID, jobRunnerInstance, state='IN PROGRESS'):
            self.jobID = jobID
            self.state = state
            self.jobRunnerInstance = jobRunnerInstance
            self.submitTimestamp = time.time()
            self.result = {}

        def __repr__(self):
            """Return string representation"""
            return str(self.jobID) + " :: " + str(self.state) + " :: " + str(self.submitTimestamp)

        def json(self):
            return {"jobId": self.jobID, "status": self.state, "result": self.result}
