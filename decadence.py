#!/usr/bin/env python2

import sys
import time
import pygame
import pygame.midi as midi
import traceback


SCALES = []
SCALE_NAMES = []
PLAYER = None

class Scale:
    DIATONIC = 0
    PENTATONIC = 1
    HARMONIC_MAJOR = 2
    HARMONIC_MINOR = 3
    MELODIC_MINOR = 4
    CHROMATIC = 5
    def __init__(self, name, intervals): # modes)
        self.name = name
        self.intervals = intervals
        # self.modes = modes

SCALES += [
    Scale('diatonic', '2212221'),
    Scale('pentatonic', '23223')
]
for scale in SCALES:
    SCALE_NAMES.append(scale.name)

RANGE = 109

class Channel:
    def __init__(self, ch, player):
        self.ch = ch # index in CHANNELS list
        self.midich = 0
        self.notes = [0] * RANGE
        self.scale = Scale.DIATONIC
        self.player = player
        self.instrument = 0
        self.octave = 5
    def note_on(self, n, v):
        if n < 0 or n > RANGE:
            return
        self.notes[n] = v
        self.player.note_on(n,v,self.midich)
    def note_off(self, n, v=127):
        if n < 0 or n >= RANGE:
            return
        if self.notes[n]:
            self.player.note_off(n,v,self.midich)
            self.notes[n] = 0
    def note_all_off(self, v=127):
        for n in xrange(RANGE):
            if self.notes[n]:
                self.player.note_off(n,v,self.midich)
        self.notes = [0] * RANGE
    def midi_channel(self, midich):
        self.note_all_off()
        self.midich = midich

midi.init()
PLAYER = pygame.midi.Output(pygame.midi.get_default_output_id())
INSTRUMENT = 0
PLAYER.set_instrument(INSTRUMENT)
CHANNELS = [Channel(ch, PLAYER) for ch in range(16)]

buf = []
BOOKMARKS = {}

try:
    slept = True
    with open(sys.argv[1]) as f:
        for line in f.readlines():
            buf += [line]
    row = 0

    while True:
        try:
            line = buf[row]
        except:
            break
        if line:
            if line[-1] == '\n':
                line = line[:-1]
            elif len(line)>2 and line[-2:-1] == '\r\n':
                line = line[:-2]
        cells = ' '.join(line.split(' ')).split(' ')
        ch_idx = 0
        # if not line.strip():
        #     continue
        print line
        for cell in cells:
            ch = CHANNELS[ch_idx]
            # if INSTRUMENT != ch.instrument:
            #     PLAYER.set_instrument(ch.instrument)
            #     INSTRUMENT = ch.instrument
            cell = cell.strip()
            
            # empty
            if not cell:
                ch_idx += 1
                continue
            
            # bookmark
            if cell[-1]==':':
                BOOKMARKS[cell[:-1]] = row
                ch_idx += 1
                continue
            
            ch.note_all_off()
            
            if cell[0]=='-' or cell[0]=='=': # mute
                ch_idx += 1
                continue
            
            scale = SCALES[ch.scale]
            notecount = len(scale.intervals)
            # octave = int(cell[0]) / notecount
            note = ((int(cell[0])-1) % notecount) + 1
            n = 0
            for i in xrange(note):
                n += int(scale.intervals[i-1])
            octave = ch.octave
            base = 4
            mn = 0
            
            mn = n + base + octave * 12
            
            if len(cell) >= 3:
                if cell[1] == '+':
                    shift = int(cell[2]) if cell[2].isdigit() else 0
                    mn = n + base + octave * 12 + shift * 12
                elif cell[1] == '-':
                    shift = int(cell[2]) if cell[2].isdigit() else 0
                    mn = n + base + octave * 12 - shift * 12
                elif cell[1] == '=':
                    octave = int(cell[2]) if cell[2].isdigit() else 5
                    ch.octave = octave
                    mn = n + base + octave * 12
            
            ch.note_on(mn,127)
            
            ch_idx += 1

        time.sleep(0.1)

        row += 1

except Exception, ex:
    print traceback.format_exc(ex)

for ch in CHANNELS:
    ch.note_all_off()
    ch.player = None

del PLAYER
midi.quit()

