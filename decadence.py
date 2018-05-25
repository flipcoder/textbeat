#!/usr/bin/env python2

import os
import sys
import pygame
import pygame.midi as midi
import traceback
import time
import random
import colorama
import subprocess
import pipes
import tempfile
import itertools
from multiprocessing import Process,Pipe
# from ConfigParser import SafeConfigParser

try:
    import ctcsound
except ImportError:
    pass

class BGCMD:
    NONE = 0
    QUIT = 1
    SAY = 2
    CACHE = 2
    CLEAR = 3

# Currently not used, caches text to speech stuff in a way compatible with jack
class BackgroundProcess:
    def __init__(self, con):
        self.con = con
        self.words = {}
        self.processes = []
    def cache(self,word):
        try:
            tmp = self.words[word]
        except:
            tmp = tempfile.NamedTemporaryFile()
            p = subprocess.Popen(['espeak', '\"'+pipes.quote(word)+'\"','--stdout'], stdout=tmp)
            p.wait()
            self.words[tmp.name] = tmp
        return tmp
    def run(self):
        devnull = open(os.devnull, 'w')
        while True:
            msg = self.con.recv()
            # print msg
            if msg[0]==BGCMD.SAY:
                tmp = self.cache(msg[1])
                # super slow, better option needed
                self.processes.append(subprocess.Popen(['mpv','-ao','jack',tmp.name],stdout=devnull,stderr=devnull))
            elif msg[0]==BGCMD.CACHE:
                self.cache(msg[1])
            elif msg[0]==BGCMD.QUIT:
                break
            elif msg[0]==BGCMD.CLEAR:
                self.words.clear()
            else:
                print 'BAD COMMAND: ' + msg[0]
            self.processses = filter(lambda p: p.poll()==None, self.processes)
        self.con.close()
        for tmp in self.words:
            tmp.close()
        for proc in self.processes:
            proc.wait()

def bgproc_run(con):
    proc = BackgroundProcess(con)
    proc.run()

if __name__!='__main__':
    sys.exit(0)

colorama.init(autoreset=True)
FG = colorama.Fore
BG = colorama.Back
STYLE = colorama.Style

BCPROC = None

# BGPIPE, child = Pipe()
# BGPROC = Process(target=bgproc_run, args=(child,))
# BGPROC.start()

# try:
#     import readline
#     import atexit
# except:
#     pass

msgs = []
def log(msg):
    global msgs
    msgs.append(msg)

VERSION = '0.1'
NUM_TRACKS = 15 # skip drum channel
NUM_CHANNELS_PER_DEVICE = 15 # "
TRACKS_ACTIVE = 1
DRUM_CHANNEL = 9
EPSILON = 0.0001
SHOWMIDI = False
DRUM_OCTAVE = -2
random.seed()

def cmp(a,b):
    return bool(a>b) - bool(a<b)
def sgn(a):
    return bool(a>0) - bool(a<0)
def orr(a,b,bad=False):
    return a if (bool(a)!=bad if bad==False else a) else b
def indexor(a,i,d=None):
    try:
        return a[i]
    except:
        return d
class Wrapper:
    def __init__(self, value=None):
        self.value = value
    def __len__(self):
        return len(self.value)

def fcmp(a, b=0.0, ep=EPSILON):
    v = a - b
    av = abs(v)
    if av > EPSILON:
        return sgn(v)
    return 0
def feq(a, b=0.0, ep=EPSILON):
    return not fcmp(a,b,ep)
def fzero(a,ep=EPSILON):
    return 0==fcmp(a,0.0,ep)
def fsnap(a,b,ep=EPSILON):
    return a if fcmp(a,b) else b
def forr(a,b,bad=False):
    return a if (fcmp(a) if bad==False else a) else b

# https://stackoverflow.com/questions/18833759/python-prime-number-checker
def is_prime(n):
    if n % 2 == 0 and n > 2: 
        return False
    return all(n % i for i in range(3, int(math.sqrt(n)) + 1, 2))

FLATS=False
NOTENAMES=True # show note names instead of numbers
SOLFEGE=False
SOLFEGE_NOTES ={
    'do': '1',
    'di': '#1',
    'ra': 'b2',
    're': '2',
    'ri': '#2',
    'me': 'b3',
    'mi': '3',
    'fa': '4',
    'fi': '4#',
    'se': 'b5',
    'sol': '5',
    'si': '#5',
    'le': 'b6',
    'la': '6',
    'li': '#6',
    'te': 'b7',
    'ti': '7',
}

def notename(n, nn=NOTENAMES, ff=FLATS, sf=SOLFEGE):
    assert type(n) == int
    if sf:
        if ff:
            return ['Do','Ra','Re','Me','Mi','Fa','Se','Sol','Le','La','Te','Ti'][n%12]
        else:
            return ['Do','Ri','Re','Ri','Mi','Fa','Fi','Sol','Si','La','Li','Ti'][n%12]
    elif nn:
        if ff:
            return ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'][n%12]
        return ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][n%12]
    else:
        if ff:
            return ['1','b2','2','b3','3','4','5b','5','b6','6','b7','7'][n%12]
        return ['1','#1','2','#2','3','4','#4','5','#5','6','#6','7'][n%12]

class Scale:
    def __init__(self, name, intervals):
        self.name = name
        self.intervals = intervals
        self.modes = [''] * 12
    def addmode(self, name, index):
        assert index > 0
        self.modes[index-1] = name
    def addmodei(self, name, index): # chromaticc index
        assert index > 0
        self.modes[index-1] = name
    def mode(self, index):
        return self.mode[index]
    def modename(self, idx):
        assert idx != 0 # modes are 1-based
        m = self.modes[idx-1]
        if not m:
            if idx == 1:
                return self.name
            else:
                return self.name + " mode " + str(idx)
        return m

DIATONIC = Scale('diatonic', '2212221')
SCALES = {
    'chromatic': Scale('chromatic', '1'*12),
    'wholetone': Scale('wholetone', '2'*6),
    'diatonic': DIATONIC,
    'bebop': Scale('bebop', '2212p121'),
    'pentatonic': Scale('pentatonic', '23223'),
    'blues': Scale('blues', '32p132'),
    'melodic minor': Scale('melodic minor', '2122221'),
    # Scale('harmonic minor', '')
    # Scale('harmonic major', '')
}
# modes and scale aliases
MODES = {
    'ionian': ('diatonic',1),
    'dorian': ('diatonic',2),
    'phyrigian': ('diatonic',3),
    'lydian': ('diatonic',4),
    'mixolydian': ('diatonic',5),
    'aeolian': ('diatonic',6),
    'locrian': ('diatonic',7),
    # 'major scale': ('diatonic',1),
    # 'minor scale': ('diatonic',6),
}
for k,v in MODES.iteritems():
    SCALES[v[0]].addmode(k,v[1])

