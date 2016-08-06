'''
Usage:
    msa-designer [options]

Options:
    -h, --help              Show this page.
    -p=<p>, --port=<p>      Web TCP port for web server [default: 8887].
    --debug                 Show debug logging
    --tracebacks            Show tracebacks
'''


import gevent

from gevent import monkey
monkey.patch_all()


import signal
import os
import sys
from docopt import docopt
import logging
from bottle import run
import daemon
import psutil
from lockfile import pidlockfile
from daemon.pidfile import TimeoutPIDLockFile
from contextlib import contextmanager
from server import SocketIOServer

logger = logging.getLogger('msa-designer.cli')


@contextmanager
def NullContext():
    yield


threads = []


def server_main(web_port):
    threads.append(gevent.spawn(run, server=SocketIOServer, host='0.0.0.0', port=web_port))
    gevent.joinall(threads)
    logging.warning('All threads completed')


def terminate(signal_number, stack_frame):
    logger.info('Terminating due to signal %s', signal_number)
    logger.debug('Killing all greenlets')
    gevent.killall(threads)
    logger.debug('Raising SystemExit')
    raise SystemExit()


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    parsed_args = docopt(__doc__, args)
    if parsed_args['--debug']:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logger.debug("Debugging enabled")
    logger.debug(parsed_args)
    context = NullContext()
    with context:
        server_main(int(parsed_args['--port']))
