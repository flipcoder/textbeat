#!/usr/bin/env python2

import sys
import pygame
import pygame.midi as midi
import traceback
import time
import random

SCALES = []
SCALE_NAMES = []
PLAYER = None

random.seed()

class Scale:
    CHROMATIC = 0
    DIATONIC = 1
    PENTATONIC = 2
    HARMONIC_MAJOR = 3
    HARMONIC_MINOR = 4
    MELODIC_MINOR = 5
    NEAPOLITAN_MAJOR = 6
    NEAPOLITAN_MINOR = 7
    def __init__(self, name, intervals): # modes)
        self.name = name
        self.intervals = intervals
        # self.modes = modes

DIATONIC = Scale('diatonic', '2212221')
SCALES = [
    Scale('chromatic', '1'*12),
    DIATONIC,
    Scale('pentatonic', '23223')
]
for scale in SCALES:
    if scale:
        SCALE_NAMES.append(scale.name)

# for lookup, normalize name first, add root
CHORDS = {
    "maj": "3 5",
    "maj7": "3 5 7",
    "m": "b3 5",
    "m7": "b3 5 b7",
    "aug": "3 #5",
    "dom7": "3 5 b7",
    "dom7b5": "3 b5 b7",
    "dim": "b3 b5",
    "dim7": "b3 b5 bb7",
    "sus": "4 5",
    "sus2": "2 5",
    "sus7": "4 5 7b",
    "sixth": "3 5 6",
    "ninth": "3 5 b7 9",
    "fifth": "5",
    "pow": "5 8",
    "q": "4 b7", # quartal
    "qt": "5 9", # quintal
    "mu": "2 3 5", # maj add2
    "mu7": "2 3 5", # maj add2
    "mu-": "2 b3 5", # m add2
    "mu-7": "2 b3 5 7", # m7 add2
    "wa": "3 4 5", # maj add4
    "wa7": "3 4 5 7", # maj7 add4
    "wa-7": "b3 4 5 7", # m7 add4
    "lyd": "3 #4",
}
CHORDS_ALT = {
    "+": "aug",
    "augmented": "aug",
    "-": "m",
    "major": "maj",
    "ma7": "maj7",
    "major7": "maj7",
    "min": "m",
    "minor": "m",
    "-7": "minor7",
    "min7": "m7",
    "minor7": "m7",
    "7": "dom7",
    "seven": "dom7",
    "p": "pow",
    "power": "pow",
    "lydian": "lyd",
    "f": "fifth",
    "5th": "fifth",
    "9": "ninth",
    "9th": "ninth",
    "11": "eleventh",
    "11th": "eleventh"
}
def normalize_chord(c):
    c = c.lower()
    try:
        c = CHORDS_ALT[c]
    except KeyError:
        pass
    return c

def expand_chord(c):
    # if c=='rand':
    #     print CHORDS.values()
    #     r = random.choice(CHORDS.values())
    #     print r
    #     return r
    return CHORDS[normalize_chord(c)].split(' ')

RANGE = 109
OCTAVE_BASE = 5

MIDI_CC = 0b1011

