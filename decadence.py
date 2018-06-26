#!/usr/bin/env python3
"""decadence
Copyright (c) 2018 Grady O'Connell
Open-source under MIT License

Examples:
    decadence.py          shell
    decadence.py song.dc  play song

Usage:
    decadence.py [--follow] [--csound] [--sonic-pi] [-eftnpsrx] [SONGNAME]
    decadence.py [+RANGE] [--follow] [-eftnpsrx] [SONGNAME]
    decadence.py -c [COMMANDS ...]
    decadence.py -l [LINE_CONTENT ...]
    decadence.py  [SONGNAME]

Options:
    -h --help             show this
    -v --verbose          verbose
    -t --tempo=<bpm>      set tempo
    -x --grid=<grid>      set grid
    -n --note=<note>      set grid using note value
    -s --speed=<speed>    (STUB) playback speed
    --dev=<device>        output device, partial match
    -p --patch=<patch>    default midi patch, partial match
    -c                    execute commands sequentially
    -l                    execute commands simultaenously
    -r --remote           (STUB) remote, keep alive as daemon
    --nomute              don't mute midi on end
    +<range>              play from line or maker, for range use start:end
    -e --edit             (STUB) open file in editor
    --vi                  (STUB) shell vi mode
    -T --transpose        (STUB) transpose (in half steps)
    --sustain             sustain by default
    --numbers             use note numbers in output
    --notenames           use note names in output
    --flats               prefer flats in output
    --sharps              prefer sharps in output
    --lint                analyze file
    --follow              (old) print newlines every line, no output
    --quiet               no output
    --csound              (STUB) enable csound
    --sonic-pi            (STUB) enable sonic-pi
"""
from __future__ import unicode_literals, print_function, generators
import os, sys, time, random, itertools, signal, tempfile, traceback, socket
from builtins import range, str
from future.utils import iteritems
import time, subprocess, pipes
import yaml, colorama, appdirs
from docopt import docopt
from collections import OrderedDict
import pygame, pygame.midi as midi
from multiprocessing import Process,Pipe
from src import *
from prompt_toolkit import prompt
from prompt_toolkit.styles import style_from_dict
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.history import FileHistory
from prompt_toolkit.token import Token

style = style_from_dict({
    Token:          '#ff0066',
    Token.DC:       '#00aa00',
    Token.Info:     '#000088',
})

ARGS = docopt(__doc__)
APPNAME = 'decadence'
DIR = appdirs.AppDirs(APPNAME)
# LOG_FN = os.path.join(DIR.user_log_dir,'.log')
HISTORY_FN = os.path.join(DIR.user_config_dir, '.history')
HISTORY = FileHistory(HISTORY_FN)
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))
CFG_PATH = os.path.join(SCRIPT_PATH, 'config')
DEF_PATH = os.path.join(SCRIPT_PATH, 'def')
try:
    os.makedirs(DIR.user_config_dir)
except OSError:
    pass
# logging.basicConfig(filename=LOG_FN,level=logging.DEBUG)

QUITFLAG = False
class SignalError(BaseException):
    pass
class ParseError(BaseException):
    def __init__(self, s=''):
        super(BaseException,self).__init__(s)
def quitnow(signum,frame):
    raise SignalError()
signal.signal(signal.SIGTERM, quitnow)
signal.signal(signal.SIGINT, quitnow)

VIMODE = False

class BGCMD:
    NONE = 0
    QUIT = 1
    SAY = 2
    CACHE = 2
    CLEAR = 3

# Currently not used, caches text to speech stuff in a way compatible with jack
# current super slow, need to write stabilizer first
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
            # log(msg)
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
                log('BAD COMMAND: ' + msg[0])
            self.processses = list(filter(lambda p: p.poll()==None, self.processes))
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

PRINT=True
LOG=False
FOLLOW=False
LINT=False

def follow(count):
    if FOLLOW:
        print('\n' * max(0,count-1))

def log(msg):
    if PRINT:
        print(msg)

def load_cfg(fn):
    with open(os.path.join(CFG_PATH, fn+'.yaml'),'r') as y:
        return yaml.safe_load(y)
def load_def(fn):
    with open(os.path.join(DEF_PATH, fn+'.yaml'),'r') as y:
        return yaml.safe_load(y)

VERSION = '0.1'
NUM_TRACKS = 15 # skip drum channel
NUM_CHANNELS_PER_DEVICE = 15 # "
TRACKS_ACTIVE = 1
DRUM_CHANNEL = 9
SHOWMIDI = False
DRUM_OCTAVE = -2
random.seed()
CSOUND_PORT = 3489

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

def note_name(n, nn=NOTENAMES, ff=FLATS, sf=SOLFEGE):
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
    def add_mode(self, name, index):
        assert index > 0
        self.modes[index-1] = name
    def add_mode_i(self, name, index): # chromaticc index
        assert index > 0
        self.modes[index-1] = name
    def mode(self, index):
        return self.mode[index]
    def mode_name(self, idx):
        assert idx != 0 # modes are 1-based
        m = self.modes[idx-1]
        if not m:
            if idx == 1:
                return self.name
            else:
                return self.name + " mode " + str(idx)
        return m

DEFS = load_def('default')
for f in os.listdir(DEF_PATH):
    if f != 'default.yaml':
        defs = load_def(f[:-len('.yaml')])
        
SCALES = {}
MODES = {}
for k,v in iteritems(DEFS['scales']):
    scale = SCALES[k] = Scale(k, v['intervals'])
    i = 1
    scaleinfo = DEFS['scales'][k]
    if 'modes' in scaleinfo:
        for scalename in scaleinfo['modes']:
            MODES[scalename] = (k,i)
            SCALES[k].add_mode(scalename,i)
            i += 1
    else:
        MODES[k] = (k,1)

