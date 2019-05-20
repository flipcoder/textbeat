from .defs import *
from shutilwhich import which
import tempfile, shutil
from . import instrument
# from xml.dom import minidom
ARGS = get_args()
SUPPORT = set(['midi'])
SUPPORT_ALL = set(['midi', 'fluidsynth', 'soundfonts']) # gme,mpe,sonicpi,supercollider,csound
MIDI = True
SOUNDFONTS = False # TODO: make this a SupportPlugin ref
AUTO = False
AUTO_MODULE = None
SOUNDFONT_MODULE = None
auto_inited = False

SUPPORT_PLUGINS = {}

# load plugins from plugins dir

import textbeat.plugins as tbp
from textbeat.plugins import *
# search module exports for plugins
plugs = []
for p in tbp.__dict__:
    try:
        pattr = getattr(tbp, p)
        plugs += [pattr.export(ARGS)]
    except:
        pass
# plugs = instrument.plugins()
for plug in plugs:
    # plug.init()
    ps = plug.support()
    SUPPORT_ALL = SUPPORT_ALL.union(ps)
    if not plug.supported():
        continue
    for s in ps:
        SUPPORT.add(s)
        SUPPORT_PLUGINS[s] = plug
        if 'auto' in s:
            AUTO = True
            AUTO_MODULE = plug
            auto_inited = True
        if 'soundfonts' in s:
            SOUNDFONTS = True
            SOUNDFONT_MODULE = plug

def supports(dev):
    global SUPPORT
    return dev in SUPPORT

def supports_soundfonts():
    return SOUNDFONTS
def supports_auto():
    return AUTO
def supports(tech):
    return tech in SUPPORT

def support_stop():
    for plug in plugs:
        if plug.inited():
            plug.stop()
    
