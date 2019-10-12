import sys
if sys.version_info[0] != 3 or sys.version_info[1] < 6:
    print("Python version must be 3.6 or greater\n")
    exit(1)

import rest_cmd_server
import argparse
import signal
import threading
import time


def sigint_handler(sig, frame):
    print('\nExit via Ctrl+C')
    threading.Thread(target=oTestServer.Stop).start()
    time.sleep(3)
    sys.exit(0)


signal.signal(signal.SIGINT, sigint_handler)

parser = argparse.ArgumentParser()
parser.add_argument('-p', '--port', help='Remote server port', default='8080')
parser.add_argument('-z', '--pemfile', help='path to ssl certificate')

args = parser.parse_args()
oTestServer = rest_cmd_server.rest_cmd_server(int(args.port), args.pemfile)
oTestServer.Start()
