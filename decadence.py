#!/usr/bin/env python2

import sys
import time
import pygame
import pygame.midi as midi

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
    def __init__(self, name, intervals, modes):
        self.name = name
        self.intervals = intervals
        self.modes = modes

SCALE_NAMES.append('diatonic')
SCALES.append(Scale(
    'diatonic', '2212221',
    [   "ionian",
        "dorian",
        "phyrigian",
        "lydian",
        "mixolydian",
        "aeolian",
        "locrian" ]
))

class Channel:
    def __init__(self, player):
        self.notes = [0] * 255
        self.scale = Scale.DIATONIC
        self.player = player
        self.instrument = 0
    def midi_note_on(self, n, v):
        self.notes[n] = v
        PLAYER.note_on(n,v)
    def midi_note_off(self, n, v=127):
        if self.notes[n]:
            PLAYER.note_off(n,v)
            self.notes[n] = v

midi.init()
PLAYER = pygame.midi.Output(0)
INSTRUMENT = 0
PLAYER.set_instrument(INSTRUMENT)
CHANNELS = [Channel(PLAYER) for x in range(16)]

try:
    with open(sys.argv[1]) as f:
        for line in f.readlines():
            cells = line.split('|')
            ch_idx = 0
            for cell in cells:
                for note in ch.notes:
                    PLAYER.note_off(note,127)
                ch = CHANNELS[ch_idx]
                if INSTRUMENT != ch.instrument:
                    PLAYER.set_instrument(INSTRUMENT)
                    INSTRUMENT = ch.instrument
                cell = cell.strip()
                scale = SCALES[ch.scale]
                notecount = len(scale.intervals)
                # octave = int(line[0]) / notecount
                note = ((int(line[0])-1) % notecount) + 1
                p = 0
                for i in xrange(note):
                    p += int(scale.intervals[i-1])
                mn = 64 + int(p) # midi note
                if line[1] == '\'':
                    mn += 12
                elif line[1] == '.':
                    mn -= 12
                ch.midi_note_on(mn,127)
                
                ch_idx += 1

            if not line.strip():
                time.sleep(0.2)

except Exception, ex:
    print ex
    for ch in CHANNELS:
        for note in ch.notes:
            PLAYER.note_off(note,127)

del PLAYER
midi.quit()