class Channel:
    def __init__(self, ch, player):
        self.ch = ch
        self.player = player
        self.reset()
    def reset(self):
        self.midich = 0
        self.notes = [0] * RANGE
        self.held_notes = [False] * RANGE # held note filter
        self.mode = 1 # 0 is NONE which inherits global mode
        self.scale = Scale.DIATONIC
        self.instrument = 0
        self.octave = 0 # rel to OCTAVE_BASE
        self.mod = 0 # dont read in mod, just track its change by this channel
        # self.hold = False
        self.arp_notes = [] # list of notes to arpegiate
        self.arp_idx = 0
        self.arp_limit = 0
        self.arp_cycle_limit = 0 # cycles remaining, only if limit != 0
        self.arp_pattern = [] # relative steps to
        self.arp_enabled = False
        self.vel = 127
        self.staccato = False
    def note_on(self, n, v=-1, hold=False):
        if v == -1:
            v = self.vel
        if n < 0 or n > RANGE:
            return
        self.notes[n] = v
        self.held_notes[n] = hold
        # print "on " + str(n)
        self.player.note_on(n,v,self.midich)
    def note_off(self, n, v=-1):
        if v == -1:
            v = self.vel
        if n < 0 or n >= RANGE:
            return
        if self.notes[n]:
            # print "off " + str(n)
            self.player.note_off(n,v,self.midich)
            self.notes[n] = 0
            self.held_notes[n] = 0
    def note_all_off(self, mute_held=False, v=-1): # this is not the midi equivalent
        if v == -1:
            v = self.vel
        for n in xrange(RANGE):
            # if mute_held, mute held notes too, otherwise ignore
            muteheld_cond = True
            if not mute_held:
                muteheld_cond =  not self.held_notes[n]
            if self.notes[n] and muteheld_cond:
                self.player.note_off(n,v,self.midich)
                self.notes[n] = 0
                self.held_notes[n] = 0
                # print "off " + str(n)
        # self.notes = [0] * RANGE
        if self.mod>0:
            self.cc(1,0)
        # self.arp_enabled = False
    def midi_channel(self, midich):
        self.note_all_off()
        self.midich = midich
    def cc(self, cc, val): # control change
        status = (MIDI_CC<<4) + ch.midich
        # print "MIDI (%s,%s)" % (bin(MIDI_CC),val)
        PLAYER.write_short(status,cc,val)
        self.mod = val
    def arp(self, notes, count=0, pattern=[1]):
        self.arp_enabled = True
        self.arp_notes = notes
        self.arp_cycle_limit = count
        self.arp_cycle = count
        self.arp_pattern = pattern
        self.arp_pattern_idx = 0
        self.arp_idx = 0 # use inversions to move this start point (?)
    def arp_stop(self):
        self.arp_enabled = False
        self.note_all_off()
    def arp_next(self):
        # print 'arp_next'
        assert self.arp_enabled
        note = ch.arp_notes[ch.arp_idx]
        if self.arp_cycle_limit:
            if ch.arp_idx+1 == len(ch.arp_notes): # cycle?
                ch.arp_cycle -= 1
                if ch.arp_cycle == 0:
                    # print 'stop arp'
                    ch.arp_enabled = False
                # if ch.arp_cycle = 0
        # increment according to pattern order
        ch.arp_idx = (ch.arp_idx+self.arp_pattern[self.arp_pattern_idx])%len(ch.arp_notes)
        self.arp_pattern_idx = (self.arp_pattern_idx+1) % len(self.arp_pattern)
        return note

# class Marker:
#     def __init__(self,name,row):
#         self.name = name
#         self.line = row

midi.init()
PLAYER = pygame.midi.Output(pygame.midi.get_default_output_id())
INSTRUMENT = 0
PLAYER.set_instrument(INSTRUMENT)
CHANNELS = [Channel(ch, PLAYER) for ch in range(16)]
TEMPO = 120.0
GRID = 4.0 # Grid subdivisions of a beat (4 = sixteenth note)

buf = []

class StackFrame:
    def __init__(self, row):
        self.row = row
        self.counter = 0 # repeat call counter

MARKERS = {}
CALLSTACK = [StackFrame(-1)]

CCHAR = '<>=~.\'\`,_cvgm&^'

