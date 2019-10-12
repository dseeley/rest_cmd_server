import sys
import os
import threading
import unittest
import json
from urllib.request import HTTPError, urlopen

if sys.version_info[0] != 3 or sys.version_info[1] < 6:
    print("Python version must be 3.6 or greater\n")
    exit(1)

# Add the ../src directory to the import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import rest_cmd_server


class BasicTestCase(unittest.TestCase):
    srv_port = 8080

    def setUp(self):
        """Call before every test case."""
        self.oTestServer = rest_cmd_server.rest_cmd_server(srv_port=BasicTestCase.srv_port)
        self.httpd_srv_thread = threading.Thread(target=self.oTestServer.Start)
        self.httpd_srv_thread.setDaemon(True)
        self.httpd_srv_thread.start()

    def tearDown(self):
        """Call after every test case."""
        self.oTestServer.Stop()

    def testInvalidAPICall(self):
        """testInvalidAPICall"""
        with self.assertRaises(HTTPError) as cm:
            response = urlopen('http://localhost:' + str(BasicTestCase.srv_port))

        resp_data = cm.exception.read()
        self.assertEqual(cm.exception.code, 501)
        self.assertEqual(json.loads(resp_data), {"Error": "Unrecognised API call"})
