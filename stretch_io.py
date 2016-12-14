import sys
import re
from time import sleep

from OSC import OSCServer, OSCClient, OSCMessage


class StretchIO(object):

    def __init__(self, listen=("0.0.0.0", 12340), send=("18.85.26.64", 12341)):
        self.server = OSCServer(listen)
        self.server.timeout = 0.0
        self.server.addMsgHandler('/1/toggle1', self.button_handler)
        self.server.addMsgHandler('/1/toggle2', self.button_handler)
        self.server.addMsgHandler('/1/toggle3', self.button_handler)
        self.server.addMsgHandler('/1/toggle4', self.button_handler)

        self.client = OSCClient()
        self.client.connect(send)

        self.__cb = None

    def step(self):
        self.server.handle_request()

    def send(self, v):
        m = OSCMessage('/1/fader1')
        m.append(float(v))
        self.client.send(m)

    def close(self):
        self.server.close()

    def register_toggle_handler(self, cb):
        """ Register the function to be called when we press the toggle.

        <cb> should be a functio with the signature
            cb(button_number, button_state)
        """
        self.__cb = cb

    def button_handler(self, path, tags, args, source):
        paths = path.split('/')
        # paths looks like this for 'auto' touchOSC elements ['', '1', 'toggle1']

        if len(paths) < 3:
            return

        match = re.match('([a-zA-Z]+)(\d+)', paths[2])

        if not match:
            print 'osc path match failed'
            return

        if len(args) < 1:
            print 'handler has no arguments'
            return

        parts = match.groups()
        name  = parts[0]
        num   = int(parts[1])
        state = args[0]

        print name, num, state
        if name == 'toggle' and self.__cb is not None:
            self.__cb(num, state)


if __name__ == '__main__':
    def f(a, b):
        print 'handler', a, b

    server = StretchIO()
    server.register_toggle_handler(f)

    while True:
        server.step()
        sleep(0.01)
