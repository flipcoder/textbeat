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
    CHROMATIC = 0
    DIATONIC = 1
    PENTATONIC = 2
    HARMONIC_MAJOR = 3
    HARMONIC_MINOR = 4
    MELODIC_MINOR = 5
    def __init__(self, name, intervals): # modes)
        self.name = name
        self.intervals = intervals
        # self.modes = modes

DIATONIC = Scale('diatonic', '2212221')
SCALES += [
    Scale('chromatic', '1'*12),
    DIATONIC,
    Scale('pentatonic', '23223')
]
for scale in SCALES:
    if scale:
        SCALE_NAMES.append(scale.name)

# for lookup, normalize name first
CHORDS = {
    "maj": "3 5",
    # "maj7": "3 5 7",
    "m": "b3 5",
    # "m7": "b3 5 7",
    "aug": "3 #5",
    "dom7": "3 5 b7",
    "dim": "b3 b5",
    "dim7": "b3 b5 bb7",
    "sus": "4 5",
    "sus2": "2 5",
    "sus7": "2 5 7b",
    "6th": "3 5 6",
    "9th": "3 5 b7 9",
    "lyd": "3 #4",

    # informal
    "q": "4 b7", # quartal
    "qt": "5 9", # quintal
    "mu": "2 3 5", # maj add2
    "mu-": "2 3b 5", # min add2
    "wa": "3 4 5", # maj add4
    "wa-": "b3 4 5", # min add4
}

RANGE = 109
DEFAULT_OCTAVE = 5

class Channel:
    def __init__(self, ch, player):
        self.ch = ch # index in CHANNELS list
        self.midich = 0
        self.notes = [0] * RANGE
        self.mode = 1 # 0 is NONE which inherits global mode
        self.scale = Scale.DIATONIC
        self.player = player
        self.instrument = 0
        self.octave = DEFAULT_OCTAVE
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

# class Bookmark:
#     def __init__(self,name,row):
#         self.name = name
#         self.line = row

midi.init()
PLAYER = pygame.midi.Output(pygame.midi.get_default_output_id())
INSTRUMENT = 0
PLAYER.set_instrument(INSTRUMENT)
CHANNELS = [Channel(ch, PLAYER) for ch in range(16)]

buf = []

class StackFrame:
    def __init__(self, row):
        self.row = row
        self.counter = 0 # repeat call counter

BOOKMARKS = {}
CALLSTACK = []

