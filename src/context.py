from . import *

class StackFrame:
    def __init__(self, row, caller, count):
        self.row = row
        self.caller = caller
        self.count = count # repeat call counter
        self.markers = {} # marker name -> line
        self.returns = {} # repeat row -> number of rpts left
        # self.returns[row] = 0

class Context:
    
    def __init__(self):
        self.quitflag = False
        self.vimode = False
        self.bcproc = None
        self.log = False
        self.canfollow = False
        self.cansleep = True
        self.lint = False
        self.tracks_active = 1
        self.showmidi = False
        self.scale = DIATONIC
        self.mode = 1
        self.transpose = 0
        self.tempo = 90.0
        self.grid = 4.0 # Grid subdivisions of a beat (4 = sixteenth note)
        self.columns = 0
        self.column_shift = 0
        self.showtext = True # nice output (-v), only shell and cmd modes by default
        self.sustain = False # start sustained
        self.ring = False # disables midi muting on program exit
        self.buf = []
        self.markers = {}
        f = StackFrame(-1,-1,0)
        f.returns[''] = 0
        self.callstack = [f]
        self.schedule = []
        self.separators = []
        self.track_history = ['.'] * NUM_TRACKS
        self.fn = None
        self.row = 0
        # self.rowno = []
        self.startrow = -1
        self.stoprow = -1
        self.dcmode = 'n' # n normal c command s sequence
        self.schedule = Schedule(self)
        self.tracks = []
        self.shell = False
        self.remote = False
        self.interactive = False
        self.gui = False
        self.portname = ''
        self.speed = 1.0
        self.muted = False # mute all except for solo tracks
        self.player = None
        self.instrument = None
        self.t = 0.0
        self.last_follow = 0
        self.last_marker = -1

    def follow(self):
        if self.startrow==-1 and self.canfollow:
            cursor = self.row + 1
            if cursor != self.last_follow:
                print(cursor)
                self.last_cursor = cursor
            # print(self.rowno[self.row])

    def pause(self):
        try:
            for ch in self.tracks[:self.tracks_active]:
                ch.release_all(True)
            input(' === PAUSED === ')
        except:
            return False
        return True

