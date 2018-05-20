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
    return CHORDS[normalize_chord(c)].split(' ')

RANGE = 109
OCTAVE_BASE = 5

class Channel:
    def __init__(self, ch, player):
        self.ch = ch
        self.player = player
        self.reset()
    def reset(self):
        self.midich = 0
        self.notes = [0] * RANGE
        self.mode = 1 # 0 is NONE which inherits global mode
        self.scale = Scale.DIATONIC
        self.instrument = 0
        self.octave = 0 # rel to OCTAVE_BASE
        self.mod = 0 # dont read in mod, just track its change by this channel
        self.hold = False
        self.arp = [] # list of notes to arpegiate
        self.pattern = [] # relative steps to
        self.vel = 0
    def note_on(self, n, v=-1):
        if v == -1:
            v = self.vel
        if n < 0 or n > RANGE:
            return
        self.notes[n] = v
        self.player.note_on(n,v,self.midich)
    def note_off(self, n, v=-1):
        if v == -1:
            v = self.vel
        if n < 0 or n >= RANGE:
            return
        if self.notes[n]:
            self.player.note_off(n,v,self.midich)
            self.notes[n] = 0
    def note_all_off(self, v=-1): # this is not the midi equivalent
        if v == -1:
            v = self.vel
        for n in xrange(RANGE):
            if self.notes[n]:
                self.player.note_off(n,v,self.midich)
        self.notes = [0] * RANGE
        if self.mod>0:
            self.cc(1,0)
    def midi_channel(self, midich):
        self.note_all_off()
        self.midich = midich
    def cc(self, cc, val): # control change
        cmd = 0b1011
        status = (cmd<<4) + ch.midich
        print "MIDI"
        PLAYER.write_short(status,cc,val)
        self.mod = val

# class Bookmark:
#     def __init__(self,name,row):
#         self.name = name
#         self.line = row

midi.init()
PLAYER = pygame.midi.Output(pygame.midi.get_default_output_id())
INSTRUMENT = 0
PLAYER.set_instrument(INSTRUMENT)
CHANNELS = [Channel(ch, PLAYER) for ch in range(16)]
TEMPO = 120
GRID = 4 # Grid subdivisions of a beat (4 = sixteenth note)

buf = []

class StackFrame:
    def __init__(self, row):
        self.row = row
        self.counter = 0 # repeat call counter

BOOKMARKS = {}
CALLSTACK = []

CCHAR = '<>=~.\'\`,_'

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
                if ls and ls[-1]==':':
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
        cells = filter(None, cells)
        ch_idx = 0
        # if not line.strip():
        #     continue

        notes = []

        # COMMENT
        if buf and buf[row][0] == ';':
            row += 1
            continue
        
        ctrl = False # ctrl line, %
        for cell in cells:
            # TODO: check for global cmds here
            if cell.startswith('%'):
                ctrl = True
                cell = cell[1:]
                for tok in cell.split(' '):
                    if tok.startswith('tempo='):
                        tok = tok[len('tempo='):].split(' ')
                        TEMPO=int(tok[0])
                        continue
                    elif tok.startswith('grid='): # grid subdivisions
                        tok = tok[len('grid='):].split(' ')
                        GRID=int(tok[0])
                        continue
                cell = []
            
            if ctrl:
                continue

            ignore = False
            ch = CHANNELS[ch_idx]
            # if INSTRUMENT != ch.instrument:
            #     PLAYER.set_instrument(ch.instrument)
            #     INSTRUMENT = ch.instrument
            cell = cell.strip()
            print cell
            
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
                if len(cell)>1 and cell[1:] == '@': # @@ return/pop callstack
                    frame = CALLSTACK[-1]
                    CALLSTACK = CALLSTACK[:-1]
                    row = frame.row
                    break
                cell = cell[1:].split('*').strip() # * repeats
                bm = cell[0] # bookmark name
                if len(cell)>1:
                    count = int(cell[1]) if len(cell)>1 else 1
                frame = CALLSTACK[-1]
                if count: # repeats remaining
                    CALLSTACK.append(StackFrame(row))
                    row = BOOKMARKS[bm]
                    continue
            
            if cell=='-' or cell[0]=='=': # mute
                ch.note_all_off()
                ch_idx += 1
                continue

            if cell[0]=='-':
                ch.note_all_off()
                ch.hold = False
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
                    if len(tok) >= 2 and tok[0:2] =='bb':
                        n -= 2
                        tok = tok[2:]
                        if not expanded: cell = cell[2:]
                    elif tok[0] =='b':
                        n -= 1
                        tok = tok[1:]
                        if not expanded: cell = cell[1:]
                    elif len(tok) >= 2 and tok[0:2] =='##':
                        n += 2
                        tok = tok[2:]
                        if not expanded: cell = cell[2:]
                    elif tok[0] =='#':
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
                        print 'chord ' + chordname
                        notes.append(n)
                        chord_root = n
                        continue
                
                notes.append(n + chord_root-1)
            
            base = 4 + OCTAVE_BASE * 12
            p = base + octave * 12 # default
            
            cell = cell.strip() # ignore spaces

            vel = 127
            nomute = False
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
                    nomute = True
                    # row_events += 1d
                # SEP
                elif c=='.':
                    cell = cell[1:] #ignore
                    nomute = True
                # HOLD
                elif c=='_':
                    ch.hold = True
                    cell = cell[1:]
                    assert notes # holding w/o note?
                elif c=='v':
                    cell = cell[1:]
                    # get number
                    num = ''
                    for char in cell:
                        if char.isdigit():
                            num += char
                        else:
                            break
                    assert num != ''
                    vel = int(num) / ('9'*len(num))
                    ch.vel = vel

            if notes and not nomute and not ch.hold:
                ch.note_all_off()

            if not ignore:
                for n in notes:
                    ch.note_on(p + n, vel)
            
            ch_idx += 1

        while True:
            try:
                time.sleep(60.0 / TEMPO / GRID)
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

