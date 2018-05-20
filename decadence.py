#!/usr/bin/env python2

import sys
import pygame
import pygame.midi as midi
import traceback
import time
import random

SCALES = []
SCALE_NAMES = []

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
    "p4": "4",
    "p5": "5",
    
    # chords and voicings
    "maj": "3 5",
    "maj7": "3 5 7",
    "maj7b5": "3 5b 7",
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
    "M7": "maj7",
    "M7b5": "maj7b5",
    "min": "m",
    "minor": "m",
    "-7": "m7",
    "min7": "m7",
    "minor7": "m7",
    "7": "dom7",
    "seven": "dom7",
    "power": "pow",
    "lydian": "lyd",
    "9": "ninth",
    "9th": "ninth",
    "11": "eleventh",
    "11th": "eleventh"
}
def normalize_chord(c):
    try:
        c = CHORDS_ALT[c]
    except KeyError:
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
MIDI_PROGRAM = 0b1100

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
        self.arp_once = False
        self.vel = 64
        self.staccato = False
        self.patch_num = 0
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
        self.player.write_short(status,cc,val)
        self.mod = val
    def patch(self, p):
        print p
        self.patch_num = p
        status = (MIDI_CC<<4) + ch.midich
        self.player.write_short(status,p)
    def arp(self, notes, count=0, pattern=[1]):
        self.arp_enabled = True
        self.arp_notes = notes
        self.arp_cycle_limit = count
        self.arp_cycle = count
        self.arp_pattern = pattern
        self.arp_pattern_idx = 0
        self.arp_idx = 0 # use inversions to move this start point (?)
        self.arp_once = False
    def arp_stop(self):
        self.arp_enabled = False
        self.note_all_off()
    def arp_next(self):
        assert self.arp_enabled
        note = ch.arp_notes[ch.arp_idx]
        if ch.arp_idx+1 == len(ch.arp_notes): # cycle?
            self.arp_once = True
            if self.arp_cycle_limit:
                ch.arp_cycle -= 1
                if ch.arp_cycle == 0:
                    # print 'stop arp'
                    ch.arp_enabled = False
                # if ch.arp_cycle = 0
        # increment according to pattern order
        ch.arp_idx = (ch.arp_idx+self.arp_pattern[self.arp_pattern_idx])%len(ch.arp_notes)
        self.arp_pattern_idx = (self.arp_pattern_idx+1) % len(self.arp_pattern)
        return note

def peel_number(s):
    r = ''
    for char in cell:
        if char.isdigit():
            r += char
        else:
            break
    return r

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

# control chars that are definitely not note or chord names
CCHAR = '<>=~.\'\`,_&^|!?'

# entries: [time, func]
SCHEDULE = []

