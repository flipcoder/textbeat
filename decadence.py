#!/usr/bin/env python2

#import curses
import os
import sys
import pygame
import pygame.midi as midi
import traceback
import time
import random
# import readline
# import atexit

# histfile = os.path.join(os.path.expanduser("~"), ".decadence_history")
# try:
#     readline.read_history_file(histfile)
#     readline.set_history_length(1000)
# except FileNotFoundError:
#     pass

# atexit.register(readline.write_history_file, histfile)

VERSION = '0.1'
SCALE_NAMES = []

random.seed()

class Scale:
    def __init__(self, name, intervals):
        self.name = name
        self.intervals = intervals
        self.modes = [''] * len(intervals)
    def addmode(self, name, index):
        assert index > 0
        self.modes[index-1] = name
    def mode(self, index):
        return self.mode[index]

DIATONIC = Scale('diatonic', '2212221')
SCALES = {
    'chromatic': Scale('chromatic', '1'*12),
    'wholetone': Scale('wholetone', '2'*6),
    'diatonic': DIATONIC,
    'bebop': Scale('bebop', '2212p121'),
    'pentatonic': Scale('pentatonic', '23223'),
    'blues': Scale('blues', '32p132'),
    'melodicminor': Scale('melodicminor', '2122221'),
    # Scale('harmonicminor', '')
    # Scale('harmonicmajor', '')
}
# modes and scale aliases
MODES = {
    'jazzminor': ('melodicminor',1),
    'majorscale': ('diatonic',1),
    'ionian': ('diatonic',1),
    'dorian': ('diatonic',2),
    'phyrigan': ('diatonic',3),
    'lydian': ('diatonic',4),
    'mixolydian': ('diatonic',5),
    'aeolian': ('diatonic',6),
    'minorscale': ('diatonic',6),
    'locrian': ('diatonic',7),
}
for k,v in MODES.iteritems():
    SCALES[v[0]].addmode(k,v[1])

# for lookup, normalize name first, add root
# number chords can't be used with note numbers
CHORDS = {
    # intervals that don't match chord names,
    # using these with numbered notation requires '
    "m2": "b2",
    "2": "2",
    "m3": "b3",
    "3": "3",
    "4": "4",
    "5": "5",
    
    # chords and voicings
    "maj": "3 5",
    "maj7": "3 5 7",
    "maj9": "3 5 7 9",
    "maj7b5": "3 b5 7",
    "maj9": "3 5 7 9",
    "majadd9": "3 5 9",
    "maj9b5": "3 b5 7 9",
    "m": "b3 5",
    "m7": "b3 5 b7",
    "m9": "b3 5 7 9",
    "madd9": "3 b5 9",
    "m7b5": "3b b5 7",
    "m9b5": "b3 b5 7 9",
    "aug": "3 #5",
    "dom7": "3 5 b7",
    "dom7b5": "3 b5 b7",
    "dim": "b3 b5",
    "dim7": "b3 b5 bb7",
    "sus": "4 5",
    "sus2": "2 5",
    "sus7": "4 5 7b",
    "6": "3 5 6",
    "9": "3 5 b7 9",
    "11": "",
    "13": "3 5 b7 9 13",
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
    "lyd": "3 b5", # lydian chord, maj7b5no7
    "11": "3 5 b7 9 #11",
}
CHORDS_ALT = {
    "+": "aug",
    "p4": "4",
    "p5": "5",
    "augmented": "aug",
    "-": "m",
    "M": "maj",
    "major": "maj",
    "ma7": "maj7",
    "ma9": "maj9",
    "Madd9": "majadd9",
    "mdd9": "madd9",
    "major7": "maj7",
    "M7": "maj7",
    "M7b5": "maj7b5",
    "min": "m",
    "minor": "m",
    "-7": "m7",
    "min7": "m7",
    "minor7": "m7",
    "7": "dom7",
    "p": "pow",
    "11th": "11",
    "o": "dim",
    "o7": "dim7",
    "7o": "dim7",
}

