#!/usr/bin/env python2

import sys
import time
import pygame
import pygame.midi as midi
import traceback

# SCALES = [
#     [
#         "Diatonic",
#         "2212221", # diatonic
#         [

#         ]
#     ],
#     [
#         "Pentatonic",
#         "23223", # pentatonic
#     ]
#     [
#     # "", # harmonic major
#     # "", # harmonic minor
#     # "" # melodic minor
#     # "1" * 11 # chromatic
# ]


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

SCALE_NAMES.append('diatonic')
SCALES.append(Scale(
    'diatonic', '2212221'
    # [   "ionian",
    #     "dorian",
    #     "phyrigian",
    #     "lydian",
    #     "mixolydian",
    #     "aeolian",
    #     "locrian" ]
))

RANGE = 109

class Channel:
    def __init__(self, ch, player):
        self.ch = ch # channel number
        self.notes = [0] * RANGE
        self.scale = Scale.DIATONIC
        self.player = player
        self.instrument = 0
    def note_on(self, n, v):
        if n < 0 or n > RANGE:
            return
        self.notes[n] = v
        self.player.note_on(n,v,self.ch)
    def note_off(self, n, v=127):
        if n < 0 or n >= RANGE:
            return
        if self.notes[n]:
            self.player.note_off(n,v,self.ch)
            self.notes[n] = 0
    def note_all_off(self, v=127):
        for n in xrange(RANGE):
            self.player.note_off(n,v,self.ch)
        self.notes = [0] * RANGE

midi.init()
PLAYER = pygame.midi.Output(pygame.midi.get_default_output_id())
INSTRUMENT = 0
PLAYER.set_instrument(INSTRUMENT)
CHANNELS = [Channel(x, PLAYER) for x in range(16)]

try:
    with open(sys.argv[1]) as f:
        for line in f.readlines():
            cells = line.split('|')
            ch_idx = 0
            if not line.strip():
                continue
            print line[:-1]
            for cell in cells:
                ch = CHANNELS[ch_idx]
                # if INSTRUMENT != ch.instrument:
                #     PLAYER.set_instrument(ch.instrument)
                #     INSTRUMENT = ch.instrument
                cell = cell.strip()
                if not cell:
                    ch_idx += 1
                    continue
                ch.note_all_off()
                
                if cell=='-': # mute
                    continue
                
                scale = SCALES[ch.scale]
                notecount = len(scale.intervals)
                # octave = int(line[0]) / notecount
                note = ((int(line[0])-1) % notecount) + 1
                n = 0
                for i in xrange(note):
                    n += int(scale.intervals[i-1])
                octave = 5
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
                        shift = int(cell[2]) if cell[2].isdigit() else 0
                        mn = n + base + shift * 12
                
                ch.note_on(mn,127)
                
                ch_idx += 1

            if line.strip():
                time.sleep(0.2)

    time.sleep(0.2)

except Exception, ex:
    print traceback.format_exc(ex)

for ch in CHANNELS:
    ch.note_all_off()

del PLAYER
midi.quit()

