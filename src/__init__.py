#!/usr/bin/python
from __future__ import unicode_literals, print_function, generators
import os, sys, time, random, itertools, signal, tempfile, traceback, socket
import time, subprocess, pipes, collections
from collections import OrderedDict
from builtins import range, str, input
from future.utils import iteritems
import yaml, colorama, appdirs
from docopt import docopt
import mido
with open(os.devnull, 'w') as devnull:
    # suppress pygame messages
    stdout = sys.stdout
    sys.stdout = devnull
    import pygame, pygame.midi
    sys.stdout = stdout
from multiprocessing import Process,Pipe
from prompt_toolkit import prompt
from prompt_toolkit.styles import style_from_dict
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.history import FileHistory
from prompt_toolkit.token import Token

if sys.version_info[0]==3:
    basestring = str

# VERSION = '0.1'
FG = colorama.Fore
BG = colorama.Back
STYLE = colorama.Style
NUM_TRACKS = 15 # skip drum channel
NUM_CHANNELS_PER_DEVICE = 15 # "DRUM_CHANNEL = 9
DRUM_CHANNEL = 9
DRUM_OCTAVE = -2
CSOUND_PORT = 3489
EPSILON = 0.0001
ARGS = None
RANGE = 109
OCTAVE_BASE = 5
DRUM_WORDS = ['drum','drums','drumset','drumkit','percussion']
CCHAR = ' <>=~.\'`,_&|!?*\"$(){}[]%@;'
CCHAR_START = 'TV' # control chars
PRINT = True

def bit(x):
    return 1 << x
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

def set_args(args):
    global ARGS
    ARGS = args
def get_args():
    return ARGS
def constrain(a,n1=1,n2=0):
    try:
        int(a)
    except ValueError:
        # fix defaults for float
        if n2==0:
            n2 = 0.0
        if n1==1:
            n1 = 1.0
    return min(max(n1,n2),max(min(n1,n2),a))

APPNAME = 'decadence'
DIR = appdirs.AppDirs(APPNAME)
# LOG_FN = os.path.join(DIR.user_log_dir,'.log')
HISTORY_FN = os.path.join(DIR.user_config_dir, '.history')
HISTORY = FileHistory(HISTORY_FN)
SCRIPT_PATH = os.path.dirname(os.path.realpath(os.path.join(__file__,'..')))
CFG_PATH = os.path.join(SCRIPT_PATH, 'config')
DEF_PATH = os.path.join(SCRIPT_PATH, 'def')
DEF_EXT = '.yaml'
def cfg_path():
    return CFG_PATH
def def_path():
    return DEF_PATH
try:
    os.makedirs(DIR.user_config_dir)
except OSError:
    pass

class SignalError(BaseException):
    pass
class ParseError(BaseException):
    def __init__(self, s=''):
        super(BaseException,self).__init__(s)
def quitnow(signum,frame):
    raise SignalError()

signal.signal(signal.SIGTERM, quitnow)
signal.signal(signal.SIGINT, quitnow)

class BGCMD:
    NONE = 0
    QUIT = 1
    SAY = 2
    CACHE = 2
    CLEAR = 3

def set_print(b):
    global PRINT
    PRINT = b

def log(msg):
    if PRINT:
        print(msg)

def load_cfg(fn):
    with open(os.path.join(CFG_PATH, fn+'.yaml'),'r') as y:
        return yaml.safe_load(y)
def load_def(fn):
    with open(os.path.join(DEF_PATH, fn+'.yaml'),'r') as y:
        return yaml.safe_load(y)

random.seed()

class Diff:
    NONE = 0
    ADD = 1
    REMOVE = 2
    UPDATE = 3

def merge(a, b, overwrite=False, skip=None, diff=None, pth=None):
    for k,v in iteritems(b):
        contains = k in a
        if contains and isinstance(a[k], dict) and isinstance(b[k], collections.Mapping):
            loc = (pth+[k]) if pth else None
            if callable(skip):
                if not skip(loc,v):
                    merge(a[k],b[k], overwrite, skip, diff, loc)
            else:
                merge(a[k],b[k], overwrite, skip, diff, loc)
        else:
            if contains:
                if callable(overwrite):
                    loc = (pth+[k]) if pth!=None else k
                    if overwrite(loc,v):
                        a[k] = b[k]
                        if diff!=None:
                            diff.add((Diff.UPDATE,loc,v))
                    else:
                        pass
                elif overwrite:
                    if diff!=None:
                        old = copy.copy(a[k])
                    a[k] = b[k]
                    if diff!=None:
                        loc = (pth+[k]) if pth!=None else k
                        diff.add((Diff.UPDATE,loc,v,old))
            else:
                a[k] = b[k]
                if diff!=None:
                    loc = (pth+[k]) if pth!=None else k
                    diff.add((Diff.ADD,loc,v))
    return a

DEFS = {}
for f in os.listdir(DEF_PATH):
    if f.lower().endswith(DEF_EXT):
        merge(DEFS,load_def(f[:-len(DEF_EXT)]))

CC = {}
try:
    CC = DEFS['cc']
except KeyError:
    pass

def get_defs():
    return DEFS

from .schedule import *
from .theory import *
from .midi import *
from .track import *
from .parser import *
from .remote import *
from .player import *

