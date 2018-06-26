#!/usr/bin/python
import os, sys
from future.utils import iteritems
from collections import OrderedDict
from . import def_path
from . import load_def

FLATS=False
SOLFEGE=False
NOTENAMES=True # show note names instead of numbers

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
for f in os.listdir(def_path()):
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