GM = [
    "Acoustic Grand Piano",
    "Bright Acoustic Piano",
    "Electric Grand Piano",
    "Honky-tonk Piano",
    "Electric Piano 1",
    "Electric Piano 2",
    "Harpsichord",
    "Clavi",
    "Celesta",
    "Glockenspiel",
    "Music Box",
    "Vibraphone",
    "Marimba",
    "Xylophone",
    "Tubular Bells",
    "Dulcimer",
    "Drawbar Organ",
    "Percussive Organ",
    "Rock Organ",
    "Church Organ",
    "Reed Organ",
    "Accordion",
    "Harmonica",
    "Tango Accordion",
    "Acoustic Guitar (nylon)",
    "Acoustic Guitar (steel)",
    "Electric Guitar (jazz)",
    "Electric Guitar (clean)",
    "Electric Guitar (muted)",
    "Overdriven Guitar",
    "Distortion Guitar",
    "Guitar harmonics",
    "Acoustic Bass",
    "Electric Bass (finger)",
    "Electric Bass (pick)",
    "Fretless Bass",
    "Slap Bass 1",
    "Slap Bass 2",
    "Synth Bass 1",
    "Synth Bass 2",
    "Violin",
    "Viola",
    "Cello",
    "Contrabass",
    "Tremolo Strings",
    "Pizzicato Strings",
    "Orchestral Harp",
    "Timpani",
    "String Ensemble 1",
    "String Ensemble 2",
    "SynthStrings 1",
    "SynthStrings 2",
    "Choir Aahs",
    "Voice Oohs",
    "Synth Voice",
    "Orchestra Hit",
    "Trumpet",
    "Trombone",
    "Tuba",
    "Muted Trumpet",
    "French Horn",
    "Brass Section",
    "SynthBrass 1",
    "SynthBrass 2",
    "Soprano Sax",
    "Alto Sax",
    "Tenor Sax",
    "Baritone Sax",
    "Oboe",
    "English Horn",
    "Bassoon",
    "Clarinet",
    "Piccolo",
    "Flute",
    "Recorder",
    "Pan Flute",
    "Blown Bottle",
    "Shakuhachi",
    "Whistle",
    "Ocarina",
    "Lead 1 (square)",
    "Lead 2 (sawtooth)",
    "Lead 3 (calliope)",
    "Lead 4 (chiff)",
    "Lead 5 (charang)",
    "Lead 6 (voice)",
    "Lead 7 (fifths)",
    "Lead 8 (bass + lead)",
    "Pad 1 (new age)",
    "Pad 2 (warm) ",
    "Pad 3 (polysynth)",
    "Pad 4 (choir)",
    "Pad 5 (bowed)",
    "Pad 6 (metallic)",
    "Pad 7 (halo)",
    "Pad 8 (sweep)",
    "FX 1 (rain)",
    "FX 2 (soundtrack)",
    "FX 3 (crystal)",
    "FX 4 (atmosphere)",
    "FX 5 (brightness)",
    "FX 6 (goblins)",
    "FX 7 (echoes)",
    "FX 8 (sci-fi)",
    "Sitar",
    "Banjo",
    "Shamisen",
    "Koto",
    "Kalimba",
    "Bag pipe",
    "Fiddle",
    "Shanai",
    "Tinkle Bell",
    "Agogo",
    "Steel Drums",
    "Woodblock",
    "Taiko Drum",
    "Melodic Tom",
    "Synth Drum",
    "Reverse Cymbal",
    "Guitar Fret Noise",
    "Breath Noise",
    "Seashore",
    "Bird Tweet",
    "Telephone Ring",
    "Helicopter",
    "Applause",
    "Gunshot",
]
for i in xrange(len(GM)): GM[i] = GM[i].lower()

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
    def __init__(self, ch, player, schedule):
        self.ch = ch
        self.player = player
        self.schedule = schedule
        self.reset()
    def reset(self):
        self.midich = 0
        self.notes = [0] * RANGE
        self.held_notes = [False] * RANGE # held note filter
        self.mode = 1 # 0 is NONE which inherits global mode
        self.scale = DIATONIC
        self.instrument = 0
        self.octave = 0 # rel to OCTAVE_BASE
        self.mod = 0 # dont read in mod, just track its change by this channel
        # self.hold = False
        self.arp_notes = [] # list of notes to arpegiate
        self.arp_idx = 0
        self.arp_cycle_limit = 0 # cycles remaining, only if limit != 0
        self.arp_pattern = [] # relative steps to
        self.arp_enabled = False
        self.arp_once = False
        self.vel = 64
        # self.off_vel = 64
        self.staccato = False
        self.patch_num = 0
        self.schedule.clear_channel(self)
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
        self.schedule.clear_channel(ch)
    def midi_channel(self, midich):
        self.note_all_off()
        self.midich = midich
    def cc(self, cc, val): # control change
        status = (MIDI_CC<<4) + self.midich
        # print "MIDI (%s,%s)" % (bin(MIDI_CC),val)
        self.player.write_short(status,cc,val)
        self.mod = val
    def patch(self, p):
        if isinstance(p,basestring):
            # look up instrument string in GM
            i = 0
            inst = p
            stop_search = False
            for i in xrange(len(GM)):
                continue_search = False
                for pword in inst.split(' '):
                    print pword
                    print GM[i].split(' ')
                    if pword.lower() not in GM[i].split(' '):
                        continue_search = True
                        break
                    p = i
                    stop_search=True
                    
                if stop_search:
                    break
                if continue_search:
                    assert i < len(GM)-1
                    continue
        self.patch_num = p
        status = (MIDI_PROGRAM<<4) + self.midich
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
                    ch.arp_enabled = False
        # increment according to pattern order
        ch.arp_idx = (ch.arp_idx+self.arp_pattern[self.arp_pattern_idx])%len(ch.arp_notes)
        self.arp_pattern_idx = (self.arp_pattern_idx+1) % len(self.arp_pattern)
        return note