try:
    slept = True

    FN = None
    
    # run command
    for arg in sys.argv:
        if arg=='-c':
            buf = ' '.join(sys.argv[2:]).split(';')
            TEMPO = 120
            GRID = 2
            break
        if arg=='-s':
            buf = ' '.join(sys.argv[2:]).split(' ')
            TEMPO = 120
            GRID = 2
            break
    else: 
        FN = sys.argv[1] if len(sys.argv)>=2 else 'songs/test.dec'
        with open(FN) as f:
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
                        bm = ls[:-1]
                        if not bm in MARKERS:
                            MARKERS[bm] = len(buf)
                    elif ls and ls[0]==':':
                        # only store INITIAL marker position here
                        bm = ls[1:]
                        if not bm in MARKERS:
                            MARKERS[bm] = len(buf)

                buf += [line]
    
    row = 0
    quitflag = False
    
    # skip to row (+ param)
    for arg in sys.argv:
        if arg.startswith('+'):
            try:
                row = int(arg[1:])
            except ValueError:
                try:
                    row = MARKERS[arg[1:]]
                except KeyError:
                    print 'invalid entry point'
                    quitflag = True

    while not quitflag:
        line = '.'
        try:
            line = buf[row]
        except IndexError:
            if not FN: # finish arps in shell mode
                arps_remaining = 0
                for ch in CHANNELS:
                    if ch.arp_enabled:
                        if not ch.arp_once:
                            line = "."
                            arps_remaining += 1

                if arps_remaining == 0:
                    break
            else:
                break
        # cells = ' '.join(line.split(' ')).split(' ')
        # cells = line.split(' '*2)
        cells = line.split(' ')
        cells = filter(None, cells)
        ch_idx = 0
        # if not line.strip():
        #     continue
        
        if line:
            
            # COMMENT
            if line and line.strip()[0] == ';':
                row += 1
                continue
            # set marker
            elif line[-1]==':': # suffix marker
                # allow override of markers in case of reuse
                MARKERS[line[:-1]] = row
                row += 1
                # continue
            elif line[0]==':': #prefix marker
                # allow override of markers in case of reuse
                MARKERS[line[1:]] = row
                row += 1
            
            # TODO: check for global cmds here
            if line.startswith('%'):
                line = line[1:]
                for tok in line.split(' '):
                    # print tok
                    if tok.startswith('tempo='):
                        tok = tok[len('tempo='):].split(' ')
                        TEMPO=float(tok[0])
                        line = line[len('tempo='):]
                    elif tok.startswith('grid='): # grid subdivisions
                        tok = tok[len('grid='):].split(' ')
                        GRID=float(tok[0])
                        line = line[len('grid='):]
                row += 1
                continue
            
            # jumps
            if line[0]=='@':
                if len(line)==1:
                    row = 0
                    continue
                if len(line)>1 and line[1:] == '@': # @@ return/pop callstack
                    frame = CALLSTACK[-1]
                    CALLSTACK = CALLSTACK[:-1]
                    row = frame.row
                    continue
                line = line[1:].split('*') # * repeats
                bm = line[0] # marker name
                count = 0
                if len(line)>1:
                    count = int(line[1]) if len(line)>1 else 1
                frame = CALLSTACK[-1]
                frame.count = count
                if count: # repeats remaining
                    CALLSTACK.append(StackFrame(row))
                    row = MARKERS[bm]
                    continue
                else:
                    row = MARKERS[bm]
                    continue
            
        ctrl = False
        
        for cell in cells:

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
            accidentals = False
            loop = True
            noteloop = True
            while noteloop:
                if not chord_notes: # processing cell note
                    tok = cell
                else: # looping notes of a chord?
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
                    accidentals = True
                c = tok[0]
                
                if c.isdigit():
                    # numbered notation
                    # wrap notes into 1-7 range before scale lookup
                    c = int(c)
                    note = (c-1) % notecount + 1
                    for i in xrange(note):
                        # dont use scale for expanded chord notes
                        if expanded:
                            n += int(DIATONIC.intervals[i-1])
                        else:
                            n += int(scale.intervals[i-1])
                        n += (c-1) / notecount * 12
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
                        # accidentals = True # dont need this
                    
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
                    # assume 1 if there's a chord, otherwise ignore this
                    ignore = True # reenable if there's a chord listed
                
                # CHORDS
                is_chord = False
                if not expanded:
                    if tok:
                        chordname = ''

                        # cut chord name from text after it
                        for char in tok:
                            if char not in CCHAR:
                                chordname += char
                            else:
                                break

                        # this will continue looping to process notes
                        if chordname:
                            try:
                                chord_notes = expand_chord(chordname)
                                expanded = True
                                try:
                                    cell = cell[len(chordname):] 
                                    tok = []
                                    is_chord = True
                                except:
                                    assert False
                            except KeyError, e:
                                # may have grabbed a ctrl char, pop one
                                if len(chord_notes)>1: # can pop?
                                    try:
                                        chord_notes = expand_chord(chordname[:-1])
                                        expanded = True
                                        try:
                                            tok = tok[len(chordname)-1:] 
                                            cell = cell[len(chordname)-1:] 
                                            is_chord = True
                                        except:
                                            assert False
                                    except KeyError:
                                        print 'key error'
                                        break
                                else:
                                    noteloop = True
                                    break
                            
                            if is_chord:
                                # assert not accidentals # accidentals with no note name?
                                notes.append(n)
                                chord_root = n
                                ignore = False # reenable default root if chord was w/o note name
                                continue
                            else:
                                break
                        else: # blank chord name
                            tok = []
                            noteloop = False
                    else: # not tok and not expanded
                        tok = []
                        noteloop = False
                # else and not chord_notes:
                #     # last note in chord, we're done
                #     tok = []
                #     noteloop = False
                    
                notes.append(n + chord_root-1)

                if expanded and not chord_notes:
                    break

            if ignore:
                notes = []

            # TODO: arp doesn't work if channel not visible/present, move this
            if ch.arp_enabled:
                if notes: # incoming notes?
                    # interupt arp
                    ch.arp_stop()
                else:
                    # continue arp
                    notes = [ch.arp_next()]

            if notes:
                print notes
            
            base = 4 + OCTAVE_BASE * 12
            p = base + octave * 12 # default
            
            cell = cell.strip() # ignore spaces

            vel = ch.vel
            mute = False
            hold = False
           
            t = 0.0
            schedule = False
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
                elif c == '<' or c == ',':
                    sym = c
                    cell = cell[1:]
                    if cell and cell[0].isdigit():
                        shift = int(cell[0])
                        cell = cell[1:]
                    else:
                        shift = 1
                    octave -= shift
                    p = base + octave * 12
                    if sym == '<': ch.octave = octave # persist
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
                    vel = int((float(num) / 100)*127)
                    ch.vel = vel
                    # print vel
                elif c=='c': # MIDI CC
                    # get number
                    cell = cell[1:]
                    num = peel_number(cell)
                    assert num
                    cc = int(num)
                    cell = cell[len(num)+1:]
                    num = peel_number(cell)
                    assert num
                    cell = cell[len(num):]
                    ccval = int(num)
                    ch.cc(cc,ccval)
                elif c=='p': # program/patch change
                    cell = cell[1:]
                    num = peel_number(cell)
                    assert num
                    cell = cell[len(num):]
                    p = int(num)
                    # ch.cc(0,p)
                    ch.patch(p)
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
                    num = peel_number(cell)
                    cell = cell[1+len(num):]
                    ch.midi_channel(num)
                elif c=='e': # note end
                    num = ''
                    for char in cell[1:]:
                        if char.isdigit() or char=='.':
                            num += char
                        else:
                            break
                    cell = cell[1+len(num):]
                    t = float(num)
                    assert -0.0001 > t > 1.0001
                    schedule = True
                # eventually make sure these don't clash with schedule
                elif len(cell)>=1 and cell[:2]=='..':
                    if notes and not ignore:
                        SCHEDULE.append([0.25, lambda _: ch.note_all_off()])
                    cell = cell[2:]
                elif c=='.':
                    if notes and not ignore:
                        SCHEDULE.append([0.5, lambda _: ch.note_all_off()])
                    cell = cell[1:]
                elif c=='s': # note start
                    num = ''
                    cell = cell[1:]
                    num = peel_number(cell)
                    cell = cell[len(num):] # ignore
                    num = float('0.'+num) if num else 0.5
                    SCHEDULE.append([num, lambda _: ch.note_all_off()])
                elif c=='|':
                    cell = cell[1:] # ignore
                elif len(cell)>=2 and cell[:2]=='!!': # loud accent
                    vel = 127
                    cell = cell[2:]
                elif c=='!': # accent
                    vel = min(127,int(ch.vel+0.5*(127-ch.vel)))
                    cell = cell[1:]
                elif len(cell)>=2 and cell[:2]=='??': # very quiet
                    vel = max(0,int(ch.vel-0.25*(127-ch.vel)))
                    cell = cell[2:]
                elif c=='?': # quiet
                    vel = max(0,int(ch.vel-0.5*(127-ch.vel)))
                    cell = cell[1:]
                else:
                    print cell + " ???"
                    cell = []
                
                # elif c=='/': # bend in
                # elif c=='\\': # bend down

            if notes or mute:
                ch.note_all_off()

            if not ignore:
                for n in notes:
                    f = lambda _: ch.note_on(p + n, vel, hold)
                    if not schedule:
                        f(0)
                    else:
                        SCHEDULE.append(t,f)
            
            ch_idx += 1

        while True:
            tp = 0.0 # timepassed percent of frame
            t = 60.0 / TEMPO / GRID
            try:
                if not ctrl:
                    # sort by schedule time
                    SCHEDULE = sorted(SCHEDULE, key=lambda e: e[0])
                    for ev in SCHEDULE:
                        if ev[0] > 1.0:
                            ev[0] -= 1.0
                        else:
                            # sleep until next event
                            time.sleep(t*(ev[0] - tp))
                            # do event
                            ev[1](0)
                            # calc time passed
                            tp += ev[0]
                    
                    # sleep until next frame
                    SCHEDULE = []
                    time.sleep(t*(1.0-tp))
                    
                    break # while true is for catch exceptions, break!
            except KeyboardInterrupt, ex:
                print ' '
                print traceback.format_exc(ex)
                print ' '
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
    print ' '
    print traceback.format_exc(ex)

for ch in CHANNELS:
    ch.note_all_off(True)
    ch.player = None

del PLAYER
midi.quit()

