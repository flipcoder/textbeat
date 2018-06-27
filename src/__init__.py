#!/usr/bin/python
from __future__ import unicode_literals, print_function, generators
import os, sys, time, random, itertools, signal, tempfile, traceback, socket
from builtins import range, str, input
from future.utils import iteritems
import time, subprocess, pipes
import yaml, colorama, appdirs
from docopt import docopt
from collections import OrderedDict
import pygame, pygame.midi
from multiprocessing import Process,Pipe
from prompt_toolkit import prompt
from prompt_toolkit.styles import style_from_dict
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.history import FileHistory
from prompt_toolkit.token import Token

if sys.version_info[0]==3:
    basestring = str

VERSION = '0.1'
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
CCHAR = ' <>=~.\'`,_&|!?*\"$(){}[]%'
CCHAR_START = 'T' # control chars
PRINT = True

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

APPNAME = 'decadence'
DIR = appdirs.AppDirs(APPNAME)
# LOG_FN = os.path.join(DIR.user_log_dir,'.log')
HISTORY_FN = os.path.join(DIR.user_config_dir, '.history')
HISTORY = FileHistory(HISTORY_FN)
SCRIPT_PATH = os.path.dirname(os.path.realpath(os.path.join(__file__,'..')))
CFG_PATH = os.path.join(SCRIPT_PATH, 'config')
DEF_PATH = os.path.join(SCRIPT_PATH, 'def')
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
class NoSuchScale(BaseException):
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

DEFS = load_def('default')
for f in os.listdir(def_path()):
    if f != 'default.yaml':
        defs = load_def(f[:-len('.yaml')])
        c = defs.copy()
        c.update(DEFS)
        DEFS = c

def get_defs():
    return DEFS

from .schedule import *
from .parser import *
from .theory import *
from .midi import *
from .track import *
from .context import *
from .remote import *