class Event:
    def __init__(self, t, func, ch):
        self.t = t
        self.func = func
        self.ch = ch

class Schedule:
    def __init__(self):
        self.events = [] # time,func,ch,skippable
        self.tp = 0.0
    # all note mute and play events should be marked skippable
    def pending(self):
        return len(self.events)
    def add(self, e):
        self.events.append(e)
    def clear(self):
        self.events = []
    def clear_channel(self, ch):
        self.events = [ev for ev in self.events if ev.ch!=ch]
    def logic(self, t):
        processed = 0
        # if self.tp > 0.0, we're resuming from kb interupt
        try:
            self.events = sorted(self.events, key=lambda e: e.t)
            for ev in self.events:
                if ev.t > 1.0:
                    ev.t -= 1.0
                else:
                    # sleep until next event
                    frac = (ev.t - self.tp)
                    if frac >= 0.0:
                        time.sleep(t*frac)
                        ev.func(0)
                        self.tp += ev.t # only inc if positive
                    
                    # calc time passed
                    processed += 1
            
            # events is sorted, so we can cut baesd on processed count
            time.sleep(t*(1.0-self.tp)) # remaining time
            self.tp = 0.0
            self.events = self.events[processed:]
        except KeyboardInterrupt, ex:
            # don't replay events
            self.events = self.events[processed:]
            raise ex

def count_seq(seq, match=''):
    if not seq:
        return 0
    if match == '':
        match = seq[0]
        r = 1
    for c in seq[1:]:
        if c != match:
            break
        r+=1
    return r

def peel_uint(s, d=None):
    a,b = peel_uint_s(s,d)
    return (int(a),b)

# don't cast
def peel_uint_s(s, d=None):
    r = ''
    for ch in s:
        if ch.isdigit():
            r += ch
        else:
            break
    if not r: return (d,0) if d!=None else ('',0)
    return (r,len(r))