try:
    slept = True
    fn = sys.argv[1] if len(sys.argv)>=2 else 'songs/test.dec'
    with open(fn) as f:
        for line in f.readlines():
            if line:
                if line[-1] == '\n':
                    line = line[:-1]
                elif len(line)>2 and line[-2:0] == '\r\n':
                    line = line[:-2]
                
                if not line:
                    continue
                ls = line.strip()
                
                # place bookmark
                if ls[-1]==':':
                    # only store INITIAL bookmark position here
                    if not ls[:-1] in BOOKMARKS:
                        BOOKMARKS[ls[:-1]] = len(buf)

            buf += [line]
    row = 0

    quitflag = False
    while True:
        try:
            line = buf[row]
        except:
            break
        # cells = ' '.join(line.split(' ')).split(' ')
        cells = line.split(' '*2)
        ch_idx = 0
        # if not line.strip():
        #     continue
        print line
        for cell in cells:
            ignore = False
            ch = CHANNELS[ch_idx]
            # if INSTRUMENT != ch.instrument:
            #     PLAYER.set_instrument(ch.instrument)
            #     INSTRUMENT = ch.instrument
            cell = cell.strip()
            
            # empty
            if not cell or cell=='.':
                ch_idx += 1
                continue
            
            # set bookmark
            if cell[-1]==':':
                # allow override of bookmarks in case of reuse
                BOOKMARKS[cell[:-1]] = row
                ch_idx += 1
                continue
            
            # jumps
            if cell[0]=='@':
                # use * for number of calls
                if len(cel)>1 and cell[1:] == '@': # @@ return/pop callstack
                    frame = CALLSTACK[-1]
                    CALLSTACK = CALLSTACK[:-1]
                    row = frame.row
                    break
                tok = cell[1:].split('*').strip() # * repeats
                bm = tok[0] # bookmark name
                if len(tok)>1:
                    count = int(tok[1]) if len(tok)>1 else 1
                frame = CALLSTACK[-1]
                if count: # repeats remaining
                    CALLSTACK.append(StackFrame(row))
                    row = BOOKMARKS[bm]
                    continue
            
            ch.note_all_off()
            
            if cell[0]=='-' or cell[0]=='=': # mute
                ch_idx += 1
                continue
            
            scale = SCALES[ch.scale]
            notecount = len(scale.intervals)
            # octave = int(cell[0]) / notecount
            c = cell[0]
            octave = ch.octave
            
            # sharps/flats before note number/name
            n = 0
            if c=='b' or c=='#':
                if len(cell) >= 2 and cell[0:2] =='bb':
                    n -= 2
                    cell = cell[2:]
                elif cell[1] =='b':
                    n -= 1
                    cell = cell[1:]
                elif len(cell) >= 2 and cell[0:2] =='##':
                    n += 2
                    cell = cell[2:]
                elif cell[1] =='#':
                    n += 1
                    cell = cell[1:]
            
            if c.isdigit():
                # numbered notation
                # wrap notes into 1-7 range before scale lookup
                note = ((int(c)-1) % notecount) + 1
                n = 0
                for i in xrange(note):
                    n += int(scale.intervals[i-1])
            else:
                
                c = cell[0]
                # flats, sharps after note names?
                if len(cell) > 2 and cell[1:3] =='bb':
                    n -= 2
                    cell = cell[2:]
                elif c == 'b':
                    n -= 1
                    cell = cell[1:]
                elif len(cell) > 2 and cell[1:3] =='##':
                    n += 2
                    cell = cell[2:]
                elif c =='#':
                    n += 1
                    cell = cell[1:]
                c = cell[0]

                # note names
                try:
                    note = ' CDEFGAB'.index(c)
                    for i in xrange(note):
                        n += int(DIATONIC.intervals[i-1])
                    cell = cell[1:]
                except: # TODO add type
                    ignore = True

            base = 4
            mn = 0
            
            mn = n + base + octave * 12 # default

            cell = cell.strip() # allow spaces inside cell here
            
            if len(cell) >= 1:
                print cell
                if c == '+':
                    print "+"
                    c = cell[1]
                    shift = int(c) if c.isdigit() else 0
                    mn = n + base + (octave+shift) * 12
                if c == '>':
                    c = cell[1]
                    shift = int(c) if c.isdigit() else 1
                    octave += shift
                    mn = n + base + octave * 12
                    ch.octave = octave
                elif c == '-':
                    c = cell[1]
                    shift = int(c) if c.isdigit() else 0
                    mn = n + base + (octave+shift) * 12
                elif c == '<':
                    c = cell[1]
                    shift = int(c) if c.isdigit() else 1
                    octave += shift
                    mn = n + base + octave * 12
                    ch.octave = octave
                elif c == '=':
                    c = cell[1]
                    octave = int(cell[1]) if cell[1].isdigit() else DEFAULT_OCTAVE
                    ch.octave = octave
                    mn = n + base + octave * 12
            
            if not ignore:
                ch.note_on(mn,127)
            
            ch_idx += 1

        while True:
            try:
                time.sleep(0.15)
                break
            except:
                print('')
                try:
                    for ch in CHANNELS:
                        ch.note_all_off()
                    raw_input(' === PAUSED === ')
                except:
                    quitflag = True
                    break

        if quitflag:
            break
        
        row += 1

except Exception, ex:
    print traceback.format_exc(ex)

for ch in CHANNELS:
    ch.note_all_off()
    ch.player = None

del PLAYER
midi.quit()

