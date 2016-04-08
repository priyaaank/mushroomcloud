import datetime

import psutil

from tornado import websocket, web, ioloop

cl = []


class SocketHandler(websocket.WebSocketHandler):
    def initialize(self, stat_collector):
        self.stat_collector = stat_collector

    def check_origin(self, origin):
        return True

    def open(self):
        if self not in cl:
            cl.append(self)
            self.relay_status()

    def on_message(self, message):
        pass

    def on_close(self):
        if self in cl:
            cl.remove(self)

    def relay_status(self):
        if self.ws_connection and self.ws_connection.stream.socket:
            self.stat_collector.collect()
            self.write_message(self.stat_collector.as_json())
            ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=5), self.relay_status)


class StatCollector:
    def __init__(self):
        self.available_memory = 0
        self.cpu_utilization = 0
        self.node_running = False
        self.worker_running = False
        self.api_running = False
        self.disk_space = 0

    def collect(self):
        self.cpu_utilization = "{percent} % user".format(percent=psutil.cpu_percent())
        self.available_memory = "{mem} MB free".format(mem=psutil.virtual_memory().available >> 20)
        self.disk_space = "{percent}% used".format(percent=psutil.disk_usage("/").percent)
        self.node_running = self.is_process_running("node","server.js")
        self.worker_running = self.is_process_running("python","queue_consumer.py")
        self.api_running = self.is_process_running("python","manage.py")

    def is_process_running(self, parent, cmdline_name):
        for p in psutil.process_iter():
            if p.as_dict(attrs=['pid', 'name', 'cmdline']).get('name') == parent:
                if cmdline_name in p.as_dict(attrs=['pid', 'name', 'cmdline'])['cmdline'][-1]:
                    return True
        return False

    def as_json(self):
        return {
            "memory" : self.available_memory,
            "cpu": self.cpu_utilization,
            "disk_space": self.disk_space,
            "node": self.node_running,
            "worker": self.worker_running,
            "api": self.api_running
        }


app = web.Application([
    (r'/status', SocketHandler, dict(stat_collector=StatCollector()))
])

if __name__ == '__main__':
    app.listen(8888)
    ioloop.IOLoop.instance().start()