DIATONIC = SCALES['diatonic']
# for lookup, normalize name first, add root to result
# number chords can't be used with note numbers "C7 but not 17
# in the future it might be good to lint chord names in a test
# so that they dont clash with commands and break previous songs if chnaged
# This will be replaced for a better parser
# TODO: need optional notes marked
CHORDS = DEFS['chords']
CHORDS_ALT = DEFS['chord_alts']
# CHORD_REPLACE = DEFS['chord_replace']
# replace and keep the rest of the name
CHORDS_REPLACE = OrderedDict([
    ("#5", "+"),
    ("aug", "+"),
    ("mmaj", "mm"),
    ("major", "ma"),
    ("M", "ma"),
    ("maj", "ma"),
    ("minor", "m"),
    ("min", "m"),
    ("dom", ""), # temp
    ("R", ""),
])

# add scales as chords
for sclname, scl in iteritems(SCALES):
    # as with chords, don't list root
    for m in range(len(scl.modes)):
        sclnotes = []
        idx = 0
        inter = list(filter(lambda x:x.isdigit(), scl.intervals))
        if m:
            inter = list(inter[m:]) + list(inter[:m])
        for x in inter:
            sclnotes.append(note_name(idx, False))
            try:
                idx += int(x)
            except ValueError:
                idx += 1 # passing tone is 1
                pass
        sclnotes = ' '.join(sclnotes[1:])
        if m==0:
            CHORDS[sclname] = sclnotes
        # log(scl.mode_name(m+1))
        # log(sclnotes)
        CHORDS[scl.mode_name(m+1)] = sclnotes

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