def peel_roman_s(s, d=None):
    nums = 'ivx'
    r = ''
    case = -1 # -1 unknown, 0 low, 1 uppper
    for ch in s:
        chl = ch.lower()
        chcase = (chl==ch)
        if chl in nums:
            if case > 0 and case != chcase:
                break # changing case ends peel
            r += ch
            chcase = 0 if (chl==ch) else 1
        else:
            break
    if not r: return (d,0) if d!=None else ('',0)
    return (r,len(r))

def peel_int(s, d=None):
    r = ''
    for ch in s:
        if ch.isdigit():
            r += ch
        elif ch=='-' and not r:
            r += ch
        else:
            break
    if r == '-': return (0,0)
    if not r: return (d,0) if d!=None else (0,0)
    if d != None: return (d,0)
    return (int(r),len(r))

def peel_float(s, d=None):
    r = ''
    decimals = 0
    for ch in s:
        if ch.isdigit():
            r += ch
        elif ch=='-' and not r:
            r += ch
        elif ch=='.':
            if decimals >= 1:
                break
            r += ch
            decimals += 1
        else:
            break
    # don't parse trailing decimals
    if r and r[-1]=='.': r = r[:-1]
    if not r: return (d,0) if d!=None else (0,0)
    return (float(r),len(r))

# class Marker:
#     def __init__(self,name,row):
#         self.name = name
#         self.line = row

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
CCHAR = '<>=~.\'\`,_&^|!?*\"#'

SCHEDULE = []
# INIT
SEPARATORS = []
CHANNEL_HISTORY = ['.'] * 16
row = 0
midi.init()
dev = 0
for i in xrange(midi.get_count()):
    port = pygame.midi.get_device_info(i)
    # print port
    # timidity
    if port[1].lower()=='timidity port 0':
        dev = i
    # qsynth
    elif port[1].lower().startswith('synth input port'):
        dev = i
    # helm will autoconnect

# PLAYER = pygame.midi.Output(pygame.midi.get_default_output_id())
PLAYER = pygame.midi.Output(dev)
INSTRUMENT = 0
PLAYER.set_instrument(0)
SCHEDULE = Schedule()
CHANNELS = [Channel(ch, PLAYER, SCHEDULE) for ch in xrange(16)] 

