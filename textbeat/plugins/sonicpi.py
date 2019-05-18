#!/usr/bin/env python
import textbeat.instrument as instrument
from textbeat.instrument import Instrument

ERROR = False
try:
    import psonic
except ImportError:
    ERROR = True

class SonicPi(Instrument):
    NAME = 'sonicpi'
    def __init__(self):
        Instrument.__init__(self, SonicPi.NAME)
        self.initalized = False
    def init(self):
        self.initalized = True
    def inited(self):
        return self.initalized
    def supported(self):
        return not ERROR
    def support(self):
        return ['sonicpi']
    def stop(self):
        pass

# instrument.export(SonicPi)
export = SonicPi

