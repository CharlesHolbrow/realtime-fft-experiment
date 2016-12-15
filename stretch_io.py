import sys
import re
import types

from time import sleep

from OSC import OSCServer, OSCClient, OSCMessage


class StretchIO(object):

    def __init__(self, listen=("0.0.0.0", 12340), send=("18.85.26.64", 12341)):
        self.server = OSCServer(listen)
        self.server.timeout = 0.0
        self.server.timed_out = False

        def timeout(self):
            self.timed_out = True
        self.server.handle_timeout = types.MethodType(timeout, self.server)

        self.client = OSCClient()
        self.client.connect(send)

        self.__fader_state = [8, 8, 8, 8]

        self.__fader_cb = None
        self.__toggle_cb = None

        for i in range(1, 5):
            self.led(i, 0.)
            self.toggle(i, 0.)
            self.fader(i, self.__fader_state[i-1])
            self.server.addMsgHandler('/1/toggle' + str(i), self.osc_handler)
            self.server.addMsgHandler('/1/fader' + str(i), self.osc_handler)


    def step(self):
        self.server.timed_out = False
        while not self.server.timed_out:
            self.server.handle_request()

    def send(self, v):
        m = OSCMessage('/1/fader1')
        m.append(float(v))
        self.client.send(m)

    def close(self):
        self.server.close()

    def set_toggle_handler(self, cb):
        """ Register the function to be called when we press the toggle.

        <cb> should be a functio with the signature
            cb(button_number, button_state)
        """
        self.__toggle_cb = cb

    def set_fader_handler(self, cb):
        self.__fader_cb = cb

    def osc_handler(self, path, tags, args, source):
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

        if name == 'fader':
            self.__fader_state[num-1] = state

        if name == 'toggle' and self.__toggle_cb is not None:
            print name, num, state
            self.__toggle_cb(num, state)
        elif name == 'fader' and self.__fader_cb is not None:
            self.__fader_state[num-1] = state
            self.__fader_cb(num, state)



    def led(self, led_num, value):
        m = OSCMessage('/1/led{0:d}'.format(led_num))
        m.append(value)
        if value > 1.0: value = 1.0
        if value < 0.0: value = 0.0
        self.client.send(m)
    def toggle(self, toggle_num, value):
        m = OSCMessage('/1/toggle{0:d}'.format(toggle_num))
        m.append(1 if value else 0)
        self.client.send(m)
    def fader(self, fader_num, value):
        m = OSCMessage('/1/fader{0:d}'.format(fader_num))
        m.append(float(value))
        self.client.send(m)

    def fader_state(self, i):
        """
        <i> is the index from zero (unlike the setters, that index from 1)
        """
        return self.__fader_state[i]



if __name__ == '__main__':
    def f(a, b):
        print 'handler', a, b

    server = StretchIO()
    server.register_toggle_handler(f)

    while True:
        server.step()
        sleep(0.01)