try:
    FN = None
    row = 0
    quitflag = False
    mode = 'n' # n normal c command s sequence

    next_arg = 1
    # request_tempo = False
    # request_grid = False
    skip = 0
    for i in xrange(1,len(sys.argv)):
        if skip:
            skip -= 1
            continue
        arg = sys.argv[i]
        if arg.startswith('-t'):
            if len(arg)>2:
                TEMPO = float(arg[2:]) # same token: -t100
            else:
                # look ahead and eat next token
                TEMPO = float(sys.argv[i+1]) # split token: -t 100
                skip += 1
        # request_tempo = True
        elif arg.startswith('-g'):
            if len(arg)>2:
                GRID = float(arg[2:]) # same token: -g100
            else:
                # look ahead and eat next token
                GRID = float(sys.argv[i+1]) # split token: -g 100
                skip += 1
        elif arg.startswith('-n'): # note value (changes grid)
            if len(arg)>2:
                GRID = float(arg[2:])/4.0 # same token: -n4
            else:
                # look ahead and eat next token
                GRID = float(sys.argv[i+1])/4.0 # split token: -n 4
                skip += 1
        elif arg.startswith('-p'):
            if len(arg)>2:
                vals = arg[2:].split(',')
            else:
                vals = sys.argv[i+1].split(',')
                skip += 1
            for i in xrange(len(vals)):
                val = vals[i]
                if val.isdigit():
                    CHANNELS[i].patch(int(val))
                else:
                    CHANNELS[i].patch(val)
        # request_grid = True
        elif arg == '-l':
            mode = 'l'
        elif arg == '-c':
            mode = 'c'
        else:
            next_arg = i
            break
        next_arg = i+1
    
    if mode=='l':
        buf = ' '.join(sys.argv[next_arg:]).split(';')
    elif mode=='c':
        buf = ' '.join(sys.argv[next_arg:]).split(' ')
    else: # mode n
        if len(sys.argv)>=2:
            FN = sys.argv[-1]
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
        else:
            mode = 'sh'
    
    for i in xrange(len(sys.argv)):
        arg = sys.argv[i]
        
        # skip to row (+ param)
        if arg.startswith('+'):
            try:
                row = int(arg[1:])
            except ValueError:
                try:
                    row = MARKERS[arg[1:]]
                except KeyError:
                    print 'invalid entry point'
                    quitflag = True
    
    if mode=='sh':
        print 'decadence v'+str(VERSION)
        print 'Copyright (c) 2018 Grady O\'Connell'
        print 'github.com/flipcoder/decadence'
        print ''
        print 'Read the manual and look at examples. Have fun!'

    while not quitflag:
        line = '.'
        try:
            line = buf[row]
        except IndexError:
            # done with file, finish playing some stuff
            
            arps_remaining = 0
            if not FN or mode == 'sh': # finish arps in shell mode
                for ch in CHANNELS:
                    if ch.arp_enabled:
                        if ch.arp_cycle_limit or not ch.arp_once:
                            arps_remaining += 1
                            line = '.'
                if not arps_remaining and mode != 'sh':
                    break
            
            if not arps_remaining and not SCHEDULE.pending(): # finish schedule always
                if mode == 'sh':
                    for ch in CHANNELS:
                        ch.note_all_off()
                    buf += raw_input('DC> ').split(' ')
                    continue
                else:
                    break
        # cells = ' '.join(line.split(' ')).split(' ')
        # cells = line.split(' '*2)
        
        if line.strip().startswith('|'):
            SEPARATORS = [] # clear
            # column setup!
            for i in xrange(1,len(line)):
                if line[i]=='|':
                    SEPARATORS.append(i)
       
        print line
        line = line.strip()
        
        ch_idx = 0
        
        # LINE COMMANDS
        ctrl = False

        if line:
            # COMMENTS (;)
            if line[0] == ';':
                row += 1
                continue
            
            # SEPARATORS (|)
            cells = []
            if not SEPARATORS:
                cells = line.split(' ')
                cells = filter(None, cells)
                # if not line.strip():
                #     continue
            else:
                s = 0
                seplen = len(SEPARATORS)
                for i in xrange(seplen):
                    if i == 0: continue# left side
                    cells.append(line[s:SEPARATORS[i]])
                    s = i

            # set marker
            if line[-1]==':': # suffix marker
                # allow override of markers in case of reuse
                MARKERS[line[:-1]] = row
                row += 1
                # continue
            elif line[0]==':': #prefix marker
                # allow override of markers in case of reuse
                MARKERS[line[1:]] = row
                row += 1
            
            # TODO: global 'silent' commands (doesn't take time)
            if line.startswith('%'):
                line = line[1:].strip() # remove % and spaces
                for tok in line.split(' '):
                    for var in ['T','G','N','P']:
                        if tok.startswith(var):
                            cmd = tok.split(' ')[0]
                            var = var.lower() # eventually deprecate lower case
                            op = cmd[1]
                            val = cmd[2:]
                            if not val or op=='.':
                                val = op + val # append
                                # TODO: add numbers after dots like other ops
                                if val[0]=='.':
                                    ct = count_seq(val)
                                    val = pow(0.5,count)
                                    op = '/'
                                    num,ct = peel_uint(val[:ct])
                                elif val[0]=='*':
                                    op = '*'
                                    val = pow(2.0,count_seq(val))
                            else:
                                val = float(val)
                            if op=='/':
                                if var=='G': GRID/=float(val)
                                elif var=='N': GRID/=float(val) #!
                                elif var=='G': TEMPO/=float(val)
                            elif op=='*':
                                if var=='G': GRID*=float(val)
                                elif var=='N': GRID*=float(val) #!
                                elif var=='T': TEMPO*=float(val)
                            elif op=='=':
                                if var=='G': GRID=float(val)
                                elif var=='N': GRID=float(val)/4.0 #!
                                elif var=='T': TEMPO=float(val)
                                elif var=='P':
                                    vals = val.split(',')
                                    for i in xrange(len(vals)):
                                        if val.strip().isdigit():
                                            ch[i].patch(int(val))
                                        else:
                                            ch[i].patch(val)
                                
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
            
        for cell in cells:

            ignore = False
            ch = CHANNELS[ch_idx]
            # if INSTRUMENT != ch.instrument:
            #     PLAYER.set_instrument(ch.instrument)
            #     INSTRUMENT = ch.instrument
            
            cell = cell.strip()
            # print cell
            
            if '\"' in cell:
                cell = cell.replace("\"", CHANNEL_HISTORY[ch_idx])
            else:
                CHANNEL_HISTORY[ch_idx] = cell
            
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
            
            scale = ch.scale
            notecount = len(scale.intervals)
            # octave = int(cell[0]) / notecount
            c = cell[0]
            
            # PROCESS NOTE
            next_note = None
            chord_notes = [] # notes to process from chord
            notes = [] # outgoing notes to midi
            chord_root = 1
            accidentals = False
            loop = True
            noteloop = True
            expanded = False # inside chord? if so, don't advance cell itr
            events = []
            inversion = 1 # chord inversion
            flip_inversion = False
            inverted = 0 # notes pending inversion
            chord_note_count = 0 # include root
            chord_note_index = 0
            octave = ch.octave
            
            while noteloop:
                roman = 0 # -1 lower, 1 upper, 0 none
                number_notes = False
                
                if not chord_notes: # processing cell note
                    tok = cell
                else: # looping notes of a chord?
                    tok = chord_notes[0]
                    chord_notes = chord_notes[1:]
                    chord_note_index += 1
                    # fix negative inversions
                    if inversion < 0: # not yet working
                        # print inversion
                        # print chord_note_count
                        octave += inversion/chord_note_count
                        inversion = inversion%chord_note_count
                        inverted = -inverted
                        flip_inversion = True
                
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
                
                # try to get roman numberal or number
                c,ct = peel_roman_s(tok)
                if ct:
                    lower = (c.lower()==c)
                    c = ['','i','ii','iii','iv','v','vi','vii','viii','ix','x','xi','xii'].index(c.lower())
                    roman = -1 if lower else 1
                else:
                    num,ct = peel_int(tok)
                    c = num
                
                # couldn't get it set c back to char
                if not ct:
                    c = tok[0]
                
                if ct:
                    c = int(c)
                    # numbered notation
                    # wrap notes into 1-7 range before scale lookup
                    note = (c-1) % notecount + 1
                    
                    for i in xrange(note):
                        # dont use scale for expanded chord notes
                        if expanded:
                            n += int(DIATONIC.intervals[i-1])
                        else:
                            n += int(scale.intervals[i-1])
                        n += (c-1) / notecount * 12
                    if inverted: # inverted counter
                        if flip_inversion:
                            # print (chord_note_count-1)-inverted
                            inverted -= 1
                        else:
                            n += 12
                            inverted -= 1
                    assert inversion != 0
                    if inversion!=1:
                        if flip_inversion: # not working yet
                            # print 'note ' + str(note)
                            # print 'down inv: %s' % (inversion/chord_note_count+1)
                            # n -= 12 * (inversion/chord_note_count+1)
                            pass
                        else:
                            # print 'inv: %s' % (inversion/chord_note_count)
                            n += 12 * (inversion/chord_note_count)
                    
                    tok = tok[ct:]
                    if not expanded: cell = cell[ct:]
                    
                    number_notes = not roman
                    
                    if tok and tok[0]==':':
                        tok = tok[1:] # allow chord sep
                        if not expanded: cell = cell[1:]
                    
                    # print 'note: %s' % n
                
                # NOTE LETTERS
                elif c in 'b#ABCDEFG':
                    
                    # flats, sharps after note names?
                    if tok:
                        lt = len(tok)
                        if lt >= 3 and tok[1:3] =='bb':
                            n -= 2
                            tok = tok[0] + tok[3:]
                            cell = cell[0:1] + cell[3:]
                        elif lt >= 2 and tok[1] == 'b':
                            n -= 1
                            tok = tok[0] + tok[2:]
                            if not expanded: cell = cell[0] + cell[2:]
                        elif lt > 3 and tok[1:3] =='##':
                            n += 2
                            tok = tok[0] + tok[3:]
                            cell = cell[0:1] + cell[3:]
                        elif lt >= 2 and tok[1] =='#':
                            n += 1
                            tok = tok[0] + tok[2:]
                            if not expanded: cell = cell[0] + cell[2:]
                        # print n
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
                    if tok or roman:
                        chordname = ''
                        cut = 0
                        
                        # cut chord name from text after it
                        for char in tok:
                            if char not in CCHAR:
                                chordname += char
                                cut += 1
                            else:
                                break
                        
                        if roman:
                            # print chordname
                            if chordname and not chordname[1:] in 'bcdef':
                                if roman == -1: # minor
                                    if chordname[0] in '6719':
                                        chordname = 'm' + chordname
                            else:
                                chordname = 'maj' if roman else 'm' + chordname
                        
                        # this will continue looping to process notes
                        
                        if chordname:
                            # accumulate how many chars to be processed
                            try:
                                inv_letter = ' abcdef'.index(chordname[-1])
                            
                                # num,ct = peel_int(tok[cut+1:])
                                # if ct and num!=0:
                                # cut += ct + 1
                                if inv_letter>1:
                                    inversion = max(1,inv_letter)
                                    inverted = max(0,inversion-1) # keep count of pending notes to invert
                                    # cut+=1
                                    chordname = chordname[:-1]
                                    
                            except ValueError:
                                pass
                            
                            try:
                                chord_notes = expand_chord(chordname)
                                chord_note_count = len(chord_notes)+1 # + 1 for root
                                expanded = True
                                cell = cell[cut:] 
                                tok = []
                                is_chord = True
                            except KeyError, e:
                                # may have grabbed a ctrl char, pop one
                                if len(chord_notes)>1: # can pop?
                                    try:
                                        chord_notes = expand_chord(chordname[:-1])
                                        chord_note_count = len(chord_notes) # + 1 for root
                                        expanded = True
                                        try:
                                            tok = tok[cut-1:] 
                                            cell = cell[cut-1:] 
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
                                if n == 0: n = 1
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

            del tok

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
                    ignore = True

            # if notes:
            #     print notes
            
            base = 4 + OCTAVE_BASE * 12
            p = base + octave * 12 # default
            
            cell = cell.strip() # ignore spaces

            vel = ch.vel
            mute = False
            hold = False
           
            delay = 0.0
            schedule = False

            # if cell and cell[0]=='|':
            #     if not expanded: cell = cell[1:]
             
            while len(cell) >= 1: # recompute len before check
                cl = len(cell)
                # All tokens here must be listed in CCHAR
                
                ## + and - symbols are changed to mean minor and aug chords
                # if c == '+':
                #     print "+"
                #     c = cell[1]
                #     shift = int(c) if c.isdigit() else 0
                #     mn = n + base + (octave+shift) * 12
                c = cell[0]
                c2 = None
                if cl:
                    c2 = cell[:2]
                
                if c: c = c.lower()
                if c2: c2 = c2.lower()
                
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
                # elif c=='v': # velocity - may be deprecated for !
                #     cell = cell[1:]
                #     # get number
                #     num = ''
                #     for char in cell:
                #         if char.isdigit():
                #             num += char
                #         else:
                #             break
                #     assert num != ''
                #     cell = cell[len(num):]
                #     vel = int((float(num) / 100)*127)
                #     ch.vel = vel
                #     # print vel
                elif c=='cc': # MIDI CC
                    # get number
                    cell = cell[1:]
                    cc,ct = peel_int(cell)
                    assert ct
                    cell = cell[len(num)+1:]
                    ccval,ct = peel_int(cell)
                    assert ct
                    cell = cell[len(num):]
                    ccval = int(num)
                    ch.cc(cc,ccval)
                elif cl>=2 and c=='pc': # program/patch change
                    cell = cell[2:]
                    p,ct = peel_int(cell)
                    assert ct
                    cell = cell[len(num):]
                    # ch.cc(0,p)
                    ch.patch(p)
                elif c=='&':
                    # repeat limit?
                    num,ct = peel_uint(cell[1:],0)
                    cell = cell[ct+1:]
                    if notes:
                        ch.arp(notes, num)
                        notes = [ch.arp_next()]
                        # print notes
                        # print 'arp start??'
                    else:
                        # & restarts arp (if no note)
                        ch.arp_enabled = True
                        ch.arp_idx = 0
                elif cl>=2 and cell[:2]=='ch': # midi channel
                    num,ct = peel_uint(cell[2:])
                    cell = cell[2+ct:]
                    ch.midi_channel(num)
                elif c=='*':
                    dots = count_seq(cell)
                    if notes:
                        cell = cell[dots:]
                        num,ct = peel_float(cell, 1.0)
                        cell = cell[ct:]
                        if dots==1:
                            events.append(Event(num, lambda _: ch.note_all_off(), ch))
                        else:
                            events.append(Event(num*pow(2.0,float(dots)), lambda _: ch.note_all_off(), ch))
                    else:
                        cell = cell[dots:]
                elif c=='.':
                    dots = count_seq(cell)
                    if len(c)>1 and notes:
                        cell = cell[dots:]
                        if ch.arp_enabled:
                            dots -= 1
                        if dots:
                            num,ct = peel_int_s(cell, 1.0)
                            num = int('0.' + num)
                            cell = cell[ct:]
                            events.append(Event(num*pow(0.5,float(dots)), lambda _: ch.note_all_off(), ch))
                    else:
                        cell = cell[dots:]
                elif c=='d': # note delay
                    num = ''
                    cell = cell[1:]
                    s,ct = peel_uint(cell)
                    cell = cell[ct:] # ignore
                    delay = float('0.'+num) if num else 0.5
                    schedule = True
                elif c=='|':
                    cell = cell[1:] # ignore
                elif c2=='!!': # loud accent
                    vel = 127
                    cell = cell[2:]
                elif c=='!': # accent
                    vel = min(127,int(ch.vel+0.5*(127-ch.vel)))
                    cell = cell[1:]
                elif c2=='??': # very quiet
                    vel = max(0,int(ch.vel-0.25*(127-ch.vel)))
                    cell = cell[2:]
                elif c=='?': # quiet
                    vel = max(0,int(ch.vel-0.5*(127-ch.vel)))
                    cell = cell[1:]
                elif c=='\'':
                    pass
                else:
                    print cell + " ???"
                    cell = []
                
                # elif c=='/': # bend in
                # elif c=='\\': # bend down

            if notes or mute:
                ch.note_all_off()

            for ev in events:
                if schedule: # is note delayed?
                    ev.t = delay
                SCHEDULE.add(ev)
            events = []

            for n in notes:
                f = lambda _: ch.note_on(p + n, vel, hold)
                if not schedule:
                    f(0)
                else:
                    SCHEDULE.add(Event(t,f,ch))
            
            ch_idx += 1

        while True:
            try:
                if not ctrl:
                    SCHEDULE.logic(60.0 / TEMPO / GRID)
                    break
            except KeyboardInterrupt, ex:
                print ' '
                print traceback.format_exc(ex)
                print ' '
                if mode != 'sh':
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

