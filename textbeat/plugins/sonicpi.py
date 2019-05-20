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
    def __init__(self, args):
        Instrument.__init__(self, SonicPi.NAME)
        self.initalized = False
    def enable(self):
        self.initalized = True
    def enabled(self):
        return self.initialized
    def supported(self):
        return not ERROR
    def support(self):
        return ['sonicpi']
    def stop(self):
        pass

# instrument.export(SonicPi)
export = SonicPi

