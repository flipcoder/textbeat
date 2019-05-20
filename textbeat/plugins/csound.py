#!/usr/bin/env python
import textbeat.instrument as instrument
from textbeat.instrument import Instrument
from shutilwhich import which
import subprocess

ERROR = False
if not which('csound'):
    ERROR = True

class CSound(Instrument):
    NAME = 'csound'
    def __init__(self, args):
        Instrument.__init__(self, CSound.NAME)
        self.initialized = False
        self.proc = None
        self.csound = None
    def enable(self):
        if not initialized:
            self.proc = subprocess.Popen(['csound', '-odac', '--port='+str(CSOUND_PORT)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.csound = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.initialized = True
    def enabled(self):
        return self.initialized
    def supported(self):
        return not ERROR
    def support(self):
        return ['csound']
    def send(self, s):
        assert self.initialized
        return csound.sendto(s,('localhost',CSOUND_PORT))
    # def note_on(self, t, n, v):
    #     self.fs.noteon(t, n, v)
    # def note_off(self, t, n, v):
    #     self.fs.noteoff(t, v)
    #     pass
    def stop(self):
        self.proc.kill()
        pass

export = CSound