GM = load_cfg('gm')
DRUM_WORDS = ['drum','drums','drumset','drumkit','percussion']
SPEECH_WORDS = ['speech','say','speak']
GM_LOWER = [""]*len(GM)
for i in range(len(GM)): GM_LOWER[i] = GM[i].lower()

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
    #     log(CHORDS.values())
    #     r = random.choice(CHORDS.values())
    #     log(r)
    #     return r
    for k,v in iteritems(CHORDS_REPLACE):
        cr = c.replace(k,v)
        if cr != c:
            c=cr
            # log(c)
            break

    # - is shorthand for m in the index, but only at beginning and end
    # ex: -7b5 -> m7b5, but mu-7 -> mum7 is invalid
    # remember notes are not part of chord name here (C-7 -> Cm7 works)
    if c.startswith('-'):
        c = 'm' + c[1:]
    if c.endswith('-'):
        c = c[:-1] + 'm'
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
    FLAGS = set('auto_roman')
    def __init__(self, idx, midich, player, schedule):
        self.idx = idx
        # self.players = [player]
        self.player = player
        self.schedule = schedule
        self.channels = [midich]
        self.midich = midich # tracks primary midi channel
        self.initial_channel = midich
        self.non_drum_channel = midich
        self.reset()
    def reset(self):
        self.notes = [0] * RANGE
        self.sustain_notes = [False] * RANGE
        self.mode = 0 # 0 is NONE which inherits global mode
        self.scale = None
        self.instrument = 0
        self.octave = 0 # rel to OCTAVE_BASE
        self.modval = 0 # dont read in mod, just track its change by this channel
        self.sustain = False # sustain everything?
        self.arp_notes = [] # list of notes to arpegiate
        self.arp_idx = 0
        self.arp_cycle_limit = 0 # cycles remaining, only if limit != 0
        self.arp_pattern = [] # relative steps to
        self.arp_enabled = False
        self.arp_once = False
        self.arp_delay = 0.0
        self.arp_sustain = False
        self.arp_note_spacing = 1.0
        self.arp_reverse = False
        self.vel = 100
        self.non_drum_channel = self.initial_channel
        # self.off_vel = 64
        self.staccato = False
        self.patch_num = 0
        self.transpose = 0
        self.pitch = 0.0
        self.tuplets = False
        self.note_spacing = 1.0
        self.tuplet_count = 0
        self.tuplet_offset = 0.0
        self.use_sustain_pedal = False # whether to use midi sustain instead of track
        self.sustain_pedal_state = False # current midi pedal state
        self.schedule.clear_channel(self)
        self.flags = set()
    # def _lazychannelfunc(self):
    #     # get active channel numbers
    #     return list(map(filter(lambda x: self.channels & x[0], [(1<<x,x) for x in range(16)]), lambda x: x[1]))
    def add_flags(self, f):
        if f != f & FLAGS:
            raise ParseError('invalid flags')
        self.flags |= f
    def mute(self):
        for ch in self.channels:
            status = (MIDI_CC<<4) + ch
            if SHOWMIDI: log(FG.YELLOW + 'MIDI: CC (%s, %s, %s)' % (status,120,0))
            self.player.write_short(status, 120, 0)
            if self.modval>0:
                ch.cc(1,0)
                self.modval = False
    def panic(self):
        for ch in self.channels:
            status = (MIDI_CC<<4) + ch
            if SHOWMIDI: log(FG.YELLOW + 'MIDI: CC (%s, %s, %s)' % (status,123,0))
            self.player.write_short(status, 123, 0)
            if self.modval>0:
                ch.cc(1,0)
                self.modval = False
    def note_on(self, n, v=-1, sustain=False):
        if self.use_sustain_pedal:
            if sustain and self.sustain != sustain:
                self.cc(MIDI_SUSTAIN_PEDAL, sustain)
        elif not sustain:  # sustain=False is overridden by track sustain
            sustain = self.sustain
        if v == -1:
            v = self.vel
        if n < 0 or n > RANGE:
            return
        for ch in self.channels:
            self.notes[n] = v
            self.sustain_notes[n] = sustain
            # log("on " + str(n))
            if SHOWMIDI: log(FG.YELLOW + 'MIDI: NOTE ON (%s, %s, %s)' % (n,v,ch))
            self.player.note_on(n,v,ch)
    def note_off(self, n, v=-1):
        if v == -1:
            v = self.vel
        if n < 0 or n >= RANGE:
            return
        if self.notes[n]:
            # log("off " + str(n))
            for ch in self.channels:
                if SHOWMIDI: log(FG.YELLOW + 'MIDI: NOTE OFF (%s, %s, %s)' % (n,v,ch))
                self.player.note_off(n,v,ch)
                self.notes[n] = 0
                self.sustain_notes[n] = 0
            self.cc(MIDI_SUSTAIN_PEDAL, True)
    def release_all(self, mute_sus=False, v=-1):
        if v == -1:
            v = self.vel
        for n in range(RANGE):
            # if mute_sus, mute sustained notes too, otherwise ignore
            mutesus_cond = True
            if not mute_sus:
                mutesus_cond =  not self.sustain_notes[n]
            if self.notes[n] and mutesus_cond:
                for ch in self.channels:
                    if SHOWMIDI: log(FG.YELLOW + 'MIDI: NOTE OFF (%s, %s, %s)' % (n,v,ch))
                    self.player.note_off(n,v,ch)
                    self.notes[n] = 0
                    self.sustain_notes[n] = 0
                # log("off " + str(n))
        # self.notes = [0] * RANGE
        if self.modval>0:
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
            if SHOWMIDI: log(FG.YELLOW + 'MIDI: PITCH (%s, %s)' % (val,val2))
            self.player.write_short(status,val,val2)
            self.mod(0)
    def cc(self, cc, val): # control change
        if type(val) ==type(bool): val = 127 if val else 0 # allow cc bool switches
        for ch in self.channels:
            status = (MIDI_CC<<4) + ch
            if SHOWMIDI: log(FG.YELLOW + 'MIDI: CC (%s, %s, %s)' % (status, cc,val))
            self.player.write_short(status,cc,val)
        if cc==1:
            self.modval = val
    def mod(self, val):
        return cc(1,val)
    def patch(self, p, stackidx=0):
        if isinstance(p,basestring):
            # look up instrument string in GM
            i = 0
            inst = p.replace('_',' ').replace('.',' ').lower()
            
            if p in DRUM_WORDS:
                self.midi_channel(DRUM_CHANNEL)
                p = 0
            else:
                if self.midich == DRUM_CHANNEL:
                    self.midi_channel(self.non_drum_channel)
                
                stop_search = False
                gmwords = GM_LOWER
                for w in inst.split(' '):
                    gmwords = list(filter(lambda x: w in x, gmwords))
                    lengw = len(gmwords)
                    if lengw==1:
                        log('found')
                        break
                    elif lengw==0:
                        log('no match')
                        assert False
                assert len(gmwords) > 0
                log(FG.GREEN + 'GM Patch: ' + FG.WHITE +  gmwords[0])
                p = GM_LOWER.index(gmwords[0])
                # for i in range(len(GM_LOWER)):
                #     continue_search = False
                #     for pword in inst.split(' '):
                #         if pword.lower() not in gmwords:
                #             continue_search = True
                #             break
                #         p = i
                #         stop_search=True
                        
                    # if stop_search:
                    #     break
                    # if continue_search:
                    #     assert i < len(GM_LOWER)-1
                    #     continue

        self.patch_num = p
        # log('PATCH SET - ' + str(p))
        status = (MIDI_PROGRAM<<4) + self.channels[stackidx]
        if SHOWMIDI: log(FG.YELLOW + 'MIDI: PROGRAM (%s, %s)' % (status,p))
        self.player.write_short(status,p)
    def arp(self, notes, count=0, sustain=False, pattern=[1], reverse=False):
        self.arp_enabled = True
        if reverse:
            notes = notes[::-1]
        self.arp_notes = notes
        self.arp_cycle_limit = count
        self.arp_cycle = count
        self.arp_pattern = pattern
        self.arp_pattern_idx = 0
        self.arp_idx = 0 # use inversions to move this start point (?)
        self.arp_once = False
        self.arp_sustain = False
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
        self.arp_pattern_idx = (self.arp_pattern_idx + 1) % len(self.arp_pattern)
        self.arp_delay = (self.arp_note_spacing+1.0) % 1.0
        return (note, self.arp_delay)
    def tuplet_next(self):
        delay = 0.0
        if self.tuplets:
            delay = self.tuplet_offset
            self.tuplet_offset = (self.tuplet_offset+self.note_spacing) % 1.0
            self.tuplet_count -= 1
            if not self.tuplet_count:
                self.tuplets = False
        else:
            self.tuplet_stop()
        if feq(delay,1.0):
            return 0.0
        # log(delay)
        return delay
    def tuplet_stop(self):
        self.tuplets = False
        self.tuplet_count = 0
        self.note_spacing = 1.0
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
        # log(self.clock)

        try:
            self.events = sorted(self.events, key=lambda e: e.t)
            for ev in self.events:
                if ev.t > 1.0:
                    ev.t -= 1.0
                else:
                    # sleep until next event
                    if ev.t >= 0.0:
                        time.sleep(SPEED*t*(ev.t-self.passed))
                        ev.func(0)
                        self.passed = ev.t # only inc if positive
                    else:
                        ev.func(0)
                    
                    processed += 1

            slp = t*(1.0-self.passed) # remaining time
            if slp > 0.0:
                time.sleep(SPEED*slp)
            self.passed = 0.0
            self.events = self.events[processed:]
        except KeyboardInterrupt as ex:
            # don't replay events
            self.events = self.events[processed:]
            raise ex
        except:
            QUITFLAG = True

def count_seq(seq, match=''):
    if not seq:
        return 0
    if match == '':
        match = seq[0]
        seq = seq[1:]
    r = 1
    for c in seq:
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
    a,b = peel_int_s(s,d)
    return (int(a),b)

def peel_int_s(s, d=None):
    r = ''
    for ch in s:
        if ch.isdigit():
            r += ch
        elif ch=='-' and not r:
            r += ch
        else:
            break
    if r == '-': return (0,0)
    if not r: return (d,'') if d!=None else (0,'')
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
COLUMNS = 0
COLUMN_SHIFT = 0
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
CCHAR = ' <>=~.\'`,_&|!?*\"$(){}[]%'
CCHAR_START = 'T' # control chars
SCHEDULE = []
SEPARATORS = []
TRACK_HISTORY = ['.'] * NUM_TRACKS
FN = None
row = 0
stoprow = -1
DCMODE = 'n' # n normal c command s sequence
next_arg = 1
# request_tempo = False
# request_grid = False
skip = 0
SCHEDULE = Schedule()
TRACKS = []
SHELL = True
DAEMON = False
GUI = False
PORTNAME = ''
SPEED = 1.0

