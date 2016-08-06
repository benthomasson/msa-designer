
from gevent import monkey
monkey.patch_all()


import os
import socket
import pkg_resources
import logging
import hashlib
import yaml
import json
from pprint import pprint
from jinja2 import Environment, PackageLoader

env = Environment(loader=PackageLoader('msa_designer_web', 'templates'))

from bottle import route, request
from bottle import static_file
from bottle import redirect

from socketio.namespace import BaseNamespace
from socketio.mixins import BroadcastMixin

logger = logging.getLogger('msa-designer.server')

saved_msas_root = os.path.abspath("saved_msas")
load_msas_root = os.path.abspath("loaded_msas")


if not os.path.exists(saved_msas_root):
    os.makedirs(saved_msas_root)


if not os.path.exists(load_msas_root):
    os.makedirs(load_msas_root)


class AgentNamespace(BaseNamespace, BroadcastMixin):

    def initialize(self):
        logger.debug("INIT")
        print self.__dict__.keys()
        print self.ns_name
        print self.request

    def on_save(self, message):
        logger.debug("save %s", message)
        app_name = message.get('app', 'msa')
        data = yaml.safe_dump(message, default_flow_style=False)
        save_id = hashlib.sha1(data).hexdigest()
        url = '/save/{0}/{1}.yml'.format(save_id, app_name)
        with open(os.path.join(saved_msas_root, save_id), 'w') as f:
            f.write(data)
        self.emit('saved', dict(url=url))


from socketio import socketio_manage


@route('/status')
def status():
    return "running"


@route('/upload', method='POST')
def do_upload():
    upload = request.files.get('upload')
    data = upload.file.read()
    print upload.filename, data
    load_id = hashlib.sha1(data).hexdigest()
    with open(os.path.join(load_msas_root, load_id), 'w') as f:
        f.write(data)
    return redirect("/msa/{0}".format(load_id))


@route('/socket.io/<namespace:path>')
def index(namespace):
    socketio_manage(request.environ, {'/msa-designer': AgentNamespace})


@route('/save/<save_id:path>/<name:path>')
def save(save_id, name):
    logger.debug("save_id %s", save_id)
    return static_file(save_id, root=saved_msas_root, mimetype="text/yaml", download=name)


@route('/')
def root():
    return env.get_template('index.html').render()


@route('/msa/<load_id:path>')
def root(load_id):
    with open(os.path.join(load_msas_root, load_id)) as f:
        msa = json.dumps(yaml.load(f.read()))
    print msa
    return env.get_template('index.html').render(msa_to_load=msa)


@route('/static/<filename:path>')
def serve_static(filename):
    return static_file(filename, root=pkg_resources.resource_filename('msa_designer_web', 'static'))



from bottle import ServerAdapter


class SocketIOServer(ServerAdapter):
    def run(self, handler):
        from socketio.server import SocketIOServer
        resource = self.options.get('resource', 'socket.io')
        policy_server = self.options.get('policy_server', False)
        done = False
        while not done:
            try:
                SocketIOServer((self.host, self.port),
                               handler,
                               resource=resource,
                               policy_server=policy_server,
                               transports=['websocket', 'xhr-multipart', 'xhr-polling']).serve_forever()
            except socket.error, e:
                if e.errno == 98:
                    logger.warning(str(e))
                    raise
                else:
                    raise