# for lookup, normalize name first, add root
# number chords can't be used with note numbers
# in the future it might be good to lint chord names in a test
# so that they dont clash with commands and break previous songs if chnaged
CHORDS = {
    # intervals that don't match hord names,
    # using these with numbered notation requires ':'
    "1": "",
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
    "+": "3 #5", # remove until fixed
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
    "mu-7b5": "2 3 b5 7",
    "mu7b5": "2 3 b5 7",
    "wa": "3 4 5", # maj add4
    "wa7": "3 4 5 7", # maj7 add4
    "wa-7": "b3 4 5 7", # m7 add4
    "wa7b5": "3 4 b5 7",
    "wa-7b5": "b3 4 b5 7",
    "majb5": "3 b5", # lydian chord
    "11": "3 5 b7 9 #11",
}
CHORDS_ALT = {
    "r": "1",
    "M2": "2",
    "M3": "3",
    "aug": "+",
    "p4": "4",
    "p5": "5",
    "-": "m",
    "M": "maj",
    "sus4": "sus",
    "major": "maj",
    "ma7": "maj7",
    "ma9": "maj9",
    "Madd9": "majadd9",
    "mdd9": "madd9",
    "major7": "maj7",
    "Mb5": "majb5",
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

# add scales as chords
for sclname, scl in SCALES.iteritems():
    # as with chords, don't list root
    for m in xrange(len(scl.modes)):
        sclnotes = []
        idx = 0
        inter = filter(lambda x:x.isdigit(), scl.intervals)
        if m:
            inter = list(inter[m:]) + list(inter[:m])
        for x in inter:
            sclnotes.append(notename(idx, False))
            try:
                idx += int(x)
            except ValueError:
                idx += 1 # passing tone is 1
                pass
        sclnotes = ' '.join(sclnotes[1:])
        if m==0:
            CHORDS[sclname] = sclnotes
        # print scl.modename(m+1)
        # print sclnotes
        CHORDS[scl.modename(m+1)] = sclnotes

# certain chords parse incorrectly with note letters
BAD_CHORDS = []
for chordlist in (CHORDS, CHORDS_ALT):
    for k in chordlist.keys():
        if k and k[0].lower() in 'abcdefgiv':
            BAD_CHORDS.append(k[1:]) # 'aug' would be 'ug'

# don't parse until checking next char
# AMBIGUOUS_NAMES = {
#     'io': 'n', # i dim vs ionian
#     'do': 'r', # d dim vs dorian
# }

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
DRUM_WORDS = ['drum','drums','drumset','drumkit','percussion']
SPEECH_WORDS = ['speech','say','speak']
GM_LOWER = [""]*len(GM)
for i in xrange(len(GM)): GM_LOWER[i] = GM[i].lower()

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

def note_value(s): # turns dot note values (. and *) into frac
    if not s:
        return (0.0, 0)
    r = 1.0
    dots = count_seq(s)
    s = s[dots:]
    num,ct = peel_float(s, 1.0)
    s = s[ct:]
    if s[0]=='*':
        if dots==1:
            r = num
        else:
            r = num*pow(2.0,float(dots-1))
    elif s[0]=='.':
        num,ct = peel_int_s(s)
        if ct:
            num = int('0.' + num)
        else:
            num = 1.0
        s = s[ct:]
        r = num*pow(0.5,float(dots))
    return (r, dots)

RANGE = 109
OCTAVE_BASE = 5
SCALE = DIATONIC
MODE = 1
TRANSPOSE = 0

MIDI_CC = 0b1011
MIDI_PROGRAM = 0b1100
MIDI_PITCH = 0b1110

class Track:
    def __init__(self, idx, midich, player, schedule):
        self.idx = idx
        # self.players = [player]
        self.player = player
        self.schedule = schedule
        self.channels = [midich]
        self.midich = midich # tracks primary midi channel
        self.initial_channel = midich
        self.non_drum_channel = midich
        self.note_spacing = 1.0
        self.tuplet_count = 0
        self.tuplet_offset = 0.0
        self.reset()
    def reset(self):
        self.notes = [0] * RANGE
        self.sustain_notes = [False] * RANGE
        self.mode = 0 # 0 is NONE which inherits global mode
        self.scale = None
        self.instrument = 0
        self.octave = 0 # rel to OCTAVE_BASE
        self.mod = 0 # dont read in mod, just track its change by this channel
        self.sustain = False # sustain everything?
        self.arp_notes = [] # list of notes to arpegiate
        self.arp_idx = 0
        self.arp_cycle_limit = 0 # cycles remaining, only if limit != 0
        self.arp_pattern = [] # relative steps to
        self.arp_enabled = False
        self.arp_once = False
        self.arp_delay = 0.0
        self.arp_note_spacing = 1.0
        self.vel = 100
        self.non_drum_channel = self.initial_channel
        # self.off_vel = 64
        self.staccato = False
        self.patch_num = 0
        self.transpose = 0
        self.pitch = 0.0
        self.schedule.clear_channel(self)
    # def _lazychannelfunc(self):
    #     # get active channel numbers
    #     return map(filter(lambda x: self.channels & x[0], [(1<<x,x) for x in xrange(16)]), lambda x: x[1])
    def mute(self):
        for ch in self.channels:
            status = (MIDI_CC<<4) + ch
            if SHOWMIDI: print FG.YELLOW + 'MIDI: CC (%s, %s, %s)' % (status,120,0)
            self.player.write_short(status, 120, 0)
    def panic(self):
        for ch in self.channels:
            status = (MIDI_CC<<4) + ch
            if SHOWMIDI: print FG.YELLOW + 'MIDI: CC (%s, %s, %s)' % (status,123,0)
            self.player.write_short(status, 123, 0)
    def note_on(self, n, v=-1, sustain=False):
        if self.sustain:
            sustain = self.sustain
        if v == -1:
            v = self.vel
        if n < 0 or n > RANGE:
            return
        for ch in self.channels:
            self.notes[n] = v
            self.sustain_notes[n] = sustain
            # print "on " + str(n)
            if SHOWMIDI: print FG.YELLOW + 'MIDI: NOTE ON (%s, %s, %s)' % (n,v,ch)
            self.player.note_on(n,v,ch)
    def note_off(self, n, v=-1):
        if v == -1:
            v = self.vel
        if n < 0 or n >= RANGE:
            return
        if self.notes[n]:
            # print "off " + str(n)
            for ch in self.channels:
                if SHOWMIDI: print FG.YELLOW + 'MIDI: NOTE OFF (%s, %s, %s)' % (n,v,ch)
                self.player.note_off(n,v,ch)
                self.notes[n] = 0
                self.sustain_notes[n] = 0
    def release_all(self, mute_sus=False, v=-1):
        if v == -1:
            v = self.vel
        for n in xrange(RANGE):
            # if mute_sus, mute sustained notes too, otherwise ignore
            mutesus_cond = True
            if not mute_sus:
                mutesus_cond =  not self.sustain_notes[n]
            if self.notes[n] and mutesus_cond:
                for ch in self.channels:
                    if SHOWMIDI: print FG.YELLOW + 'MIDI: NOTE OFF (%s, %s, %s)' % (n,v,ch)
                    self.player.note_off(n,v,ch)
                    self.notes[n] = 0
                    self.sustain_notes[n] = 0
                # print "off " + str(n)
        # self.notes = [0] * RANGE
        if self.mod>0:
            self.cc(1,0)
        # self.arp_enabled = False
        self.schedule.clear_channel(self)
    # def cut(self):
    def midi_channel(self, midich, stackidx=-1):
        if midich==DRUM_CHANNEL: # setting to drums
            if self.channels[stackidx] != DRUM_CHANNEL:
                self.non_drum_channel = self.channels[stackidx]
            self.octave = DRUM_OCTAVE
        else:
            for ch in self.channels:
                if ch!=DRUM_CHANNEL:
                    midich = ch
            if midich != DRUMCHANNEL: # no suitable channel in span?
                midich = self.non_drum_channel
        if stackidx == -1: # all
            self.release_all()
            self.channels = [midich]
        elif midich not in self.channels:
            self.channels.append(midich)
    def pitch(self, val): # [-1.0,1.0]
        val = min(max(0,int((1.0 + val)*0x2000)),16384)
        self.pitch = val
        val2 = (val>>0x7f)
        val = val&0x7f
        for ch in self.channels:
            status = (MIDI_PITCH<<4) + self.midich
            if SHOWMIDI: print FG.YELLOW + 'MIDI: PITCH (%s, %s)' % (val,val2)
            self.player.write_short(status,val,val2)
    def cc(self, cc, val): # control change
        status = (MIDI_CC<<4) + self.midich
        # print "MIDI (%s,%s)" % (bin(MIDI_CC),val)
        if SHOWMIDI: print FG.YELLOW + 'MIDI: CC (%s, %s, %s)' % (status, cc,val)
        self.player.write_short(status,cc,val)
        self.mod = val
    def patch(self, p, stackidx=0):
        if isinstance(p,basestring):
            # look up instrument string in GM
            i = 0
            inst = p.replace('_',' ').replace('.',' ')
            
            if p in DRUM_WORDS:
                self.midi_channel(DRUM_CHANNEL)
                p = 0
            else:
                if self.midich == DRUM_CHANNEL:
                    self.midi_channel(self.non_drum_channel)
                
                stop_search = False
                for i in xrange(len(GM_LOWER)):
                    continue_search = False
                    for pword in inst.split(' '):
                        if pword.lower() not in GM_LOWER[i].split(' '):
                            continue_search = True
                            break
                        p = i
                        stop_search=True
                        
                    if stop_search:
                        break
                    if continue_search:
                        assert i < len(GM_LOWER)-1
                        continue

        self.patch_num = p
        # print 'PATCH SET - ' + str(p)
        status = (MIDI_PROGRAM<<4) + self.channels[stackidx]
        if SHOWMIDI: print FG.YELLOW + 'MIDI: PROGRAM (%s, %s)' % (status,p)
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
        self.release_all()
    def arp_next(self):
        assert self.arp_enabled
        note = self.arp_notes[self.arp_idx]
        if self.arp_idx+1 == len(self.arp_notes): # cycle?
            self.arp_once = True
            if self.arp_cycle_limit:
                self.arp_cycle -= 1
                if self.arp_cycle == 0:
                    self.arp_enabled = False
        # increment according to pattern order
        self.arp_idx = (self.arp_idx+self.arp_pattern[self.arp_pattern_idx])%len(self.arp_notes)
        self.arp_pattern_idx = (self.arp_pattern_idx+1) % len(self.arp_pattern)
        self.arp_delay = (self.arp_note_spacing+1.0) % 1.0
        return (note, self.arp_delay)
    def tuplet_next(self):
        delay = 0.0
        if self.tuplet_count:
            delay = self.tuplet_offset
            self.tuplet_offset = (self.tuplet_offset+self.note_spacing) % 1.0
            self.tuplet_count -= 1
        else:
            self.tuplet_offset = 0.0
        if feq(delay,1.0):
            return 0.0
        # print delay
        return delay
    def tuplet_stop(self):
        self.tuplet_count = 0
        self.note_spacing = 1
        self.tuplet_offset = 0.0

class Event:
    def __init__(self, t, func, ch):
        self.t = t
        self.func = func
        self.ch = ch

class Schedule:
    def __init__(self):
        self.events = [] # time,func,ch,skippable
        # store this just in case logic() throws
        # we'll need to reenter knowing this value
        self.passed = 0.0 
        self.clock = 0.0
        self.started = False
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
        
        # clock = time.clock()
        # if self.started:
        #     tdelta = (clock - self.passed)
        #     self.passed += tdelta
        #     self.clock = clock
        # else:
        #     self.started = True
        #     self.clock = clock
        #     self.passed = 0.0
        # print self.clock

        try:
            self.events = sorted(self.events, key=lambda e: e.t)
            for ev in self.events:
                if ev.t > 1.0:
                    ev.t -= 1.0
                else:
                    # sleep until next event
                    if ev.t >= 0.0:
                        time.sleep(t*ev.t)
                        ev.func(0)
                        self.passed = ev.t # only inc if positive
                    else:
                        ev.func(0)
                    
                    processed += 1


            slp = t*(1.0-self.passed) # remaining time
            if slp > 0.0:
                time.sleep(slp)
            self.passed = 0.0
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
        seq = seq[1:]
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

def peel_any(s, match, d=''):
    r = ''
    ct = 0
    for ch in s:
        if ch in match:
            r += ch
            ct += 1
        else:
            break
    return (ct,orr(r,d))

def pauseDC():
    try:
        for ch in TRACKS[:TRACKS_ACTIVE]:
            ch.release_all(True)
        raw_input(' === PAUSED === ')
    except:
        return False
    return True

# class Marker:
#     def __init__(self,name,row):
#         self.name = name
#         self.line = row

TEMPO = 90.0
GRID = 4.0 # Grid subdivisions of a beat (4 = sixteenth note)
SHOWTEXT = True # nice output (-v), only shell and cmd modes by default
SUSTAIN = False # start sustained
NOMUTE = False # nomute=True disables midi muting on program exit

buf = []

class StackFrame:
    def __init__(self, row):
        self.row = row
        self.counter = 0 # repeat call counter

MARKERS = {}
CALLSTACK = [StackFrame(-1)]

# control chars that are definitely not note or chord names
CCHAR = ' <>=~.\'`,_&^|!?*\"#$(){}[]'

SCHEDULE = []
# INIT
SEPARATORS = []
TRACK_HISTORY = ['.'] * NUM_TRACKS

FN = None

row = 0
stoprow = 0
quitflag = False
dcmode = 'n' # n normal c command s sequence
next_arg = 1
# request_tempo = False
# request_grid = False
skip = 0
SCHEDULE = Schedule()
TRACKS = []
mch = 0
SHELL = False
GUI = False

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
                TRACKS[i].patch(int(val))
            else:
                TRACKS[i].patch(val)
    # request_grid = True
    elif arg == '-g':
        GUI = True
        import curses
    elif arg == '-v':
        SHOWTEXT = True
    elif arg == '-l':
        dcmode = 'l'
    elif arg == '-c':
        dcmode = 'c'
    elif arg == '-sh':
        SHELL = True
    elif arg == '--nomute':
        NOMUTE = True
    elif arg == '--sustain':
        SUSTAIN = True
    elif arg == '--sharps':
        FLATS = False
    elif arg == '--flats':
        FLATS = True
    elif arg == '--numbers':
        NOTENAMES = False
    elif arg == '--notenames':
        NOTENAMES = True
    else:
        next_arg = i
        break
    next_arg = i+1

if dcmode=='l':
    buf = ' '.join(sys.argv[next_arg:]).split(';') # ;
elif dcmode=='c':
    buf = ' '.join(sys.argv[next_arg:]).split(' ') # spaces
else: # mode n
    if len(sys.argv)>=2:
        FN = sys.argv[-1]
        with open(FN) as f:
            for line in f.readlines():
                lc = 0
                if line:
                    if line[-1] == '\n':
                        line = line[:-1]
                    elif len(line)>2 and line[-2:0] == '\r\n':
                        line = line[:-2]
                    
                    # if not line:
                    #     lc += 1
                    #     continue
                    ls = line.strip()
                    
                    # place marker
                    if ls and ls[0]==':':
                        bm = ls[1:]
                        # only store INITIAL marker positions
                        if not bm in MARKERS:
                            MARKERS[bm] = lc
                lc += 1
                buf += [line]
    else:
        if dcmode == 'n':
            dcmode = ''
        SHELL = True

midi.init()
dev = 0
portname = None
for i in xrange(midi.get_count()):
    port = pygame.midi.get_device_info(i)
    portname = port[1]
    # print port
    # timidity
    if portname.lower()=='timidity port 0':
        dev = i
    # qsynth
    elif portname.lower().startswith('synth input port'):
        dev = i
    # helm will autoconnect

# PLAYER = pygame.midi.Output(pygame.midi.get_default_output_id())
PLAYER = pygame.midi.Output(dev)
INSTRUMENT = 0
PLAYER.set_instrument(0)
for i in xrange(NUM_CHANNELS_PER_DEVICE):
    # print "%s -> %s" % (i,mch)
    TRACKS.append(Track(i, mch, PLAYER, SCHEDULE))
    mch += 2 if i==DRUM_CHANNEL else 1

if SUSTAIN:
    TRACKS[0].sustain = SUSTAIN

# show nice output in certain modes
if SHELL or dcmode in 'cl':
    SHOWTEXT = True

for i in xrange(len(sys.argv)):
    arg = sys.argv[i]
    
    # play range (+ param, comma-separated start and end)
    if arg.startswith('+'):
        vals = arg[1:].split(',')
        try:
            row = int(vals[0])
        except ValueError:
            try:
                row = MARKERS[vals[0]]
            except KeyError:
                print 'invalid entry point'
                quitflag = True
        try:
            stoprow = int(vals[1])
        except ValueError:
            try:
                # we cannot cut buf now, since seq might be non-linear
                stoprow = MARKERS[vals[0]]
            except KeyError:
                print 'invalid stop point'
                quitflag = True
        except IndexError:
            pass # no stop param

if SHELL:
    print FG.BLUE + 'decadence v'+str(VERSION)
    print 'Copyright (c) 2018 Grady O\'Connell'
    print 'https://github.com/flipcoder/decadence'
    if portname:
        print FG.GREEN + 'Device: ' + FG.WHITE + '%s' % (portname if portname else 'Unknown',)
        if TRACKS[0].midich == DRUM_CHANNEL:
            print FG.GREEN + 'GM Percussion'
        else:
            print FG.GREEN + 'GM Patch: '+ FG.WHITE +'%s' % GM[TRACKS[0].patch_num]
    print ''
    print 'Read the manual and look at examples. Have fun!'

header = True # set this to false as we reached cell data
while not quitflag:
    try:
        line = '.'
        try:
            line = buf[row]
            if stoprow and row == stoprow:
                buf = []
                raise IndexError
        except IndexError:
            row = len(buf)
            # done with file, finish playing some stuff
            
            arps_remaining = 0
            if SHELL or dcmode in ['c','l']: # finish arps in shell mode
                for ch in TRACKS[:TRACKS_ACTIVE]:
                    if ch.arp_enabled:
                        if ch.arp_cycle_limit or not ch.arp_once:
                            arps_remaining += 1
                            line = '.'
                if not arps_remaining and not SHELL and dcmode not in ['c','l']:
                    break
                line = '.'
            
            if not arps_remaining and not SCHEDULE.pending():
                if SHELL:
                    for ch in TRACKS[:TRACKS_ACTIVE]:
                        ch.release_all()
                    
                    # SHELL PROMPT
                    # print orr(TRACKS[0].scale,SCALE).modename(orr(TRACKS[0].mode,MODE))
                    cur_oct = TRACKS[0].octave
                    prompt = FG.GREEN + 'DC> '+FG.BLUE +\
                        '('+str(int(TEMPO))+'bpm x'+str(int(GRID))+' '+\
                        notename(TRACKS[0].transpose) + ' ' +\
                        orr(TRACKS[0].scale,SCALE).modename(orr(TRACKS[0].mode,MODE,-1))+\
                        ')> '
                    bufline = raw_input(prompt)
                    # if bufline.endswith('.dc'):
                        # play file?
                    buf += filter(None, bufline.split(' '))
                    continue
                
                else:
                    break
            
        print FG.MAGENTA + line
        
        # cells = line.split(' '*2)
        
        # if line.startswith('|'):
        #     SEPARATORS = [] # clear
        #     # column setup!
        #     for i in xrange(1,len(line)):
        #         if line[i]=='|':
        #             SEPARATORS.append(i)
        
        # print BG.RED + line
        fullline = line[:]
        line = line.strip()
        
        # LINE COMMANDS
        ctrl = False
        cells = []

        if line:
            # COMMENTS (;)
            if line[0] == ';':
                row += 1
                continue
            
            # set marker
            if line[-1]==':': # suffix marker
                # allow override of markers in case of reuse
                MARKERS[line[:-1]] = row
                row += 1
                continue
                # continue
            elif line[0]==':': #prefix marker
                # allow override of markers in case of reuse
                MARKERS[line[1:]] = row
                row += 1
                continue
            
            # TODO: global 'silent' commands (doesn't take time)
            if line.startswith('%'):
                line = line[1:].strip() # remove % and spaces
                for tok in line.split(' '):
                    var = tok[0].upper()
                    if var in 'TGNPSRM':
                        cmd = tok.split(' ')[0]
                        op = cmd[1]
                        try:
                            val = cmd[2:]
                        except:
                            val = ''
                        # print "op val %s %s" % (op,val)
                        if not op in '*/=-+':
                            # implicit =
                            val = str(op) + str(val)
                            op='='
                        if not val or op=='.':
                            val = op + val # append
                            # TODO: add numbers after dots like other ops
                            if val[0]=='.':
                                note_value(val)
                                ct = count_seq(val)
                                val = pow(0.5,count)
                                op = '/'
                                num,ct = peel_uint(val[:ct])
                            elif val[0]=='*':
                                op = '*'
                                val = pow(2.0,count_seq(val))
                        if op=='/':
                            if var=='G': GRID/=float(val)
                            elif var=='N': GRID/=float(val) #!
                            elif var=='T': TEMPO/=float(val)
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
                                    p = vals[i]
                                    if p.strip().isdigit():
                                        TRACKS[i].patch(int(p))
                                    else:
                                        TRACKS[i].patch(p)
                            elif var=='R' or var=='S':
                                if val:
                                    val = val.lower()
                                    # ambigous alts
                                    
                                    if val.isdigit():
                                        modescale = (SCALE.name,int(val))
                                    else:
                                        alts = {'major':'ionian','minor':'aeolian'}
                                        try:
                                            modescale = (alts[modescale[0]],modescale[1])
                                        except:
                                            pass
                                        val = val.lower()
                                        modescale = MODES[val]
                                    
                                    try:
                                        SCALE = SCALES[modescale[0]]
                                        MODE = modescale[1]
                                        inter = SCALE.intervals
                                        TRANSPOSE = 0
                                        
                                        print MODE-1
                                        if var=='R':
                                            for i in xrange(MODE-1):
                                                inc = 0
                                                try:
                                                    inc = int(inter[i])
                                                except ValueError:
                                                    pass
                                                TRANSPOSE += inc
                                    except ValueError:
                                        print 'no such scale'
                                        assert False
                                else:
                                    TRANSPOSE = 0
                                    
                row += 1
                continue
            
            # jumps
            if line[0]=='@':
                if len(line)<=1:
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
            
        
        # this is not indented in blank lines because even blank lines have this logic
        if SHELL:
            cells = filter(None,line.split(' '))
        elif not SEPARATORS:
            # AUTOGENERATE CELL SEPARATORS
            cells = fullline.split(' ')
            pos = 0
            for cell in cells:
                if cell:
                    if pos:
                        SEPARATORS.append(pos)
                    # print cell
                pos += len(cell) + 1
            # print  "SEPARATORS " + str(SEPARATORS)
            cells = filter(None,cells)
            # if fullline.startswith(' '):
            #     cells = ['.'] + cells # dont filter first one
            autoseparate = True
        else:
            # SPLIT BASED ON SEPARATORS
            s = 0
            seplen = len(SEPARATORS)
            # print seplen
            pos = 0
            for i in xrange(seplen):
                cells.append(fullline[pos:SEPARATORS[i]].strip())
                pos = SEPARATORS[i]
            lastcell = fullline[pos:].strip()
            if lastcell: cells.append(lastcell)
        
        # make sure active tracks get empty cell
        len_cells = len(cells)
        if len_cells > TRACKS_ACTIVE:
            TRACKS_ACTIVE = len_cells
        else:
            # add empty cells for active tracks to the right
            cells += ['.'] * (len_cells - TRACKS_ACTIVE)
        del len_cells
        
        cell_idx = 0
        
        # CELL LOGIC
        for cell in cells:
            
            cell = cells[cell_idx]
            ch = TRACKS[cell_idx]
            fullcell = cell[:]
            ignore = False
            
            # if INSTRUMENT != ch.instrument:
            #     PLAYER.set_instrument(ch.instrument)
            #     INSTRUMENT = ch.instrument

            cell = cell.strip()
            if cell:
                header = False
            
            if cell.count('\"') == 1: # " is recall, but multiple " means speak
                cell = cell.replace("\"", TRACK_HISTORY[cell_idx])
            else:
                TRACK_HISTORY[cell_idx] = cell
            
            fullcell_sub = cell[:]
            
            # empty
            # if not cell:
            #     cell_idx += 1
            #     continue

            if cell and cell[0]=='-':
                if SHELL:
                    ch.mute()
                else:
                    ch.release_all() # don't mute sustain
                cell_idx += 1
                continue
            
            if cell and cell[0]=='=': # hard mute
                ch.mute()
                cell_idx += 1
                continue

            if cell and cell[0]=='-': # mute prefix
                ch.release_all(True)
                # ch.sustain = False
                cell = cell[1:]
            
            notecount = len(ch.scale.intervals if ch.scale else SCALE.intervals)
            # octave = int(cell[0]) / notecount
            c = cell[0] if cell else ''
            
            # PROCESS NOTE
            chord_notes = [] # notes to process from chord
            notes = [] # outgoing notes to midi
            slashnotes = [[]] # using slashchords, to join this into notes [] above
            allnotes = [] # same, but includes all scheduled notes
            accidentals = False
            # loop = True
            noteloop = True
            expanded = False # inside chord? if so, don't advance cell itr
            events = []
            inversion = 1 # chord inversion
            flip_inversion = False
            inverted = 0 # notes pending inversion
            chord_root = 1
            chord_note_count = 0 # include root
            chord_note_index = -1
            octave = ch.octave
            strum = 0.0
            noteletter = '' # track this just in case (can include I and V)
            chordname = ''
            
            cell_before_slash=cell[:]
            sz_before_slash=len(cell)
            slash = cell.split('/') # slash chords
            tok = slash[0]
            cell = slash[0][:]
            slashidx = 0
            addbottom = False # add note at bottom instead
            
            while True:
                n = 1
                roman = 0 # -1 lower, 0 none, 1 upper, 
                accidentals = ''
                # number_notes = False
                
                # if not chord_notes: # processing cell note
                #     pass
                # else: # looping notes of a chord?
                
                if tok and not tok=='.':
                
                    # sharps/flats before note number/name
                    c = tok[0]
                    if c=='b' or c=='#':
                        if len(tok) > 2 and tok[0:2] =='bb':
                            accidentals = 'bb'
                            n -= 2
                            tok = tok[2:]
                            if not expanded: cell = cell[2:]
                        elif c =='b':
                            accidentals = 'b'
                            n -= 1
                            tok = tok[1:]
                            if not expanded: cell = cell[1:]
                        elif len(tok) > 2 and tok[0:2] =='##':
                            accidentals = '##'
                            n += 2
                            tok = tok[2:]
                            if not expanded: cell = cell[2:]
                        elif c =='#':
                            accidentals = '#'
                            n += 1
                            tok = tok[1:]
                            if not expanded: cell = cell[1:]

                    # try to get roman numberal or number
                    c,ct = peel_roman_s(tok)
                    ambiguous = 0
                    ambiguous += tok.lower().startswith('ion')
                    ambiguous += tok.lower().startswith('dor')
                    if ct and not ambiguous:
                        lower = (c.lower()==c)
                        c = ['','i','ii','iii','iv','v','vi','vii','viii','ix','x','xi','xii'].index(c.lower())
                        noteletter = notename(c-1,NOTENAMES,FLATS)
                        roman = -1 if lower else 1
                    else:
                        # use normal numbered note
                        num,ct = peel_int(tok)
                        c = num
                    
                    # couldn't get it, set c back to char
                    if not ct:
                        c = tok[0] if tok else ''
                    
                    if c=='.':
                        tok = tok[1:]
                        cell = cell[1:]

                    # tok2l = tok.lower()
                    # if tok2l in SOLEGE_NOTES or tok2l.startswith('sol'):
                    #     # SOLFEGE_NOTES = 
                    #     pass
                        
                    # note numbers, roman, numerals or solege
                    lt = len(tok)
                    if ct:
                        c = int(c)
                        if c == 0:
                            ignore = True
                            break
                        #     n = 1
                        #     break
                        # numbered notation
                        # wrap notes into 1-7 range before scale lookup
                        wrap = ((c-1) / notecount)
                        note = ((c-1) % notecount)+1
                        # print 'note ' + str(note)
                        
                        for i in xrange(1,note):
                            # dont use scale for expanded chord notes
                            if expanded:
                                try:
                                    n += int(DIATONIC.intervals[i-1])
                                except ValueError:
                                    n += 1 # passing tone
                            else:
                                m = orr(ch.mode,MODE,-1)-1
                                steps = orr(ch.scale,SCALE).intervals
                                idx = steps[(i-1 + m) % notecount]
                                n += int(idx)
                        if inverted: # inverted counter
                            if flip_inversion:
                                # print (chord_note_count-1)-inverted
                                inverted -= 1
                            else:
                                # print 'inversion?'
                                # print n
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
                        # print '---'
                        # print n
                        # print 'n slash %s,%s' %(n,slashidx)
                        n += 12 * (wrap - slashidx)
                        
                        # print tok
                        tok = tok[ct:]
                        # print tok
                        if not expanded: cell = cell[ct:]
                        
                        # number_notes = not roman
                        
                        if tok and tok[0]==':':
                            tok = tok[1:] # allow chord sep
                            if not expanded: cell = cell[1:]
                        
                        # print 'note: %s' % n
                
                    # NOTE LETTERS
                    elif c.upper() in '#ABCDEFG' and not ambiguous:
                        
                        n = 0
                        # flats, sharps after note names?
                        # if tok:
                        if lt >= 3 and tok[1:3] =='bb':
                            accidentals = 'bb'
                            n -= 2
                            tok = tok[0] + tok[3:]
                            cell = cell[0:1] + cell[3:]
                        elif lt >= 2 and tok[1] == 'b':
                            accidentals = 'b'
                            n -= 1
                            tok = tok[0] + tok[2:]
                            if not expanded: cell = cell[0] + cell[2:]
                        elif lt >= 3 and tok[1:3] =='##':
                            accidentals = '##'
                            n += 2
                            tok = tok[0] + tok[3:]
                            cell = cell[0:1] + cell[3:]
                        elif lt >= 2 and tok[1] =='#':
                            accidentals = '#'
                            n += 1
                            tok = tok[0] + tok[2:]
                            if not expanded: cell = cell[0] + cell[2:]
                        # print n
                        # accidentals = True # dont need this
                    
                        if not tok:
                            c = 'b' # b note was falsely interpreted as flat
                        
                        # note names, don't use these in chord defn
                        try:
                            # dont allow lower case, since 'b' means flat
                            note = ' CDEFGAB'.index(c.upper())
                            noteletter = str(c)
                            for i in xrange(note):
                                n += int(DIATONIC.intervals[i-1])
                            n -= slashidx*12
                            # adjust B(7) and A(6) below C, based on accidentials
                            nn = (n-1)%12+1 # n normalized
                            # print 'note ' + str(nn)
                            # print nn
                            if (8<=nn<=9 and accidentals.startswith('b')): # Ab or Abb
                                n -= 12
                            elif nn == 10 and not accidentals:
                                n -= 12
                            elif nn > 10:
                                n -= 12
                            # print (n-1) % 12 + 1
                            tok = tok[1:]
                            if not expanded: cell = cell[1:]
                        except ValueError:
                            ignore = True
                    else:
                        ignore = True # reenable if there's a chord listed
                    
                    # CHORDS
                    is_chord = False
                    if not expanded:
                        if tok or roman:
                            # print tok
                            cut = 0
                            nonotes = []
                            chordname = ''
                            
                            # cut chord name from text after it
                            for char in tok:
                                if char not in CCHAR:
                                    chordname += char
                                    try:
                                        # TODO: addchords
                                        
                                        # TODO note removal (Maj7no5)
                                        if chordname[-2:]=='no':
                                            numberpart = tok[cut+1:]
                                            # second check will throws
                                            if numberpart in '#b' or (int(numberpart) or True):
                                                # if tok[]
                                                print 'no'
                                                prefix,ct = peel_any(tok[cut:],'#b')
                                                if ct: cut += ct
                                                
                                                num,ct = peel_uint(tok[cut+1:])
                                                if ct:
                                                    cut += ct
                                                    cut -= 2 # remove "no"
                                                    chordname = chordname[:-2] # cut "no
                                                    nonotes.append(str(prefix)+str(num)) # ex: b5
                                                    print "chord name " + chordname
                                                    break
                                    except IndexError:
                                        print 'chordname length ' + str(len(chordname))
                                        pass # chordname length
                                    except ValueError:
                                        print 'bad cast ' + char
                                        pass # bad int(char)
                                    cut += 1
                                else:
                                    # found control char, we're donde
                                    break
                                # else:
                                    # try:
                                    #     if tok[cut+1]==AMBIGUOUS_CHORDS[chordname]:
                                    #         continue # read ahead to disambiguate
                                    # except:
                                    #     break
                                
                            # try:
                            #     # number chords w/o note letters aren't chords
                            #     if int(chordname) and not noteletter:
                            #         chordname = '' # reject
                            # except:
                            #     pass
                            
                            # print chordname
                            # don't include tuplet in chordname
                            if chordname.endswith('t'):
                                chordname = chordname[:-1]
                                cut -= 1
                            
                            # print chordname
                            if roman: # roman chordnames are sometimes empty
                                # print chordname
                                if chordname and not chordname[1:] in 'bcdef':
                                    if roman == -1: # minor
                                        if chordname[0] in '6719':
                                            chordname = 'm' + chordname
                                else:
                                    # print chordname
                                    chordname = 'maj' if roman>0 else 'm' + chordname
                            
                            if chordname:
                                # print chordname
                                if chordname in BAD_CHORDS:
                                    # certain chords may parse wrong w/ note letters
                                    # example: aug, in this case, 'ug' is the bad chord name
                                    chordname = noteletter + chordname # fix it
                                    n -= 1 # fix chord letter

                                try:
                                    inv_letter = ' abcdef'.index(chordname[-1])
                                
                                    # num,ct = peel_int(tok[cut+1:])
                                    # if ct and num!=0:
                                    # cut += ct + 1
                                    if inv_letter>=1:
                                        inversion = max(1,inv_letter)
                                        inverted = max(0,inversion-1) # keep count of pending notes to invert
                                        # cut+=1
                                        chordname = chordname[:-1]
                                        
                                except ValueError:
                                    pass
                                
                                try:
                                    chord_notes = expand_chord(chordname)
                                    chord_notes = filter(lambda x: x not in nonotes, chord_notes)
                                    # print chord_notes
                                    chord_note_count = len(chord_notes)+1 # + 1 for root
                                    expanded = True
                                    tok = ""
                                    cell = cell[cut:]
                                    # print cell
                                    # print tok
                                    is_chord = True
                                except KeyError, e:
                                    # may have grabbed a ctrl char, pop one
                                    if len(chord_notes)>1: # can pop?
                                        try:
                                            chord_notes = expand_chord(chordname[:-1])
                                            chord_notes = filter(lambda x,nonotes=nonotes: x in nonotes)
                                            # print chordnames
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
                                        # noteloop = True
                                        # assert False
                                        # invalid chord
                                        print FG.RED + 'Invalid Chord: ' + chordname
                                        break
                            
                            if is_chord:
                                # assert not accidentals # accidentals with no note name?
                                slashnotes[0].append(n + chord_root-1)
                                chord_root = n
                                ignore = False # reenable default root if chord was w/o note name
                                continue
                            else:
                                # print 'not chord, treat as note'
                                pass
                            #     assert False # not a chord, treat as note
                            #     break
                        else: # blank chord name
                            # print 'blank chord name'
                            # expanded = False
                            pass
                    else: # not tok and not expanded
                        # print 'not tok and not expanded'
                        pass
                # else and not chord_notes:
                #     # last note in chord, we're done
                #     tok = ""
                #     noteloop = False
                    
                    slashnotes[0].append(n + chord_root-1)
                
                # if not tok and not expanded:
                #     break
                
                # tok may be blank here if slash is
                # else:
                #     print slash
                #     if not slash:
                #         break
                # if not tok:
                #     print slash
                #     if not slash:
                #         break
                
                if expanded:
                    if not chord_notes:
                        # next chord
                        # print cell
                        expanded = False
                
                if chord_notes:
                    # print 'chord_notes'
                    tok = chord_notes[0]
                    # print 'tok'+ str(tok)
                    chord_notes = chord_notes[1:]
                    chord_note_index += 1
                    # fix negative inversions
                    if inversion < 0: # not yet working
                        # print inversion
                        # print chord_note_count
                        # octave += inversion/chord_note_count
                        inversion = inversion%chord_note_count
                        inverted = -inverted
                        flip_inversion = True
                        
                if not expanded:
                    # print 'not expanded'
                    inversion = 1 # chord inversion
                    flip_inversion = False
                    inverted = 0 # notes pending inversion
                    chord_root = 1
                    chord_note_count = 0 # include root
                    chord_note_index = -1
                    chord_note_index = -1
                    # next slash chord part
                    # print slash
                    flip_inversion = False
                    inversion = 1
                    # print 'nextslash'
                    chord_notes = []
                    slash = slash[1:]
                    if slash:
                        tok = slash[0]
                        cell = slash[0]
                        slashnotes = [] + slashnotes
                    else:
                        break
                    slashidx += 1
                # if expanded and not chord_notes:
                #     break

            notes = [i for o in slashnotes for i in o] # combine slashnotes
            # print notes
            # print sz_before_slash
            # print len(cell)
            cell = cell_before_slash[sz_before_slash-len(cell):]
            # print len(cell)

            if ignore:
                allnotes = []
                notes = []

            # save the intended notes since since scheduling may drop some
            # during control phase
            allnotes = notes 
            
            tuplets = False

            # TODO: arp doesn't work if channel not visible/present, move this
            if ch.arp_enabled:
                if notes: # incoming notes?
                    # print notes
                    # interupt arp
                    ch.arp_stop()
                else:
                    # continue arp
                    arpnext = ch.arp_next()
                    notes = [arpnext[0]]
                    delay = arpnext[1]
                    if not fzero(delay):
                        ignore = False
                    #   schedule=True

            # if notes:
            #     print notes
            
            cell = cell.strip() # ignore spaces

            vel = ch.vel
            mute = False
            sustain = False
           
            delay = 0.0
            showtext = []
            arpnotes = False
            duration = 0.0

            # if cell and cell[0]=='|':
            #     if not expanded: cell = cell[1:]

            # print cell

            # ESPEAK / FESTIVAL support wip
            # if cell.startswith('\"') and cell.count('\"')==2:
            #     quote = cell.find('\"',1)
            #     word =  cell[1:quote]
            #     BGPIPE.send((BGCMD.SAY,str(word)))
            #     cell = cell[quote+1:]
            #     ignore = True
             
            notevalue = ''
            while len(cell) >= 1: # recompute len before check
                after = [] # after events
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


                tuplets = False

                # OCTAVE SHIFT UP
                    # if sym== '>': ch.octave = octave # persist
                    # row_events += 1
                # elif c == '-':
                #     c = cell[1]
                #     shift = int(c) if c.isdigit() else 0
                #     p = base + (octave+shift) * 12
                # INVERSION
                if c == '>' or c=='<':
                    sign = (1 if c=='>' else -1)
                    ct = count_seq(cell)
                    for i in xrange(ct):
                        notes[i] += 12*sign
                    notes = notes[sign*1:] + notes[:1*sign]
                    # when used w/o note/chord, track history should update
                    # TRACK_HISTORY[cell_idx] = fullcell_sub
                    # print notes
                    if ch.arp_enabled:
                        ch.arp_notes = ch.arp_notes[1:] + ch.arp_notes[:1]
                    cell = cell[1+ct:]
                elif c == ',' or c=='\'':
                    cell = cell[1:]
                    sign = 1 if c=='\'' else -1
                    if cell and cell[0].isdigit(): # numbers persist
                        shift,ct = peel_int(cell,1)
                        cell = cell[ct:]
                        octave += sign*shift
                        ch.octave = octave # persist
                    else:
                        rpt = count_seq(cell,',')
                        octave += sign*(rpt+1) # persist
                        cell = cell[rpt:]
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
                    # row_events += 1
                # VIBRATO
                elif c == '~': # vibrato -- eventually using pitch wheel
                    ch.cc(1,127)
                    cell = cell[1:]
                    # row_events += 1d
                # HOLD
                elif c2=='__': # persist sustain (pedal)
                    sustain = True # use sustain flag in note on func
                    cell = cell[2:]
                    # assert notes # sustaining w/o note?
                elif c2=='-_': # persist sustain (pedal)
                    sustain = False
                    cell = cell[2:]
                elif c=='_':
                    ch.sustain = True # persist
                    cell = cell[1:]
                    # assert notes # sustaining w/o note?
                elif c=='v': # volume
                    # mult g* or g/
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
                # extend range up another octave (this will be moved upward to work in slash chords)
                elif c=='^':
                    cell = cell[1:]
                    minnote = min(notes)
                    maxnote = max(notes)
                    span = (maxnote-minnote)/12 + 1
                    onotes = []
                    for o in xrange(1,count):
                        onotes += map(lambda n=n,o=o,span=span: n+o*span*12, notes)
                    notes = notes + onotes
                elif c2=='ch': # midi channel
                    num,ct = peel_uint(cell[2:])
                    cell = cell[2+ct:]
                    ch.midi_channel(num)
                    if SHOWTEXT:
                        showtext.append('channel')
                elif c=='*':
                    dots = count_seq(cell)
                    if notes:
                        cell = cell[dots:]
                        num,ct = peel_float(cell, 1.0)
                        cell = cell[ct:]
                        if dots==1:
                            duration = num
                            events.append(Event(num, lambda _: ch.release_all(), ch))
                        else:
                            duration = num*pow(2.0,float(dots-1))
                            events.append(Event(num*pow(2.0,float(dots-1)), lambda _: ch.release_all(), ch))
                    else:
                        cell = cell[dots:]
                    if SHOWTEXT:
                        showtext.append('duration(*)')
                elif c=='.':
                    dots = count_seq(cell)
                    if len(c)>1 and notes:
                        notevalue = '.' * dots
                        cell = cell[dots:]
                        if ch.arp_enabled:
                            dots -= 1
                        if dots:
                            num,ct = peel_int_s(cell)
                            if ct:
                                num = int('0.' + num)
                            else:
                                num = 1.0
                            cell = cell[ct:]
                            duration = num*pow(0.5,float(dots))
                            events.append(Event(num*pow(0.5,float(dots)), lambda _: ch.release_all(), ch))
                    else:
                        cell = cell[dots:]
                    if SHOWTEXT:
                        showtext.append('shorten(.)')
                elif c==')': # note delay
                    num = ''
                    cell = cell[1:]
                    s,ct = peel_uint(cell, 5)
                    if ct:
                        cell = cell[ct:]
                    delay = float('0.'+num) if num else 0.5
                    if SHOWTEXT:
                        showtext.append('delay(.)')
                elif c=='|':
                    cell = cell[1:] # ignore
                elif c2=='!!': # loud accent
                    vel,ct = peel_uint_s(cell[1:],127)
                    cell = cell[2+ct:]
                    if ct>2: ch.vel = vel # persist if numbered
                    if SHOWTEXT:
                        showtext.append('accent(!!)')
                elif c=='!': # accent
                    curv = ch.vel
                    num,ct = peel_uint_s(cell[1:])
                    if ct:
                        vel = min(127,int(float('0.'+num)*127.0))
                    else:
                        vel = min(127,int(curv + 0.5*(127.0-curv)))
                    cell = cell[ct+1:]
                    if SHOWTEXT:
                        showtext.append('accent(!!)')
                elif c2=='??': # very quiet
                    vel = max(0,int(ch.vel-0.25*(127-ch.vel)))
                    cell = cell[2:]
                    if SHOWTEXT:
                        showtext.append('soften(??)')
                elif c=='?': # quiet
                    vel = max(0,int(ch.vel-0.5*(127-ch.vel)))
                    cell = cell[1:]
                    if SHOWTEXT:
                        showtext.append('soften(??)')
                elif c=='$': # strum
                    sq = count_seq(cell)
                    cell = cell[sq:]
                    strum = -1.0 if sq==2 else 1.0
                    sustain = False
                    # print 'strum'
                    if SHOWTEXT:
                        showtext.append('strum($)')
                elif c=='&':
                    count = count_seq(cell)
                    num,ct = peel_uint(cell[count:],0)
                    cell = cell[ct+count:]
                    if not notes:
                        # & restarts arp (if no note)
                        ch.arp_enabled = True
                        ch.arp_idx = 0
                    else:
                        arpnotes = True
                    if SHOWTEXT:
                        showtext.append('arpeggio(&)')
                elif c=='\\': # bend
                    num,ct = peel_int_s(cell[1:])
                    if ct:
                        sign = 1
                        if num<0: 
                            num=num[1:]
                            sign = -1
                        vel = min(127,sign*int(float('0.'+num)*127.0))
                    else:
                        vel = min(127,int(curv + 0.5*(127.0-curv)))
                    cell = cell[ct+1:]
                    ch.pitch(vel)
                    pass
                elif c=='t': # tuplet
                    # each t increases prime number
                    # times note attacks to be tuplet ratio
                    # tup, ct = count_seq(cell)
                    # self.tuplet_offset = 1.0 / tup
                    tuplets = True
                    ch.tuplet_count = 3 # nested tuplet might throw this off, might need stack
                    pow2i = 0.0
                    for i in itertools.count():
                        pow2i = pow(2.0,i)
                        if pow2i > 3:
                            break
                    ch.note_spacing = pow2i/3.0
                    cell = cell[1+ct:]
                    if SHOWTEXT:
                        showtext.append('tuplet(t)')
                elif c=='@':
                    if not notes:
                        cell = []
                        continue # ignore jump
                # elif c==':':
                #     if not notes:
                #         cell = []
                #         continue # ignore marker
                else:
                    if dcmode in 'cl':
                        print FG.BLUE + line
                    indent = ' ' * (len(fullcell)-len(cell))
                    print FG.RED + indent +  "^ Unexpected " + cell[0] + " here"
                    cell = []
                    ignore = True
                    break
                
                # elif c=='/': # bend in
                # elif c=='\\': # bend down
            
            base =  (OCTAVE_BASE+octave) * 12 - 1 + TRANSPOSE + ch.transpose
            p = base
            
            if arpnotes:
                ch.arp(notes, num)
                arpnext = ch.arp_next()
                notes = [arpnext[0]]
                delay = arpnext[1]
                # if not fcmp(delay):
                #     pass
                    # schedule=True

            if notes or mute:
                ch.release_all()

            for ev in events:
                SCHEDULE.add(ev)
            
            delta = 0 # how much to separate notes
            if strum < -EPSILON:
                notes = notes[::-1] # reverse
                strum -= strum
            if strum > EPSILON:
                delta = strum/(len(notes))*(forr(duration,1.0)) #t between notes

            if SHOWTEXT:
                pass
                # print FG.MAGENTA + ', '.join(map(lambda n: notename(p+n), notes))
                # chordoutput = chordname
                # if chordoutput and noletter:
                #     coordoutput = notename(chord_root+base) + chordoutput
                # print FG.CYAN + chordoutput + " ("+ \
                #     (', '.join(map(lambda n,base=base: notename(base+n),notes)))+")"
                # print showtext
                # showtext = []
                # if chordname and not ignore:
                #     noteletter = notename(n+base)
                #     print FG.CYAN + noteletter + chordname+ " ("+ \
                #         (', '.join(map(lambda n,base=base: notename(base+n),allnotes)))+")"

            if tuplets:
                delay += ch.tuplet_next()
            else:
                ch.tuplet_stop()
            
            i = 0
            for n in notes:
                # if no schedule, play note immediately
                # also if scheduled, play first note of strum if there's no delay
                if fzero(delay):
                # if not schedule or (i==0 and strum>=EPSILON and delay<EPSILON):
                    ch.note_on(p + n, vel, sustain)
                    delay += delta
                else:
                    f = lambda _,ch=ch,p=p,n=n,vel=vel,sustain=sustain: ch.note_on(p + n, vel, sustain)
                    delay += delta
                    SCHEDULE.add(Event(delay,f,ch))
                i += 1
            
            cell_idx += 1

        while True:
            try:
                if not ctrl and not header:
                    SCHEDULE.logic(60.0 / TEMPO / GRID)
                    break
                else:
                    break
            except KeyboardInterrupt:
                # print FG.RED + traceback.format_exc()
                quitflag = True
                break
            except:
                print FG.RED + traceback.format_exc()
                if not SHELL and not pauseDC():
                    quitflag = True
                    break

        if quitflag:
            break
        
        row += 1
    
    except KeyboardInterrupt:
        # print FG.RED + traceback.format_exc()
        break
    except:
        print FG.RED + traceback.format_exc()
        if not SHELL and not pauseDC():
            break

# TODO: turn all midi note off
i = 0
for ch in TRACKS:
    if not NOMUTE:
        ch.panic()
    ch.player = None

del PLAYER
midi.quit()

# def main():
#     pass
    
# if __name__=='__main__':
#     curses.wrapper(main)

if BCPROC:
    BGPIPE.send((BGCMD.QUIT,))
    BGPROC.join()