for arg,val in iteritems(ARGS):
    if val:
        if arg == '--tempo': TEMPO = float(val)
        elif arg == '--grid': GRID = float(val)
        elif arg == '--note': GRID = float(val)/4.0
        elif arg == '--speed': SPEED = float(val)
        elif arg == '--verbose': SHOWTEXT = True
        elif arg == '--dev': PORTNAME = val
        elif arg == '--vi': VIMODE = True
        elif arg == '--patch':
            vals = val.split(',')
            for i in range(len(vals)):
                val = vals[i]
                if val.isdigit():
                    TRACKS[i].patch(int(val))
                else:
                    TRACKS[i].patch(val)
        elif arg == '--sustain': SUSTAIN=True
        elif arg == '--nomute': NOMUTE=True
        elif arg == '--remote': DAEMON = True
        elif arg == '--lint': LINT = True
        elif arg == '--quiet': PRINT = False
        elif arg == '--follow':
            FOLLOW = True
            PRINT = False
        elif arg == '--flats': FLATS = True
        elif arg == '--sharps': SHARPS= True
        elif arg == '--edit': pass
        elif arg == '-l' and val: DCMODE = 'l'
        elif arg == '-c' and val: DCMODE = 'c'

SUPPORT = set(['midi'])
SUPPORT_ALL = set(['sonic-pi','csound','midi']) # gme,mpe
psonic = None
if ARGS['--sonic-pi']:
    import psonic
    SUPPORT.add('sonic-pi')

