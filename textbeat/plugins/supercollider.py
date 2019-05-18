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
    def __init__(self):
        Instrument.__init__(self, SuperCollider.NAME)
        self.initalized = False
    def init(self):
        self.initalized = True
    def inited(self):
        return self.initalized
    def supported(self):
        return not ERROR
    def support(self):
        return ['supercollider']
    def stop(self):
        pass

export = SuperCollider