try:
    slept = True

    # run command
    if sys.argv[1] == '-c':
        buf = ' '.join(sys.argv[2:]).split(';')
        TEMPO = 90
        GRID = 1
    else: 
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
                    
                    # place marker
                    if ls and ls[-1]==':':
                        # only store INITIAL marker position here
                        if not ls[:-1] in MARKERS:
                            MARKERS[ls[:-1]] = len(buf)

                buf += [line]
    row = 0

    quitflag = False
    while True:
        try:
            line = buf[row]
        except:
            break
        # cells = ' '.join(line.split(' ')).split(' ')
        # cells = line.split(' '*2)
        cells = line.split(' ')
        cells = filter(None, cells)
        ch_idx = 0
        # if not line.strip():
        #     continue

        notes = []

        # COMMENT
        if buf and buf[row][0] == ';':
            row += 1
            continue

        # set marker
        if buf[-1]==':': # suffix marker
            # allow override of markers in case of reuse
            MARKERS[buf[:-1]] = row
            ch_idx += 1
            continue
        elif buf[0]==':': #prefix marker
            # allow override of markers in case of reuse
            MARKERS[buf[1:]] = row
            ch_idx += 1
            continue

        
        # jumps
        if buf[0]=='@':
            if len(buf)==1:
                row = 0
                continue
            if len(buf)>1 and buf[1:] == '@': # @@ return/pop callstack
                frame = CALLSTACK[-1]
                CALLSTACK = CALLSTACK[:-1]
                row = frame.row
                continue
            buf = buf[1:].split('*') # * repeats
            bm = buf[0] # marker name
            count = 0
            if len(buf)>1:
                count = int(buf[1]) if len(buf)>1 else 1
            frame = CALLSTACK[-1]
            frame.count = count
            if count: # repeats remaining
                CALLSTACK.append(StackFrame(row))
                row = MARKERS[bm]
                continue
            else:
                row = MARKERS[bm]
                continue
        
        ctrl = False # ctrl line, %
        for cell in cells:
            # TODO: check for global cmds here
            if cell.startswith('%'):
                ctrl = True
                cell = cell[1:]
                for tok in cell.split(' '):
                    # print tok
                    if tok.startswith('tempo='):
                        tok = tok[len('tempo='):].split(' ')
                        TEMPO=float(tok[0])
                        cell = cell[len('tempo='):]
                    elif tok.startswith('grid='): # grid subdivisions
                        tok = tok[len('grid='):].split(' ')
                        GRID=float(tok[0])
                        cell = cell[len('grid='):]
                cell = []
            
            if ctrl:
                break

            ignore = False
            ch = CHANNELS[ch_idx]
            # if INSTRUMENT != ch.instrument:
            #     PLAYER.set_instrument(ch.instrument)
            #     INSTRUMENT = ch.instrument
            cell = cell.strip()
            print cell
            
            # empty
            if not cell:
                ch_idx += 1
                continue
            
            if cell=='-' or cell[0]=='=': # mute
                ch.note_all_off(True) # mute held as well
                ch_idx += 1
                continue

            if cell[0]=='-': # mute prefix
                ch.note_all_off(True)
                # ch.hold = False
                cell = cell[1:]
            
            scale = SCALES[ch.scale]
            notecount = len(scale.intervals)
            # octave = int(cell[0]) / notecount
            c = cell[0]
            octave = ch.octave
            
            # PROCESS NOTE
            next_note = None
            chord_notes = [] # notes to process from chord
            notes = [] # outgoing notes to midi
            chord_root = 1
            expanded = False # inside chord? if so, don't advance cell itr
            while True:
                if not chord_notes:
                    tok = cell
                else:
                    tok = chord_notes[0]
                    chord_notes = chord_notes[1:]
                
                if not tok:
                    break
            
                # sharps/flats before note number/name
                n = 0
                c = tok[0]
                if c=='b' or c=='#':
                    if len(tok) > 2 and tok[0:2] =='bb':
                        n -= 2
                        tok = tok[2:]
                        if not expanded: cell = cell[2:]
                    elif c =='b':
                        n -= 1
                        tok = tok[1:]
                        if not expanded: cell = cell[1:]
                    elif len(tok) > 2 and tok[0:2] =='##':
                        n += 2
                        tok = tok[2:]
                        if not expanded: cell = cell[2:]
                    elif c =='#':
                        n += 1
                        tok = tok[1:]
                        if not expanded: cell = cell[1:]
                c = tok[0]
                
                if c.isdigit():
                    # numbered notation
                    # wrap notes into 1-7 range before scale lookup
                    note = ((int(c)-1) % notecount) + 1
                    for i in xrange(note):
                        # dont use scale for expanded chord notes
                        if expanded:
                            n += int(DIATONIC.intervals[i-1])
                        else:
                            n += int(scale.intervals[i-1])
                    tok = tok[1:]
                    if not expanded: cell = cell[1:]
                
                elif c in 'b#ABCDEFG':
                    
                    # flats, sharps after note names?
                    if tok:
                        lt = len(tok)
                        if lt > 2 and tok[1:3] =='bb':
                            n -= 2
                            tok = tok[:2]
                            if not expanded: cell = cell[:2]
                        elif lt > 1 and tok[1] == 'b':
                            n -= 1
                            tok = tok[:1]
                            if not expanded: cell = cell[:1]
                        elif lt > 2 and tok[1:3] =='##':
                            n += 2
                            tok = tok[:2]
                            if not expanded: cell = cell[:2]
                        elif lt > 1 and tok[1] =='#':
                            n += 1
                            tok = tok[:1]
                            if not expanded: cell = cell[:1]
                    
                    c = tok[0]

                    # note names, don't use these in chord defn
                    try:
                        # dont allow lower case, since 'b' means flat
                        note = ' CDEFGAB'.index(c)
                        for i in xrange(note):
                            n += int(DIATONIC.intervals[i-1])
                        tok = tok[1:]
                        if not expanded: cell = cell[1:]
                    except ValueError:
                        ignore = True
                else:
                    break # cmd stuff
                
                # CHORDS
                if cell and not expanded:
                    chordname = ''

                    # cut chord name from text after it
                    for char in cell:
                        if char not in CCHAR:
                            chordname += char
                        else:
                            break
                    
                    # this will continue looping to process notes
                    if chordname:
                        try:
                            cell = cell[len(chordname):] 
                            chord_notes = expand_chord(chordname)
                            expanded = True
                        except KeyError, e:
                            print 'key error'
                            break
                        # print 'chord ' + chordname
                        notes.append(n)
                        chord_root = n
                        continue
                
                notes.append(n + chord_root-1)

            if ch.arp_enabled:
                if notes: # incoming notes?
                    # interupt arp
                    ch.arp_stop()
                else:
                    # continue arp
                    notes = [ch.arp_next()]
            
            base = 4 + OCTAVE_BASE * 12
            p = base + octave * 12 # default
            
            cell = cell.strip() # ignore spaces

            vel = ch.vel
            mute = False
            hold = False
            
            # stacatto current doesn't persist
            
            while len(cell) >= 1:
                # All tokens here must be listed in CCHAR
                
                ## + and - symbols are changed to mean minor and aug chords
                # if c == '+':
                #     print "+"
                #     c = cell[1]
                #     shift = int(c) if c.isdigit() else 0
                #     mn = n + base + (octave+shift) * 12
                c = cell[0]
                # if c == '-' or c == '+' or c.isdigit(c):
                #     cell = cell[1:] # deprecated, ignore
                    # continue

                # OCTAVE SHIFT UP
                if c == '>' or c=='\'' or c=='\`':
                    sym = c
                    cell = cell[1:]
                    if cell and cell[0].isdigit():
                        shift = int(cell[0])
                        cell = cell[1:]
                    else:
                        shift = 1
                    octave += shift
                    p = base + octave * 12
                    if sym== '>': ch.octave = octave # persist
                    # row_events += 1
                # elif c == '-':
                #     c = cell[1]
                #     shift = int(c) if c.isdigit() else 0
                #     p = base + (octave+shift) * 12
                # OCTAVE SHIFT DOWN
                elif c == '<' or c==',':
                    sym = c
                    cell = cell[1:]
                    if cell and cell[0].isdigit():
                        shift = int(cell[0])
                        cell = cell[1:]
                    else:
                        shift = 1
                    octave -= shift
                    p = base + octave * 12
                    if sym == '<':
                        ch.octave = octave # persist
                    # row_events += 1
                # SET OCTAVE
                elif c == '=':
                    cell = cell[1:]
                    if cell and cell[0].isdigit():
                        octave = int(cell[0])
                        cell = cell[1:]
                    else:
                        octave = 0 # default
                        shift = 1
                    ch.octave = octave
                    p = base + octave * 12
                    # row_events += 1
                # VIBRATO
                elif c == '~': # vibrato -- eventually using pitch wheel
                    ch.cc(1,127)
                    cell = cell[1:]
                    # row_events += 1d
                # HOLD
                elif c=='_':
                    hold = True # use hold flag in note on func
                    cell = cell[1:]
                    assert notes # holding w/o note?
                elif c=='g': # gain/volume
                    cell = cell[1:]
                    # get number
                    num = ''
                    for char in cell:
                        if char.isdigit():
                            num += char
                        else:
                            break
                    assert num != ''
                    cell = cell[len(num):]
                    vel = int((float(num) / float('9'*len(num)))*127)
                    ch.cc(7,vel)
                elif c=='v': # velocity
                    cell = cell[1:]
                    # get number
                    num = ''
                    for char in cell:
                        if char.isdigit():
                            num += char
                        else:
                            break
                    assert num != ''
                    cell = cell[len(num):]
                    vel = int((float(num) / float('9'*len(num)))*127)
                    ch.vel = vel
                    # print vel
                elif c=='c': # control change
                    cell = cell[1:]
                    # get number
                    num = ''
                    for char in cell:
                        if char.isdigit():
                            num += char
                        else:
                            break
                    assert num != ''
                    cc = int(num)
                    cell = cell[len(num):]
                    for char in cell:
                        if char.isdigit():
                            num += char
                        else:
                            break
                    assert num != ''
                    num = int(ccval)
                    ch.cc(cc,ccval)
                elif c=='&':
                        
                    # repeat limit?
                    num = ''
                    for char in cell[1:]:
                        if char.isdigit():
                            num += char
                        else:
                            break
                    
                    cell = cell[1+len(num):]
                    
                    if not num:
                        num = 0
                    else:
                        num = int(num)
                    
                    if notes:
                        ch.arp(notes, num)
                        notes = [ch.arp_next()]
                        # print notes
                        # print 'arp start??'
                    else:
                        # & restarts arp (if no note)
                        ch.arp_enabled = True
                        ch.arp_idx = 0
                elif c=='m': # midi channel
                    num = ''
                    for char in cell[1:]:
                        if char.isdigit():
                            num += char
                        else:
                            break
                    cell = cell[1+len(num):]
                    ch.channel(num)
                elif c=='.':
                    if notes:
                        ch.staccato = True
                    cell = cell[1:] # otherwise ignore
                    
                # elif c=='/': # bend in
                # elif c=='\\': # bend down

            if notes or mute:
                ch.note_all_off()

            if not ignore:
                for n in notes:
                    ch.note_on(p + n, vel, hold)
            
            ch_idx += 1

        while True:
            try:
                if not ctrl:
                    t = 60.0 / TEMPO / GRID
                    time.sleep(t / 2.0)
                    for ch in CHANNELS:
                        if ch.staccato:
                            ch.note_all_off()
                            ch.staccato = False
                    time.sleep(t / 2.0)
                break
            except KeyboardInterrupt:
                print('')
                try:
                    for ch in CHANNELS:
                        ch.note_all_off(True)
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
    ch.note_all_off(True)
    ch.player = None

del PLAYER
midi.quit()