csound = None
if ARGS['--csound']:
    csound_proc = subprocess.Popen(['csound', '-odac', '--port='+str(CSOUND_PORT)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    csound = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    SUPPORT.add('csound')

def csound_send(s):
    assert csound
    return csound.sendto(s,('localhost',CSOUND_PORT))

# import logging

if DCMODE=='l':
    buf = ' '.join(ARGS['LINE_CONTENT']).split(';') # ;
elif DCMODE=='c':
    buf = ' '.join(ARGS['COMMANDS']).split(' ') # spaces
else: # mode n
    # if len(sys.argv)>=2:
    #     FN = sys.argv[-1]
    if ARGS['SONGNAME']:
        FN = ARGS['SONGNAME']
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
                    if ls.startswith(':'):
                        bm = ls[1:]
                        # only store INITIAL marker positions
                        if not bm in MARKERS:
                            MARKERS[bm] = lc
                    elif ls.startswith('|') and ls.endswith(':'):
                        bm = ls[1:-1]
                        # only store INITIAL marker positions
                        if not bm in MARKERS:
                            MARKERS[bm] = lc

                lc += 1
                buf += [line]
            SHELL = False
    else:
        if DCMODE == 'n':
            DCMODE = ''
        SHELL = True

midi.init()
if midi.get_count()==0:
    print('No midi devices found.')
    sys.exit(1)    
dev = -1
for i in range(midi.get_count()):
    port = pygame.midi.get_device_info(i)
    portname = port[1].decode('utf-8')
    # timidity
    devs = [
        'timidity port 0',
        'synth input port',
        'loopmidi'
        # helm will autoconnect
    ]
    if PORTNAME:
        if portname.lower().startswith(PORTNAME.lower()):
            PORTNAME = portname
            dev = i
            break
    for name in devs:
        if portname.lower().startswith(name):
            PORTNAME = portname
            dev = i
            break

# PLAYER = pygame.midi.Output(pygame.midi.get_default_output_id())

PLAYER = pygame.midi.Output(dev)
INSTRUMENT = 0
PLAYER.set_instrument(0)
mch = 0
for i in range(NUM_CHANNELS_PER_DEVICE):
    # log("%s -> %s" % (i,mch))
    TRACKS.append(Track(i, mch, PLAYER, SCHEDULE))
    mch += 2 if i==DRUM_CHANNEL else 1

if SUSTAIN:
    TRACKS[0].sustain = SUSTAIN

# show nice output in certain modes
if SHELL or DCMODE in 'cl':
    SHOWTEXT = True

for i in range(len(sys.argv)):
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
                log('invalid entry point')
                QUITFLAG = True
        try:
            stoprow = int(vals[1])
        except ValueError:
            try:
                # we cannot cut buf now, since seq might be non-linear
                stoprow = MARKERS[vals[0]]
            except KeyError:
                log('invalid stop point')
                QUITFLAG = True
        except IndexError:
            pass # no stop param

if SHELL:
    log(FG.BLUE + 'decadence v'+str(VERSION))
    log('Copyright (c) 2018 Grady O\'Connell')
    log('https://github.com/flipcoder/decadence')
    s = SUPPORT_ALL & SUPPORT
    s2 = SUPPORT_ALL - SUPPORT
    if s:
        log(FG.GREEN + 'Active Modules: ' + FG.WHITE +  ', '.join(s) + FG.WHITE)
    if s2:
        log(FG.RED + 'Inactive Modules: ' +  FG.WHITE + ', '.join(s2))
    if PORTNAME:
        log(FG.GREEN + 'Device: ' + FG.WHITE + '%s' % (PORTNAME if PORTNAME else 'Unknown',))
        if TRACKS[0].midich == DRUM_CHANNEL:
            log(FG.GREEN + 'GM Percussion')
        else:
            log(FG.GREEN + 'GM Patch: '+ FG.WHITE +'%s' % GM[TRACKS[0].patch_num])
    log('Use -h for command line options.')
    log('Read the manual and look at examples. Have fun!')
    log('')

header = True # set this to false as we reached cell data
while not QUITFLAG:
    try:
        line = '.'
        try:
            line = buf[row]
            if stoprow!=-1 and row == stoprow:
                buf = []
                raise IndexError
        except IndexError:
            row = len(buf)
            # done with file, finish playing some stuff
            
            arps_remaining = 0
            if SHELL or DAEMON or DCMODE in ['c','l']: # finish arps in shell mode
                for ch in TRACKS[:TRACKS_ACTIVE]:
                    if ch.arp_enabled:
                        if ch.arp_cycle_limit or not ch.arp_once:
                            arps_remaining += 1
                            line = '.'
                if not arps_remaining and not SHELL and DCMODE not in ['c','l']:
                    break
                line = '.'
            
            if not arps_remaining and not SCHEDULE.pending():
                if SHELL or DAEMON:
                    for ch in TRACKS[:TRACKS_ACTIVE]:
                        ch.release_all()
                    
                    if SHELL:
                        # SHELL PROMPT
                        # log(orr(TRACKS[0].scale,SCALE).mode_name(orr(TRACKS[0].mode,MODE)))
                        cur_oct = TRACKS[0].octave
                        # cline = FG.GREEN + 'DC> '+FG.BLUE+ '('+str(int(TEMPO))+'bpm x'+str(int(GRID))+' '+\
                        #     note_name(TRACKS[0].transpose) + ' ' +\
                        #     orr(TRACKS[0].scale,SCALE).mode_name(orr(TRACKS[0].mode,MODE,-1))+\
                        #     ')> '
                        cline = 'DC> ('+str(int(TEMPO))+'bpm x'+str(int(GRID))+' '+\
                            note_name(TRACKS[0].transpose) + ' ' +\
                            orr(TRACKS[0].scale,SCALE).mode_name(orr(TRACKS[0].mode,MODE,-1))+\
                            ')> '
                        # if bufline.endswith('.dc'):
                            # play file?
                        # bufline = raw_input(cline)
                        bufline = prompt(cline,
                            history=HISTORY, vi_mode=VIMODE)
                        bufline = list(filter(None, bufline.split(' ')))
                        bufline = list(map(lambda b: b.replace(';',' '), bufline))
                        buf += bufline
                    elif DAEMON:
                        pass
                        # wait on socket
                    continue
                
                else:
                    break
            
        log(FG.MAGENTA + line)
        
        # cells = line.split(' '*2)
        
        # if line.startswith('|'):
        #     SEPARATORS = [] # clear
        #     # column setup!
        #     for i in range(1,len(line)):
        #         if line[i]=='|':
        #             SEPARATORS.append(i)
        
        # log(BG.RED + line)
        fullline = line[:]
        line = line.strip()
        
        # LINE COMMANDS
        ctrl = False
        cells = []

        if line:
            # COMMENTS (;)
            if line[0] == ';':
                follow(1)
                row += 1
                continue
            
            # set marker
            if line[-1]==':': # suffix marker
                # allow override of markers in case of reuse
                MARKERS[line[:-1]] = row
                follow(1)
                row += 1
                continue
                # continue
            elif line[0]==':': #prefix marker
                # allow override of markers in case of reuse
                MARKERS[line[1:]] = row
                follow(1)
                row += 1
                continue
            
            # TODO: global 'silent' commands (doesn't take time)
            if line.startswith('%'):
                line = line[1:].strip() # remove % and spaces
                for tok in line.split(' '):
                    if not tok:
                        break
                    if tok[0]==' ':
                        tok = tok[1:]
                    var = tok[0].upper()
                    if var in 'TGNPSRMCX':
                        cmd = tok.split(' ')[0]
                        op = cmd[1]
                        try:
                            val = cmd[2:]
                        except:
                            val = ''
                        # log("op val %s %s" % (op,val))
                        if op == ':': op = '='
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
                            elif var=='X': GRID/=float(val)
                            elif var=='N': GRID/=float(val) #!
                            elif var=='T': TEMPO/=float(val)
                        elif op=='*':
                            if var=='G': GRID*=float(val)
                            elif var=='X': GRID*=float(val)
                            elif var=='N': GRID*=float(val) #!
                            elif var=='T': TEMPO*=float(val)
                        elif op=='=':
                            if var=='G': GRID=float(val)
                            elif var=='X': GRID=float(val)
                            elif var=='N': GRID=float(val)/4.0 #!
                            elif var=='T':
                                vals = val.split('x')
                                TEMPO=float(vals[0])
                                try:
                                    GRID = float(vals[1])
                                except:
                                    pass
                            elif var=='C':
                                vals = val.split(',')
                                COLUMNS = int(vals[0])
                                try:
                                    COLUMN_SHIFT = int(vals[1])
                                except:
                                    pass
                            elif var=='P':
                                vals = val.split(',')
                                for i in range(len(vals)):
                                    p = vals[i]
                                    if p.strip().isdigit():
                                        TRACKS[i].patch(int(p))
                                    else:
                                        TRACKS[i].patch(p)
                            elif var=='F': # flags
                                for i in range(len(vals)):
                                    TRACKS[i].add_flags(val.split(','))
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
                                        val = val.lower().replace(' ','')
                                        modescale = MODES[val]
                                    
                                    try:
                                        SCALE = SCALES[modescale[0]]
                                        MODE = modescale[1]
                                        inter = SCALE.intervals
                                        TRANSPOSE = 0
                                        
                                        log(MODE-1)
                                        if var=='R':
                                            for i in range(MODE-1):
                                                inc = 0
                                                try:
                                                    inc = int(inter[i])
                                                except ValueError:
                                                    pass
                                                TRANSPOSE += inc
                                    except ValueError:
                                        log('no such scale')
                                        assert False
                                else:
                                    TRANSPOSE = 0
                                    
                follow(1)
                row += 1
                continue
            
            # jumps
            if line.startswith(':') and line.endswith("|"):
                jumpline = line[1:-1]
            else:
                jumpline = line[1:]
            if line[0]=='@':
                if len(jumpline)==0:
                    row = 0
                    continue
                if len(jumpline)>=1 and jumpline == '@': # @@ return/pop callstack
                    frame = CALLSTACK[-1]
                    CALLSTACK = CALLSTACK[:-1]
                    row = frame.row
                    continue
                jumpline = jumpline.split('*') # * repeats
                bm = jumpline[0] # marker name
                count = 0
                if len(jumpline)>=1:
                    count = int(jumpline) if len(jumpline)>=1 else 1
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
        gutter = ''
        if SHELL:
            cells = list(filter(None,line.split(' ')))
        elif COLUMNS:
            cells = fullline
            # shift column pos right if any
            cells = ' ' * max(0,-COLUMN_SHIFT) + cells
            # shift columns right, creating left-hand gutter
            # cells = cells[-1*min(0,COLUMN_SHIFT):] # create gutter (if negative shift)
            # separate into chunks based on column width
            cells = [cells[i:i + COLUMNS] for i in range(0, len(cells), COLUMNS)]
            # log(cells)
        elif not SEPARATORS:
            # AUTOGENERATE CELL SEPARATORS
            cells = fullline.split(' ')
            pos = 0
            for cell in cells:
                if cell:
                    if pos:
                        SEPARATORS.append(pos)
                    # log(cell)
                pos += len(cell) + 1
            # log( "SEPARATORS " + str(SEPARATORS))
            cells = list(filter(None,cells))
            # if fullline.startswith(' '):
            #     cells = ['.'] + cells # dont filter first one
            autoseparate = True
        else:
            # SPLIT BASED ON SEPARATORS
            s = 0
            seplen = len(SEPARATORS)
            # log(seplen)
            pos = 0
            for i in range(seplen):
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
            chordnames = []
            
            cell_before_slash=cell[:]
            sz_before_slash=len(cell)
            slash = cell.split('/') # slash chords
            # log(slash)
            tok = slash[0]
            cell = slash[0][:]
            slashidx = 0
            addbottom = False # add note at bottom instead
            # slash = cell[0:min(cell.find(n) for n in '/|')]
            
            # chordnameslist = []
            # chordnoteslist = []
            # chordrootslist = []
            
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
                    for amb in ('ion','dor','dom'): # I dim or D dim conflict w/ ionian and dorian
                        ambiguous += tok.lower().startswith(amb)
                    if ct and not ambiguous:
                        lower = (c.lower()==c)
                        c = ['','i','ii','iii','iv','v','vi','vii','viii','ix','x','xi','xii'].index(c.lower())
                        noteletter = note_name(c-1,NOTENAMES,FLATS)
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
                        wrap = ((c-1) // notecount)
                        note = ((c-1) % notecount)+1
                        # log('note ' + str(note))
                        
                        for i in range(1,note):
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
                                # log((chord_note_count-1)-inverted)
                                inverted -= 1
                            else:
                                # log('inversion?')
                                # log(n)
                                n += 12
                                inverted -= 1
                        assert inversion != 0
                        if inversion!=1:
                            if flip_inversion: # not working yet
                                # log('note ' + str(note))
                                # log('down inv: %s' % (inversion/chord_note_count+1))
                                # n -= 12 * (inversion/chord_note_count+1)
                                pass
                            else:
                                # log('inv: %s' % (inversion/chord_note_count))
                                n += 12 * (inversion/chord_note_count)
                        # log('---')
                        # log(n)
                        # log('n slash %s,%s' %(n,slashidx))
                        n += 12 * (wrap - slashidx)
                        
                        # log(tok)
                        tok = tok[ct:]
                        if not expanded: cell = cell[ct:]
                        
                        # number_notes = not roman
                        
                        if tok and tok[0]==':': # currently broken? wrong notes
                            tok = tok[1:] # allow chord sep
                            if not expanded: cell = cell[1:]
                        
                        # log('note: %s' % n)
                
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
                        # accidentals = True # dont need this
                    
                        if not tok:
                            c = 'b' # b note was falsely interpreted as flat
                        
                        # note names, don't use these in chord defn
                        try:
                            # dont allow lower case, since 'b' means flat
                            note = ' CDEFGAB'.index(c.upper())
                            noteletter = str(c)
                            for i in range(note):
                                n += int(DIATONIC.intervals[i-1])
                            n -= slashidx*12
                            # adjust B(7) and A(6) below C, based on accidentials
                            nn = (n-1)%12+1 # n normalized
                            if (8<=nn<=9 and accidentals.startswith('b')): # Ab or Abb
                                n -= 12
                            elif nn == 10 and not accidentals:
                                n -= 12
                            elif nn > 10:
                                n -= 12
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
                            # log(tok)
                            cut = 0
                            nonotes = []
                            chordname = ''
                            reverse = False
                            addhigherroot = False
                            
                            # cut chord name from text after it
                            for char in tok:
                                if cut==0 and char in CCHAR_START:
                                    break
                                if char in CCHAR:
                                    break
                                if char == '\\':
                                    reverse = True
                                    break
                                if char == '^':
                                    addhigherroot = True
                                    break
                                chordname += char
                                addnotes = []
                                try:
                                    # TODO: addchords
                                    
                                    # TODO note removal (Maj7no5)
                                    if chordname[-2:]=='no':
                                        numberpart = tok[cut+1:]
                                        # second check will throws
                                        if numberpart in '#b' or (int(numberpart) or True):
                                            # if tok[]
                                            prefix,ct = peel_any(tok[cut:],'#b')
                                            if ct: cut += ct
                                            
                                            num,ct = peel_uint(tok[cut+1:])
                                            if ct:
                                                cut += ct
                                                cut -= 2 # remove "no"
                                                chordname = chordname[:-2] # cut "no
                                                nonotes.append(str(prefix)+str(num)) # ex: b5
                                                break
                                          
                                    if 'add' in chordname:
                                        addtoks = chordname.split('add')
                                        chordname = addtoks[0]
                                        addnotes = addtoks[1:]
                                except IndexError:
                                    log('chordname length ' + str(len(chordname)))
                                    pass # chordname length
                                except ValueError:
                                    log('bad cast ' + char)
                                    pass # bad int(char)
                                cut += 1
                                i += 1
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
                            
                            # log(chordname)
                            # don't include tuplet in chordname
                            if chordname.endswith('T'):
                                chordname = chordname[:-1]
                                cut -= 1
                            
                            # log(chordname)
                            if roman: # roman chordnames are sometimes empty
                                if chordname and not chordname[1:] in 'bcdef':
                                    if roman == -1: # minor
                                        if chordname[0] in '6719':
                                            chordname = 'm' + chordname
                                else:
                                    chordname = 'maj' if roman>0 else 'm' + chordname

                            if chordname:
                                # log(chordname)
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
                                    chord_notes = list(filter(lambda x: x not in nonotes, chord_notes))
                                    chord_note_count = len(chord_notes)+1 # + 1 for root
                                    expanded = True
                                    tok = ""
                                    cell = cell[cut:]
                                    is_chord = True
                                except KeyError as e:
                                    # may have grabbed a ctrl char, pop one
                                    if len(chord_notes)>1: # can pop?
                                        try:
                                            chord_notes = expand_chord(chordname[:-1])
                                            chord_notes = list(filter(lambda x,nonotes=nonotes: x in nonotes))
                                            chord_note_count = len(chord_notes) # + 1 for root
                                            expanded = True
                                            try:
                                                tok = tok[cut-1:]
                                                cell = cell[cut-1:]
                                                is_chord = True
                                            except:
                                                assert False
                                        except KeyError:
                                            log('key error')
                                            break
                                    else:
                                        # noteloop = True
                                        # assert False
                                        # invalid chord
                                        log(FG.RED + 'Invalid Chord: ' + chordname)
                                        break
                            
                            if is_chord:
                                # assert not accidentals # accidentals with no note name?
                                if reverse:
                                    chord_notes = chord_notes[::-1] + ['1']
                                else:
                                    chord_notes = ['1'] + chord_notes

                                chord_notes += addnotes # TODO: sort
                                # slashnotes[0].append(n + chord_root - 1 - slashidx*12)
                                # chordnameslist.append(chordname)
                                # chordnoteslist.append(chord_notes)
                                # chordrootslist.append(chord_root)
                                chord_root = n
                                ignore = False # reenable default root if chord was w/o note name
                                continue
                            else:
                                # log('not chord, treat as note')
                                pass
                            #     assert False # not a chord, treat as note
                            #     break
                        else: # blank chord name
                            # log('blank chord name')
                            # expanded = False
                            pass
                    else: # not tok and not expanded
                        # log('not tok and not expanded')
                        pass
                # else and not chord_notes:
                #     # last note in chord, we're done
                #     tok = ""
                #     noteloop = False
                    
                    slashnotes[0].append(n + chord_root-1)
                
                if expanded:
                    if not chord_notes:
                        # next chord
                        expanded = False
                
                if chord_notes:
                    tok = chord_notes[0]
                    chord_notes = chord_notes[1:]
                    chord_note_index += 1
                    # fix negative inversions
                    if inversion < 0: # not yet working
                        # octave += inversion/chord_note_count
                        inversion = inversion%chord_note_count
                        inverted = -inverted
                        flip_inversion = True
                        
                if not expanded:
                    inversion = 1 # chord inversion
                    flip_inversion = False
                    inverted = 0 # notes pending inversion
                    chord_root = 1
                    chord_note_count = 0 # include root
                    chord_note_index = -1
                    chord_note_index = -1
                    # next slash chord part
                    flip_inversion = False
                    inversion = 1
                    chord_notes = []
                    slash = slash[1:]
                    if slash:
                        tok = slash[0]
                        cell = slash[0]
                        slashnotes = [[]] + slashnotes
                    else:
                        break
                    slashidx += 1
                # if expanded and not chord_notes:
                #     break

            notes = [i for o in slashnotes for i in o] # combine slashnotes
            cell = cell_before_slash[sz_before_slash-len(cell):]

            if ignore:
                allnotes = []
                notes = []

            # save the intended notes since since scheduling may drop some
            # during control phase
            allnotes = notes 
            
            # TODO: arp doesn't work if channel not visible/present, move this
            if ch.arp_enabled:
                if notes: # incoming notes?
                    # log(notes)
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
            #     log(notes)
            
            cell = cell.strip() # ignore spaces

            vel = ch.vel
            mute = False
            sustain = ch.sustain
           
            delay = 0.0
            showtext = []
            arpnotes = False
            arpreverse = False
            arppattern = [1]
            duration = 0.0

            # if cell and cell[0]=='|':
            #     if not expanded: cell = cell[1:]

            # log(cell)

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
                #     log("+")
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
                    # if sym== '>': ch.octave = octave # persist
                    # row_events += 1
                # elif c == '-':
                #     c = cell[1]
                #     shift = int(c) if c.isdigit() else 0
                #     p = base + (octave+shift) * 12
                # INVERSION
                ct = 0
                if c == '>' or c=='<':
                    sign = (1 if c=='>' else -1)
                    ct = count_seq(cell)
                    for i in range(ct):
                        if notes:
                            notes[i%len(notes)] += 12*sign
                    notes = notes[sign*1:] + notes[:1*sign]
                    # when used w/o note/chord, track history should update
                    # TRACK_HISTORY[cell_idx] = fullcell_sub
                    # log(notes)
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
                elif cl>1 and cell.startswith('~'): # vib/pitch wheel
                    if c=='/' or c=='\\':
                        num,ct = peel_int_s(cell[2:])
                        num *= 1 if c=='/' else -1
                        cell = cell[2:]
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
                elif c == '~': # pitch wheel
                    ch.pitch(127)
                    cell = cell[1:]
                elif c == '`': # mod wheel
                    ch.mod(127)
                    cell = cell[1:]
                # SUSTAIN
                elif cell.startswith('__-'):
                    ch.mute()
                    sustain = ch.sustain = True
                    cell = cell[3:]
                elif c2=='__':
                    sustain = ch.sustain = True
                    cell = cell[2:]
                elif c2=='_-':
                    sustain = False
                    cell = cell[2:]
                elif c=='_':
                    sustain = True
                    cell = cell[1:]
                elif cell.startswith('%v'): # volume
                    pass
                    cell = cell[2:]
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
                #     # log(vel)
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
                elif c=='(' or c==')': # note shift (early/delay)
                    num = ''
                    cell = cell[1:]
                    s,ct = peel_uint(cell, 5)
                    if ct:
                        cell = cell[ct:]
                    delay = -1*(c=='(')*float('0.'+num) if num else 0.5
                    assert(delay > 0.0) # TOOD: impl early notes
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
                    vel = max(0,int(ch.vel*0.25))
                    cell = cell[2:]
                    if SHOWTEXT:
                        showtext.append('soften(??)')
                elif c=='?': # quiet
                    vel = max(0,int(ch.vel*0.5))
                    cell = cell[1:]
                    if SHOWTEXT:
                        showtext.append('soften(??)')
                # elif cell.startswith('$$') or (c=='$' and lennotes==1):
                elif c=='$': # strum/spread/tremolo
                    sq = count_seq(cell)
                    cell = cell[sq:]
                    num,ct = peel_uint_s(cell,'0')
                    cell = cell[ct:]
                    num = float('0.'+num)
                    strum = 1.0
                    if len(notes)==1: # tremolo
                        notes = [notes[i:i + sq] for i in range(0, len(notes), sq)]
                    # log('strum')
                    if SHOWTEXT:
                        showtext.append('strum($)')
                elif c=='&':
                    count = count_seq(cell)
                    num,ct = peel_uint(cell[count:],0)
                        # notes = list(itertools.chain.from_iterable(itertools.repeat(\
                        #     x, count) for x in notes\
                        # ))
                    cell = cell[ct+count:]
                    if count>1: arpreverse = True
                    if not notes:
                        # & restarts arp (if no note)
                        ch.arp_enabled = True
                        ch.arp_count = num
                        ch.arp_idx = 0
                    else:
                        arpnotes = True

                    if cell.startswith(':'):
                        num,ct = peel_uint(cell[1:],1)
                        arppattern = [num]
                        cell = cell[1+ct:]
                    if SHOWTEXT:
                        showtext.append('arpeggio(&)')
                elif c=='t': # tuplet
                    if not ch.tuplets:
                        ch.tuplets = True
                        pow2i = 0.0
                        cell = cell[1:]
                        num,ct = peel_uint(cell,'3')
                        cell = cell[ct:]
                        ct2=0
                        denom = 0
                        if cell and cell[0]==':':
                            denom,ct2 = peel_float(cell)
                            cell = cell[1+ct2:]
                        if not ct2:
                            for i in itertools.count():
                                denom = 1 << i
                                if denom > num:
                                    break
                        ch.note_spacing = denom/float(num) # !
                        ch.tuplet_count = int(num)
                        cell = cell[ct:]
                    else:
                        cell = cell[1:]
                        pass
                elif c=='@':
                    if not notes:
                        cell = []
                        continue # ignore jump
                # elif c==':':
                #     if not notes:
                #         cell = []
                #         continue # ignore marker
                elif c=='%':
                    # ctrl line
                    cell = []
                    break
                else:
                    if DCMODE in 'cl':
                        log(FG.BLUE + line)
                    indent = ' ' * (len(fullcell)-len(cell))
                    log(FG.RED + indent +  "^ Unexpected " + cell[0] + " here")
                    cell = []
                    ignore = True
                    break
                
                # elif c=='/': # bend in
                # elif c=='\\': # bend down
            
            base =  (OCTAVE_BASE+octave) * 12 - 1 + TRANSPOSE + ch.transpose
            p = base
            
            if arpnotes:
                ch.arp(notes, num, sustain, arppattern, arpreverse)
                arpnext = ch.arp_next()
                notes = [arpnext[0]]
                delay = arpnext[1]
                # if not fcmp(delay):
                #     pass
                    # schedule=True

            if notes:
                ch.release_all()

            for ev in events:
                SCHEDULE.add(ev)
            
            delta = 0 # how much to separate notes
            if strum < -EPSILON:
                notes = notes[::-1] # reverse
                strum -= strum
            if strum > EPSILON:
                ln = len(notes)
                delta = (1.0/(ln*forr(duration,1.0))) #t between notes

            if SHOWTEXT:
                # log(FG.MAGENTA + ', '.join(map(lambda n: note_name(p+n), notes)))
                # chordoutput = chordname
                # if chordoutput and noletter:
                #     coordoutput = note_name(chord_root+base) + chordoutput
                # log(FG.CYAN + chordoutput + " ("+ \)
                #     (', '.join(map(lambda n,base=base: note_name(base+n),notes)))+")"
                # log(showtext)
                showtext = []
                if chordname and not ignore:
                    noteletter = note_name(n+base)
                    # for cn in chordnames:
                    #     log(FG.CYAN + noteletter + cn + " ("+ \)
                    #         (', '.join(map(lambda n,base=base: note_name(base+n),allnotes)))+")"

            delay += ch.tuplet_next()
            
            i = 0
            for n in notes:
                # if no schedule, play note immediately
                # also if scheduled, play first note of strum if there's no delay
                if fzero(delay):
                # if not schedule or (i==0 and strum>=EPSILON and delay<EPSILON):
                    ch.note_on(p + n, vel, sustain)
                else:
                    f = lambda _,ch=ch,p=p,n=n,vel=vel,sustain=sustain: ch.note_on(p + n, vel, sustain)
                    SCHEDULE.add(Event(delay,f,ch))
                delay += delta
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
                # log(FG.RED + traceback.format_exc())
                QUITFLAG = True
                break
            except:
                log(FG.RED + traceback.format_exc())
                if SHELL:
                    QUITFLAG = True
                    break
                if not SHELL and not pauseDC():
                    QUITFLAG = True
                    break

        if QUITFLAG:
            break
         
    except KeyboardInterrupt:
        QUITFLAG = True
        break
    except SignalError:
        QUITFLAG = True
        break
    except:
        log(FG.RED + traceback.format_exc())
        if SHELL:
            QUITFLAG = True
            break
        if not SHELL and not pauseDC():
            break

    follow(1)
    row += 1

# TODO: turn all midi note off
i = 0
for ch in TRACKS:
    if not NOMUTE:
        ch.panic()
    ch.player = None

del PLAYER
midi.quit()

if csound and csound_proc:
    csound_proc.kill()

# def main():
#     pass
    
# if __name__=='__main__':
#     curses.wrapper(main)

if BCPROC:
    BGPIPE.send((BGCMD.QUIT,))
    BGPROC.join()

