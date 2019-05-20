#!/usr/bin/env python
import textbeat.instrument as instrument
from textbeat.instrument import Instrument
from shutilwhich import which

ERROR = False
if which('fluidsynth'):
    try:
        import fluidsynth # https://github.com/flipcoder/pyfluidsynth
    except:
        ERROR = True
else:
    ERROR = True

class FluidSynth(Instrument):
    NAME = 'fluidsynth'
    def __init__(self, args):
        Instrument.__init__(self, FluidSynth.NAME)
        self.initialized = False
        self.enabled = False
        self.soundfonts = []
    def init(self):
        self.initialized = True
    def inited(self):
        return self.initialized
    def enabled(self):
        return self.enabled
    def enable(self):
        self.fs = fluidsynth.Synth()
        self.enabled = True
    def soundfont(self, fn, track, bank, preset):
        sfid = self.fs.sfload(fn)
        self.fs.program_select(track, sfid, bank, preset)
        return sfid
    def supported(self):
        return not ERROR
    def support(self):
        return ['fluidsynth','soundfonts']
    def note_on(self, t, n, v):
        self.fs.noteon(t, n, v)
    def note_off(self, t, n, v):
        self.fs.noteoff(t, v)
        pass
    def stop(self):
        pass

# instrument.export(FluidSynth)
export = FluidSynth

