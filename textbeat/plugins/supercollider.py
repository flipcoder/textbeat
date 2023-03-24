#!/usr/bin/env python
import textbeat.instrument as instrument
from textbeat.instrument import Instrument
from shutilwhich import which

ERROR = False
if which('scsynth'):
    try:
        import pythonosc
    except:
        ERROR = True
else:
    ERROR = True

class SuperCollider(Instrument):
    NAME = 'supercollider'
    def __init__(self, args):
        Instrument.__init__(self, SuperCollider.NAME)
        self.initialized = False
    def enable(self):
        self.initialized = True
    def enabled(self):
        return self.enabled
    def supported(self):
        return not ERROR
    def support(self):
        return ['supercollider']
    def stop(self):
        pass

export = SuperCollider

