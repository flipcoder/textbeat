#!/usr/bin/env python
import sys, time, math, random
import pyaudio
import numpy as np
from array import array

if __name__=='__main__':
    class Device(object):
        pass
else:
    from .. import device

class Synth(Device):

    SINE = lambda f: math.sin(math.tau * f)
    TRIANGLE = lambda f: -f if math.fmod(f*2.0) > 0.5 else f + 0.25
    SQUARE = lambda f: 1.0 if f < 0.5 else -1.0
    SAW = lambda f: math.fmod(f + 0.5, 1.0)
    NOISE = lambda f: random.random()
    
    FRAMES = 512
    RATE = 44100
    CHANNELS = 1
    WIDTH = 2
    class Oscillator:
        def __init__(self, synth, dest=True):
            self.reset()
            self.synth = synth
            if dest:
                self.dest = Synth.Oscillator(synth, False)
        def reset(self):
            self.amp = 0.0
            self.midinote = -1
            self.pitch = 0.0
            self.phase = 0.0
            self.vib_phase = 0.0
            self.mix = 1.0
            self.vib = 0.0
            self.func = Synth.SINE
            self.t = 0
            self.next = False
            self.dest = None
            self.sign = 0
            self.ch = 0
            self.end = False
            self.rate_crush = 1
            # self.bufs = None
            # self.fx = None
            # self.enabled = False
        def note(self, n=0, v=1.0, **kwargs):
            self.dest.func = kwargs.get('func', Synth.SINE)
            self.dest.midinote = n
            self.dest.pitch = Synth.midi_to_pitch(n)
            self.dest.amp = v
            self.next = True
            print('note', n, v, self.dest.pitch)
        # def on(self):
        #     self.note(0, 1.0)
        def generate(self):
            pass
        def off(self):
            self.dest.amp = 0.0
            self.dest.midinote = -1
            self.next = True
        def swap(self):
            nx = self.dest
            self.reset()
            nx.dest = self
            return nx
        def sample(self, n, block_recur=False):
            osc = self
            v = osc.amp * osc.func(osc.phase) * osc.mix
            sgn = np.sign(v)
            if self.next and (sgn==0 or (self.sign!=0 and sgn!=self.sign)):
                if block_recur:
                    assert False
                    return osc, 0.0
                osc = osc.swap()
                osc.sign = sgn
                vib = math.sin(self.vib_phase)
                self.vib_phase += self.vib / Synth.RATE
                osc.phase += osc.rate_crush * osc.pitch / Synth.RATE
                return osc.sample(True)
            osc.sign = sgn
            if not block_recur:
                vib = math.sin(self.vib_phase)
                self.vib_phase += self.vib / Synth.RATE
                osc.phase += osc.rate_crush * (osc.pitch+vib) / Synth.RATE
            return osc, v
        def done(self):
            return (self.next and self.dest.midinote==-1) or (not self.next and self.midinote==-1)
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.midinotes = [None] * 127
        self.crush = 256
        self.osc = 1
        self.osc_count = 0
        self.oscs = [Synth.Oscillator(self) for x in range(self.osc)]
        self.buf = array('h', list(range(Synth.FRAMES)))
        self.stream = self.audio.open(
            format=self.audio.get_format_from_width(Synth.WIDTH),
            channels=Synth.CHANNELS,
            rate=Synth.RATE,
            frames_per_buffer=Synth.FRAMES,
            output=True,
            stream_callback=self.callback()
        )
        self.stream.start_stream()
    @staticmethod
    def midi_to_pitch(f):
        return pow(2.0, (f - 69.0)/12.0) * 440.0
    def callback(self):
        def internal_callback(in_data, frame_count, time_info, status):
            for n in range(frame_count):
                self.buf[n] = 0
            self.osc_count = 0
            for o in range(len(self.oscs)):
                osc = self.oscs[o]
                if osc.done():
                    break
                self.osc_count += 1
                vs = 0
                for n in range(frame_count // osc.rate_crush):
                    osc, smp = osc.sample(n)
                    self.oscs[o] = osc
                    v = self.fx(int(0x7fff * smp)) // self.crush * self.crush
                    for i in range(osc.rate_crush):
                        self.buf[n * osc.rate_crush + i] += v
            return (bytes(self.buf), pyaudio.paContinue)
        return internal_callback
    # def run(self):
        # self.stream.start_stream()
        # while self.stream.is_active():
        #     time.sleep(0.1)
    def fx(self, v):
        return v
    def deinit(self):
        for osc in self.oscs:
            if osc.midinote >= 0:
                osc.off()
                while self.osc_count > 0:
                    time.sleep(0.1)
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()
    def note(self, n, v=1.0, **kwargs):
        ch = kwargs.get('ch', 0)
        func = kwargs.get('func', Synth.SINE)
        o = 0
        for osc in self.oscs:
            if osc.done():
                osc = self.oscs[o]
                osc.note(n, v, func=func)
                return o
            o += 1
        osc = self.oscs[0]
        osc.note(n, v, func=func)
        return 0
    def off(self, **kwargs):
        ch = kwargs.get('ch', None)
        for osc in self.oscs:
            if (ch==None) or ch == osc.ch:
                if not osc.done():
                    osc.off()
        self.oscs.sort(key=lambda x: x.midinote==-1)

if __name__=='__main__':
    synth = Synth()
    for i in range(3):
        synth.note(60 + i * 2, func=Synth.SAW)
        time.sleep(0.5)
        synth.off()
        time.sleep(0.5)
    synth.deinit()
    del synth

