from .defs import *

from collections import deque
from prompt_toolkit import PromptSession
from enum import Enum

STACK_SIZE = 64

class LoopResult(Enum):
    """This enum types help us decide whether we should continue in the loop, break, or proceed.
    This type is needed so we can choose how to deal interact with a loop outside a functions scope.
    """
    PROCEED = 0     # Continue forward in the current loop
    CONTINUE = 1    # Skip to the next iteration
    BREAK = 2       # Break from the loop

class StackFrame(object):
    """
    Stack frames are items on the Player's call stack.
    Similar to function calls, the Player uses a stack to track markers/repeats.
    """
    def __init__(self, name, row, caller, count):
        self.name = name
        self.row = row
        self.caller = caller
        self.count = count # repeat call counter
        self.markers = {} # marker name -> line
        self.returns = {} # repeat row -> number of rpts left
        # self.returns[row] = 0
    def __str__(self):
        return 'StackFrame' + str((self.name, self.row, self.caller, self.count, self.markers, self.returns))

class Player(object):
    """
    The Player is what parses the txbt format and plays it.
    Beware! This is the most "quick and dirty" part of textbeat, so it will probably
    be rewritten eventually.
    """
    
    class Flag:
        """
        Bitflag options for Roman numeral notation, transposition, and looping
        """
        ROMAN = bit(0) # use roman numeral notation
        TRANSPOSE = bit(1) # allow transposition of note letters
        LOOP = bit(2) # loop the textbeat file (good for jamtrack, metronome)
    
    # string names for the bitflags
    FLAGS = [
        'roman',
        'transpose',
        'loop'
    ]
    # FLAGS = set([
    #     'roman', # STUB: fit roman chord in scale shape
    #     'transpose', # allow transposition of note letters
    #     'loop'
    # ])

    def __init__(self):
        self.quitflag = False # Set this bool to escape to stop the parser
        self.vimode = False # use vi readline mode for prompt_toolkit
        # self.log = False
        # 'canfollow' means cursor location is printed for interop with vim and others
        self.canfollow = False
        self.last_follow = 0 # the last line 'followed' (printed)
        # sleeping can be disabled for writing to midi files instead of playback
        self.cansleep = True
        self.lint = False # analyze file (not yet implemented)
        self.tracks_active = 1 # the current number of known active tracks found by Player
        self.showmidi = False
        self.scale = DIATONIC # default scale, see other options in theory.py
        self.mode = 1 # musical mode number, 1=ionian
        self.transpose = 0 # current transposion of entire song (in steps)
        self.octave = 0 # relative octave transposition of entire song
        self.tempo = 90.0 # default tempo when unspecified (may be different inside shell)
        self.grid = 4.0 # Grid subdivisions of a beat (4 = sixteenth note)
        # columns/shift is hardcoded column placement and widths for
        #   when working in text editors with column highlighting
        self.columns = 0
        self.column_shift = 0
        # self.showtextstr = []
        self.showtext = False # nice output (-v), only shell and cmd modes by default
        self.sustain = False # start sustained?
        self.ring = False # ring: disables midi muting on program exit, letting notes ring out
        self.buf = []
        self.markers = {} # markers are for doing jumps and repeats
        f = StackFrame('',-1,-1,0)
        f.returns[''] = 0
        self.tutorial = None # Tutorial object to run (should be run inside shell, see -T)
        # self.callstack = [f] # callstack for moving around the file using markers/repeats
        self.callstack = deque(maxlen=STACK_SIZE) # callstack for moving around the file using markers/repeats
        self.callstack.append(f)
        # self.separators = [] # separators are currently not supported
        self.track_history = ['.'] * NUM_TRACKS # keep track of track history for replaying with " symbol
        self.fn = None # filename
        self.row = 0 # parser location, row #
        # self.rowno = []
        self.startrow = -1 # last row processed, def -1
        self.stoprow = -1 # row to stop on, if playing a specific region (-1 is entire file)
        self.cmdmode = 'n' # n normal c command s sequence
        self.plugins = [] # (under dev) textbeat interop plugins
        self.tracks = []
        self.shell = False
        # eventually, text editor interop may be done by controlling txbt through a socket
        #   instead of column following
        # self.remote = None
        self.interactive = False
        self.gui = False
        self.portname = ''
        self.speed = 1.0 # speed multiplier (this one is per file)
        self.muted = False # mute all except for "solo" tracks
        self.midi = []
        # self.instrument = None
        self.t = 0.0 # time since file processing started, in sec
        self.last_follow = -1 # last follow location (row #)
        self.last_marker = -1 # last marker location (row #)
        self.midifile = None # midi file to write output to
        self.flags = 0 # see FLAGS (bitflags)
        self.version = '0'
        self.auto = False # (under dev) automatically generate VST rack using a plugin
        # embedded config files (key=filename), for things like synth/plugin customization
        self.embedded_files = {}
        self.vibrato_tracks = set() # tracks that currently have vibrato going

        # other devices require enabling them at the top of the file
        self.devices = ['midi']
        
        # (under dev) schedule will eventually decouple the player and parser
        self.schedule = Schedule(self)
        
    def init(self):
        
        for i in range(len(sys.argv)):
            arg = sys.argv[i]

            # play range (+ param, comma-separated start and end)
            if arg.startswith('+'):
                vals = arg[1:].split(',')
                try:
                    self.startrow = int(vals[0])
                except ValueError:
                    try:
                        self.startrow = self.markers[vals[0]]
                    except KeyError:
                        log('invalid entry point')
                        self.quitflag = True
                try:
                    self.stoprow = int(vals[1])
                except ValueError:
                    try:
                        # we cannot cut buf now, since seq might be non-linear
                        self.stoprow = self.markers[vals[0]]
                    except KeyError:
                        log('invalid stop point')
                        self.quitflag = True
                except IndexError:
                    pass # no stop param
        
        # read embedded files
        for row in self.buf:
            embedded_fn = None
            embedded_file = []
            base_indent = ''
            if embedded_fn:
                if row.startswith(' ') or row.startswith('\t'):
                    if not base_indent:
                        base_indent = row[0] * count_seq(row)
                        embedded_file = self.row
                    embedded_file += [row[base_indent:]]
                else:
                    base_indent = ''
                    self.embedded_files[embedded_fn] = embedded_file
                    embedded_fn = None
                    embedded_file = []
            
            if row.startswith('`'):
                embedded_fn = row[1:]
                embedded_file = []
            
        # out(self.embedded_files.keys())

    def refresh_devices(self):
        # determine output device support and load external programs
        # try:
        from .support import supports, SUPPORT_PLUGINS
        # except:
        #     import textbeat.support as support
        for dev in self.devices:
            if not supports(dev):
                if dev!='auto':
                    out('Device not supported by system: ' + dev)
                else:
                    out('Loading instrument presets requires a compatible host module.')
                assert False
            try:
                # support_enable[dev](self.rack)
                SUPPORT_PLUGINS[dev].enable(self.plugins)
            except KeyError:
                # no init needed, silent
                pass
        self.auto = 'auto' in self.devices

    def set_plugins(self, plugins):
        self.plugins = plugins
        self.refresh_devices()
        
    # def remove_flags(self, f):
    #     pass
    def add_flags(self, f):
        if isinstance(f, basestring):
            f = 1 << self.FLAGS.index(f)
        elif isinstance(f, int):
            assert f > 0
        else:
            for e in f:
                if e.startswith('-'):
                    # TODO: cancel flag?
                    # e = e[1:]
                    # self.flags &= ~e
                    pass
                else:
                    self.add_flags(e)
            return
        self.flags |= f
    def has_flags(self, f):
        if isinstance(f, basestring):
            f = 1 << self.FLAGS.index(f)
        elif isinstance(f, int):
            assert f > 0
        else:
            vals = f
            f = 0
            i = 0
            for e in self.FLAGS:
                if e in vals:
                    f |= 1 << i
                i += 1
            # for e in vals:
            #     f |= 1 << self.FLAGS.index(e)
            return
        return self.flags & f

    # for editor integration: "follows" the output of the file by printing
    #   line numbers to stdout for every parsed line
    def follow(self):
        if self.startrow==-1 and self.canfollow:
            cursor = self.row + 1
            if cursor != self.last_follow:
                print(cursor)
                self.last_cursor = cursor
            # out(self.rowno[self.row])

    def pause(self):
        try:
            for ch in self.tracks[:self.tracks_active]:
                ch.release_all(True)
            out('')
            input('PAUSED: Press ENTER to resume. Press Ctrl-C To quit.')
        except:
            return False
        return True

    def write_midi_tempo(self):
        # set initial midifile tempo
        if self.midifile:
            if not self.midifile.tracks:
                self.midifile.tracks.append(mido.MidiTrack())
            self.midifile.tracks[0].append(mido.MetaMessage(
                'set_tempo', tempo=mido.bpm2tempo(self.tempo)
            ))

               
    async def run(self):
        for ch in self.tracks:
            ch.refresh()
        
        self.header = True
        embedded_file = False
        
        self.write_midi_tempo()

        prompt_session = PromptSession(history=HISTORY, vi_mode=self.vimode)
        
        while not self.quitflag:
            self.follow()
            
            try:
                self.line = '.'
                loop_result = await self.next_row(prompt_session)
                if loop_result == LoopResult.CONTINUE: continue
                elif loop_result == LoopResult.BREAK: break

                log(FG.MAGENTA + self.line)
                
                # cells = line.split(' '*2)
                
                # if line.startswith('|'):
                #     self.separators = [] # clear
                #     # column setup!
                #     for i in range(1,len(line)):
                #         if line[i]=='|':
                #             self.separators.append(i)
                
                # log(BG.RED + line)

                # skip reading embedded files, since they're already in mem
                if self.line.startswith('`'):
                    embedded_file = True
                    self.row += 1
                    continue
                elif self.line.startswith(' ') or self.line.startswith('\t'):
                    if embedded_file:
                        self.row += 1
                        continue
                else:
                    embedded_file = False
                
                fullline = self.line[:]
                self.line = self.line.strip()
                
                # LINE COMMANDS
                ctrl = False
                cells = []

                if self.line:
                    # COMMENTS (;)
                    if self.line[0] == ';' and not self.line.startswith(';;'):
                        self.row += 1
                        continue
                    
                    # set marker
                    # if self.line[-1]==':': # suffix marker
                    #     # allow override of markers in case of reuse
                    #     self.markers[self.line[:-1]] = self.row
                    #     self.callstack[-1].returns[self.row] = 0
                    #     self.row += 1
                    #     continue
                    #     # continue
                    if self.line[0]=='#' and self.line[-1]=='#':
                        # track title, ignore
                        self.row += 1
                        continue
                    
                    # TODO: global 'silent' commands (doesn't consume time)
                    if self.line.startswith('%'):
                        self.line = self.line[1:].strip() # remove % and spaces
                        for tok in self.line.split(' '):
                            if not tok:
                                break
                            if tok[0]==' ':
                                tok = tok[1:]
                            var = tok[0].upper()
                            if var in 'TGXNPSRCKFDR': # global vars %
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
                                    if var in 'GX': self.grid/=float(val)
                                    elif var=='N': self.grid/=float(val) #!
                                    elif var=='T': self.tempo/=float(val)
                                    else: assert False
                                elif op=='*':
                                    if var in 'GX': self.grid*=float(val)
                                    elif var=='N': self.grid*=float(val) #!
                                    elif var=='T': self.tempo*=float(val)
                                    else: assert False
                                elif op=='+':
                                    if var=='K': self.transpose += note_offset('#1' if val=='+' else val)
                                    # elif var=='O': self.octave += int(1 if val=='+' else val)
                                    elif var=='T': self.tempo += max(0,float(val))
                                    elif var in 'GX': self.grid += max(0,float(val))
                                    else: assert False
                                    # if var=='K':
                                    #     self.octave += -1*sgn(self.transpose)*(self.transpose//12)
                                    #     self.transpose = self.transpose%12
                                elif op=='-':
                                    if var=='K':
                                        self.transpose -= note_offset(val)
                                        out(note_offset(val))
                                    # elif var=='O': self.octave -= int(1 if val=='-' else val)
                                    elif var=='T': self.tempo -= max(0,float(val))
                                    elif var in 'GX': self.grid -= max(0,float(val))
                                    else: assert False
                                    # self.octave += -1*sgn(self.transpose)*(self.transpose//12)
                                    # if var=='K':
                                    #     self.octave += -1*sgn(self.transpose)*(self.transpose//12)
                                    #     self.transpose = self.transpose%12
                                elif op=='=':
                                    if var in 'GX': self.grid=float(val)
                                    elif var=='R':
                                        if not 'auto' in self.devices:
                                            self.devices = ['auto'] + self.devices
                                        self.set_plugins(val.split(','))
                                    elif var=='V': self.version = val
                                    elif var=='D':
                                        self.devices = val.split(',')
                                        self.refresh_devices()
                                    # elif var=='O': self.octave = int(val)
                                    elif var=='N': self.grid=float(val)/4.0 #!
                                    elif var=='T':
                                        vals = val.split('x')
                                        self.tempo=float(vals[0])
                                        try:
                                            self.grid = float(vals[1])
                                        except:
                                            pass
                                    elif var=='C':
                                        vals = val.split(',')
                                        self.columns = int(vals[0])
                                        try:
                                            self.column_shift = int(vals[1])
                                        except:
                                            pass
                                    elif var=='P':
                                        vals = val.split(',')
                                        for i in range(len(vals)):
                                            p = vals[i]
                                            if p.strip().isdigit():
                                                self.tracks[i].patch(int(p))
                                            else:
                                                self.tracks[i].patch(p)
                                    elif var=='F': # flags
                                        self.add_flags(val.split(','))
                                        # for i in range(len(vals)): # TODO: ?
                                        #     self.tracks[i].add_flags(val.split(','))
                                    # elif var=='O':
                                    #     self.octave = int(val)
                                    elif var=='K':
                                        self.transpose = note_offset(val)
                                        # self.octave += -1*sgn(self.transpose)*(self.transpose//12)
                                        # self.transpose = self.transpose%12
                                    elif var=='S':
                                        # var R=relative usage deprecated
                                        try:
                                            if val:
                                                val = val.lower()
                                                # ambigous alts
                                                
                                                if val.isdigit():
                                                    modescale = (self.scale.name,int(val))
                                                else:
                                                    alts = {'major':'ionian','minor':'aeolian'}
                                                    # try:
                                                    #     modescale = (alts[val[0],val[1])
                                                    # except KeyError:
                                                    #     pass
                                                    val = val.lower().replace(' ','')
                                                    
                                                    try:
                                                        modescale = MODES[val]
                                                    except KeyError:
                                                        raise NoSuchScale()
                                                
                                                try:
                                                    self.scale = SCALES[modescale[0]]
                                                    self.mode = modescale[1]
                                                    inter = self.scale.intervals
                                                    self.transpose = 0
                                                    # log(self.mode-1)
                                                    
                                                    if var=='R':
                                                        for i in range(self.mode-1):
                                                            inc = 0
                                                            try:
                                                                inc = int(inter[i])
                                                            except ValueError:
                                                                pass
                                                            self.transpose += inc
                                                    elif var=='S':
                                                        pass
                                                except ValueError:
                                                    raise NoSuchScale()
                                            # else:
                                            #     self.transpose = 0
                                        
                                        except NoSuchScale:
                                            out(FG.RED + 'No such scale.')
                                            pass
                                    else: assert False # no such var
                                else: assert False # no such op
                                            
                                if var=='T':
                                    if self.midifile:
                                        if not self.midifile.tracks:
                                            self.midifile.tracks.append(mido.MidiTrack())
                                        self.midifile.tracks[0].append(mido.MetaMessage(
                                            'set_tempo', tempo=mido.bpm2tempo(int(
                                                val.split('x')[0]
                                            ))
                                        ))
                        self.row += 1
                        continue
                    
                    # set marker here
                    if (self.line[0]=='|' or self.line.startswith(':|')) and self.line[-1]==':':
                        # allow override of markers in case of reuse
                        frame = self.callstack[-1]
                        if self.line[0]==':': # :|:
                            bm = self.line[self.line.index('|')+1:-1]
                        else: 
                            bm = self.line[1:-1] # |:
                        self.markers[bm] = self.row
                        frame.markers[bm] = self.row
                        # self.callstack[-1].returns[self.row] = 0
                        self.last_marker = self.row
                        self.row += 1
                        if self.line[0]!=':': # |blah:
                            # marker only, not repeat
                            continue
                        # marker AND repeat, continue to repeat parser section
                    
                    if self.line.startswith('||||'):
                        self.quitflag = True
                        continue
                    elif self.line.startswith('|||'):
                        p = None
                        while True:
                            assert self.callstack
                            p = self.callstack.pop()
                            if p.name != '':
                                break
                        self.row = p.caller + 1
                        continue
                    elif self.line.startswith('||'): # return/pop
                        # print(self.callstack)
                        if len(self.callstack)>1:
                            frame = self.callstack[-1]
                            frame.count = max(0,frame.count-1)
                            if frame.count:
                                self.row = frame.row + 1
                                continue
                            else:
                                # print('returning to caller', frame.caller)
                                self.row = frame.caller + 1
                                # self.callstack = self.callstack[:-1]
                                self.callstack.pop()
                                continue
                        else:
                            # allow bypassing '||' on empty stack
                            # self.quitflag = True
                            self.row += 1
                            continue
                    elif self.line[0]==':' and self.line[-1] in '|:' and '|' in self.line:
                        jumpline = self.line[1:self.line.index('|')]
                        frame = self.callstack[-1]
                        jumpline = jumpline.split('*') # *n = n repeats
                        bm = jumpline[0]
                        if bm.isdigit():
                            bm = ''
                            count = int(jumpline[0])
                        else:
                            count = int(jumpline[1]) if len(jumpline)>1 else 1
                        # frame = self.callstack[-1]
                        # if count: # repeats remaining

                        if bm:
                            bmrow = self.markers[bm]
                        else:
                            bmrow = self.last_marker

                        # if not bm:
                        #     frame.count = max(0,frame.count-1)
                        #     if frame.count:
                        #         self.row = frame.row + 1
                        #         continue
                        #     else:
                        #         self.row += 1
                        #         continue
                        
                        # if bmrow in frame.returns:
                            
                            # return to marker (no pushing)
                            #     self.callstack.append(StackFrame(bm, bmrow, self.row, count))
                        #     self.markers[jumpline[0]] = bmrow
                        #     self.row = bmrow + 1
                        #     self.last_marker = bmrow
                        
                        # print('bm', bm)
                        # print('fm', frame.markers)
                        # print('fm', frame.returns)
                        if bmrow==self.last_marker or bm in frame.markers: # call w/o push?
                        # # if bm in frame.markers:
                            # ctx already passed bookmark, call w/o pushing (return to mark)
                            # print(frame.returns, self.row)
                            if self.row in frame.returns: # have we repeated yet?
                                # 2nd repeat (count exists)
                                rpt = frame.returns[self.row]
                                if rpt>0:
                                    frame.returns[self.row] = rpt - 1
                                    self.row = bmrow + 1 # repeat
                                else:
                                    # repeating done
                                    # frame.returns[self.row] = rpt - 1
                                    del frame.returns[self.row] # reset
                                    self.row += 1
                            else:
                                # start return count
                                self.callstack.append(StackFrame(bm, bmrow, self.row, count))
                                self.callstack[-1].returns[self.row] = count - 1
                                self.row = bmrow + 1 # repeat
                        else:
                            # mark not yet passed, do push/pop
                            # print(bm)
                            self.callstack.append(StackFrame(bm, bmrow, self.row, count))
                            self.markers[bm] = bmrow
                            self.row = bmrow + 1
                            self.last_marker = bmrow

                        # else:
                        #     retcount = frame.returns[self.row]
                        #     if retcount > count:
                        #         self.row = bmrow + 1
                        #         frame.returns[self.row] -= 1
                        #     else:
                        #         self.row += 1
                        # else:
                        #     self.callstack.append(StackFrame(bm, bmrow, self.row, count))
                        #     self.markers[jumpline[0]] = bmrow
                        #     self.row = bmrow + 1
                        #     self.last_marker = bmrow
                        continue

                # this is not indented in blank lines because even blank lines have this logic
                gutter = ''
                if self.shell:
                    cells = list(filter(None,self.line.split(' ')))
                elif self.columns:
                    cells = fullline
                    # shift column pos right if any
                    cells = ' ' * max(0,-self.column_shift) + cells
                    # shift columns right, creating left-hand gutter
                    # cells = cells[-1*min(0,self.column_shift):] # create gutter (if negative shift)
                    # separate into chunks based on column width
                    cells = [cells[i:i + self.columns] for i in range(0, len(cells), self.columns)]
                    # log(cells)
                else:
                    # elif not self.separators:
                    # AUTOGENERATE CELL self.separators
                    cells = fullline.split(' ')
                    pos = 0
                    for cell in cells:
                        # if cell:
                            # if pos:
                            #     self.separators.append(pos)
                            # log(cell)
                        pos += len(cell) + 1
                    # log( "self.separators " + str(self.separators))
                    cells = list(filter(None,cells))
                    # if fullline.startswith(' '):
                    #     cells = ['.'] + cells # dont filter first one
                    autoseparate = True
                # else:
                #     log('Track separators are no longer supported.')
                #     assert False
                #     # SPLIT BASED ON self.separators
                #     s = 0
                #     seplen = len(self.separators)
                #     # log(seplen)
                #     pos = 0
                #     for i in range(seplen):
                #         cells.append(fullline[pos:self.separators[i]].strip())
                #         pos = self.separators[i]
                #     lastcell = fullline[pos:].strip()
                #     if lastcell: cells.append(lastcell)
                
                # make sure active tracks get empty cell
                len_cells = len(cells)
                if len_cells > self.tracks_active:
                    self.tracks_active = len_cells
                else:
                    # add empty cells for active tracks to the right
                    cells += ['.'] * (self.tracks_active - len_cells)
                del len_cells
                
                cell_idx = 0
                
                # CELL LOGIC
                # cells += ['.'] * (tracks_active - len(cells))
                for cell in cells:
                    
                    cell = cells[cell_idx]
                    ch = self.tracks[cell_idx]
                    fullcell = cell[:]
                    ignore = False
                    skipcell = False
                    
                    # if self.instrument != ch.instrument:
                    #     self.player.set_instrument(ch.instrument)
                    #     self.instrument = ch.instrument

                    cell = cell.strip()
                    if cell:
                        self.header = False # contents here, no longer in file header
                    
                    if cell.count('\"') == 1: # " is recall, but multiple " means lyrics/speak?
                        cell = cell.replace("\"", self.track_history[cell_idx])
                    else:
                        self.track_history[cell_idx] = cell
                    
                    fullcell_sub = cell[:]

                    # empty
                    # if not cell:
                    #     cell_idx += 1
                    #     continue

                    if cell and cell[0]=='-':
                        if self.shell:
                            ch.stop()
                        else:
                            ch.release_all() # don't mute sustain
                        cell_idx += 1
                        continue
                    if cell=='--':
                        ch.sustain = False
                        cell_idx += 1
                        continue
                    
                    if cell and cell[0]=='=': # hard stop
                        ch.panic()
                        cell_idx += 1
                        continue
                    if cell=='==':
                        ch.panic()
                        ch.sustain = False
                        cell_idx += 1
                        continue

                    if cell and cell[0]=='-': # stop prefix
                        ch.release_all(True)
                        # ch.sustain = False
                        cell = cell[1:]
         
                    notecount = len(ch.scale.intervals if ch.scale else self.scale.intervals)
                    # octave = int(cell[0]) // notecount
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
                    octave = self.octave + ch.octave
                    strum = 0.0
                    noteletter = '' # track this just in case (can include I and V)
                    chordname = ''
                    chordnames = []

                    # frets = bool(ch.frets)
                    # frets = False
                    # if cell and len(cell.strip())>1 and cell[0]=='|' and cell[-1]!=':':
                    #     cells = cells.lstrip()[1:]
                    #     frets = True
                    
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
                            # Help parser ambiguities (TODO: make these automatic)
                            # (These are names that begin with letters or roman numerals)
                            for amb in ('ion','dor','dim','dom','alt','dou','egy','aeo','dia','gui','bas','aug'):
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
                                    # TODO: allow zero if only if fretting mode
                                    # skipcell = True
                                    cell = cell[1:]
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
                                        m = orr(ch.mode,self.mode,-1)-1
                                        steps = orr(ch.scale,self.scale).intervals
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
                                        # log('down inv: %s' % (inversion//chord_note_count+1))
                                        # n -= 12 * (inversion//chord_note_count+1)
                                        pass
                                    else:
                                        # log('inv: %s' % (inversion//chord_note_count))
                                        n += 12 * (inversion//chord_note_count)
                                # log('---')
                                # log(n)
                                # log('n slash %s,%s' %(n,slashidx))
                                n += 12 * (wrap - slashidx)
                                
                                # log(tok)
                                tok = tok[ct:]
                                if not expanded: cell = cell[ct:]
                                
                                # number_notes = not roman
                                
                                # if tok and tok[0]==':': # currently broken? wrong notes
                                #     n += 1
                                #     tok = tok[1:] # allow chord sep
                                #     if not expanded: cell = cell[1:]
                                
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
                                    
                                    if ch.flags & Player.Flag.TRANSPOSE:
                                        # compensate so note letters are absolute
                                        n -= self.transpose + ch.transpose
                                    
                                    if not expanded: cell = cell[1:]
                                except ValueError:
                                    ignore = True
                            else:
                                ignore = True # reenable if there's a chord listed
                            
                            # CHORDS
                            addnotes = []
                            is_chord = False
                            if not expanded:
                                if tok or roman:
                                    # log(tok)
                                    cut = 0
                                    nonotes = []
                                    chordname = ''
                                    reverse = False
                                    # addhigherroot = False
                                    
                                    # cut chord name from text after it
                                    for char in tok:
                                        if cut==0 and char in CCHAR_START:
                                            break
                                        if cut!=1 and char.isupper():
                                            break
                                        if char in CCHAR:
                                            break
                                        if char == '\\':
                                            reverse = True
                                            break
                                        # if char == '^':
                                        #     addhigherroot = True
                                        #     break
                                        chordname += char
                                        try:
                                            # TODO: addchords
                                            
                                            # TODO omit note (Maj7no5)
                                            if chordname[-2:]=='no':
                                                # print(tok)
                                                # print(cut)
                                                cut += 1 # The 'o' of no
                                                numberpart = tok[cut:]
                                                # print(numberpart)
                                                # second check will throws
                                                int_numberpart = None
                                                try:
                                                    int_numberpart = int(numberpart)
                                                except ValueError:
                                                    pass
                                                if numberpart[0] in '#b' or int_numberpart!=None:
                                                    # if tok[]
                                                    prefix,ct = peel_any(tok[cut:],'#b')
                                                    # print('prefix', prefix)
                                                    # print('ct', ct)
                                                    if ct: cut += ct
                                                    
                                                    num,ct = peel_uint(tok[cut:])
                                                    if ct:
                                                        cut += ct
                                                        # cut += 1 # remove "no"
                                                        chordname = chordname[:-2] # cut "no"
                                                        if prefix:
                                                            nonotes.append(str(prefix)+str(num)) # ex: b5
                                                        else:
                                                            nonotes.append(str(num)) # ex: b5
                                                        # print(nonotes)
                                                        break
                                                
                                                # cut += 2
                                                
                                        except IndexError:
                                            log('bad chordname index')
                                            pass # chordname length
                                        except ValueError:
                                            log('bad cast ' + char)
                                            pass # bad int(char)
                                        cut += 1
                                        # i += 1
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
                                    if 'add' in chordname:
                                        # out(chordname)
                                        addtoks = chordname.split('add')
                                        # out(addtoks)
                                        chordname = addtoks[0]
                                        addnotes = addtoks[1:]
                                    
                                    if chordname.endswith('T'):
                                        chordname = chordname[:-1]
                                        cut -= 1
                                    
                                    # log(chordname)
                                    if roman: # roman chordnames are sometimes empty
                                        if chordname: #and not chordname[1:] in 'bcdef':
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

                                        # letter inversions deprecated (use <>)
                                        # try:
                                        #     inv_letter = ' abcdef'.index(chordname[-1])
                                        
                                        #     # num,ct = peel_int(tok[cut+1:])
                                        #     # if ct and num!=0:
                                        #     # cut += ct + 1
                                        #     if inv_letter>=1:
                                        #         inversion = max(1,inv_letter)
                                        #         inverted = max(0,inversion-1) # keep count of pending notes to invert
                                        #         # cut+=1
                                        #         chordname = chordname[:-1]
                                                
                                        # except ValueError:
                                        #     pass
                                        
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
                                            if '1' in nonotes:
                                                chord_notes = chord_notes[::-1]
                                            else:
                                                chord_notes = chord_notes[::-1] + ['1']
                                        else:
                                            if '1' not in nonotes:
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

                    # if frets:
                    #     ch.strings = notes
                    #     notes = []

                    # 'ignore' means do outer break
                    if ignore:
                        allnotes = []
                        notes = []
                        # if skipcell: # 0 or something weird, completely skip line
                        #     break
                    
                    # save the intended notes since since scheduling may drop some
                    # during control phase
                    allnotes = notes 
                    sustain = ch.sustain
                    delay = 0.0
                    
                    # TODO: arp doesn't work if channel not visible/present, move this
                    if ch.arp_enabled:
                        if notes: # incoming notes?
                            # log(notes)
                            # interupt arp
                            ch.arp_stop()
                        else:
                            # continue arp
                            if ch.arp_next(self.shell or self.cmdmode in 'lc'):
                                notes = [ch.arp_note]
                                delay = ch.arp_delay
                                sustain = ch.arp_sustain
                                if not fzero(delay):
                                    ignore = False
                            #   schedule=True

                    # if notes:
                    #     log(notes)
                    
                    cell = cell.strip() # ignore spaces

                    vel = ch.vel
                    stop = False
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

                    # cell = self.fx(cell)
                    
                    accent = ''
                    notevalue = ''
                    tuplets = False
                    while len(cell) >= 1: # recompute len before check
                        if fullcell=='.':
                            break
                        spacer = False
                        if cell.strip() and cell[0] in '@ ':
                            spacer = True
                            cell = cell[count_seq(cell):] 

                        after = [] # after events
                        clen = len(cell)
                        # All tokens here must be listed in CCHAR
                        
                        ## + and - symbols are changed to mean minor and aug chords
                        # if c == '+':
                        #     log("+")
                        #     c = cell[1]
                        #     shift = int(c) if c.isdigit() else 0
                        #     mn = n + base + (octave+shift) * 12
                        c = cell[0]
                        c2 = None
                        if clen:
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
                        ct = 0
                        # CELL COMMENTS
                        if c2==';;': # cell comment
                            cell = []
                            break
                        #INVERSIONS
                        elif c == '>' or c=='<':
                            sign = (1 if c=='>' else -1)
                            ct = count_seq(cell)
                            for i in range(ct):
                                if notes:
                                    notes[i%len(notes)] += 12*sign
                            notes = notes[sign*1:] + notes[:1*sign]
                            # when used w/o note/chord, track history should update
                            # self.track_history[cell_idx] = fullcell_sub
                            # log(notes)
                            if ch.arp_enabled:
                                ch.arp_notes = ch.arp_notes[1:] + ch.arp_notes[:1]
                            cell = cell[ct:]
                        # OCTAVE SHIFTING
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
                        # PITCH WHEEL
                        elif clen>1 and c=='~':
                            cell = cell[1:]
                            # sn = 1.0
                            if cell[0]=='/' or cell[0]=='\\':
                                # sn = 1.0 if cell[0]=='/' else -1.0
                                cell = cell[1:]
                            num,ct = peel_uint_s(cell)
                            if ct:
                                onum = num
                                num = float('0.'+num)
                                num *= 1.0 if c=='/' else -1.0
                                sign = 1
                                if num<0:
                                    num=onum[1:]
                                    num = float('0.'+num)
                                    sign = -1
                                vel = constrain(sign*int(num*127.0),127)
                                cell = cell[ct:]
                            else:
                                if cell and cell[0]=='|':
                                    cell = cell[1:]
                                vel = min(127,int(ch.vel + 0.5*(127.0-ch.vel)))
                            ch.pitch(vel)
                        # VIBRATO
                        elif c == '~':
                            ch.mod(127) # TODO: pitch osc in the future
                            cell = cell[1:]
                        # MOD WHEEL
                        # elif c == '`': # mod wheel -- moved to CC
                        #     ch.mod(127)
                        #     cell = cell[1:]
                        # MUTE SUSTAIN
                        elif cell.startswith('--'):
                            num, ct = count_seq('-')
                            sustain = ch.sustain = False
                            cell = cell[ct:]
                        # STOP/PANIC
                        elif cell.startswith('='):
                            num, ct = count_seq('=')
                            if num==2:
                                ch.stop()
                            elif num==3:
                                ch.panic()
                            if num<=3:
                                sustain = ch.sustain = False
                            cell = cell[ct:]
                        # SUSTAIN HOLD
                        elif c2=='__':
                            sustain = ch.sustain = True
                            ch.arp_sustain = True
                            cell = cell[2:]
                        # [DEPRECATED] STOP SUSTAIN
                        elif c2=='_-':
                            sustain = False
                            cell = cell[2:]
                        # SUSTAIN
                        elif c=='_':
                            ch.arp_sustain = True
                            sustain = True
                            cell = cell[1:]
                        # elif c=='v': # volume - moved to CC
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
                        #     vel = int((float(num) / float('9'*len(num)))*127)
                        #     ch.cc(7,vel)
                        # RECORD SEQ
                        # elif cell.startswith('^^'):
                        elif c2=='^^':
                            cell = cell[2:]
                            r,ct = peel_uint(cell,0)
                            ch.record(r)
                            cell = cell[ct:]
                        # REPLAY SEQ
                        elif c=='^':
                        # elif cell.startswith('^'):
                            cell = cell[1:]
                            r,ct = peel_uint(cell,0)
                            if self.showtext:
                                showtext.append('play sequence: ' + num)
                            ch.replay(r)
                            cell = cell[ct:]
                        # MIDI CHANNEl
                        elif c2=='ch':
                            num,ct = peel_uint(cell[1:])
                            cell = cell[1+ct:]
                            if self.showtext:
                                showtext.append('midi channel: ' + num) 
                            ch.midi_channel(num)
                        # SCALE
                        elif c=='s':
                            # solo if used by itself (?)
                            # scale if given args
                            # ch.soloed = True
                            cell = cell[1:]
                        # MUTE
                        elif c=='m':
                            ch.enable(c=='m')
                            cell = cell[1:]
                        # MIDI CC
                        elif c=='c': # MIDI CC
                            # get number
                            cell = cell[1:]
                            cc,ct = peel_int(cell)
                            assert ct
                            cell = cell[ct+1:]
                            ccval,ct = peel_int(cell)
                            assert ct
                            if not ct:
                                error('cc requires value')
                                cell = []
                            cell = cell[ct:]
                            ccval = int(num)
                            ch.cc(cc,ccval)
                        # PROGRAM/PATCH CHANGE
                        elif c=='p':
                            # bank select as other args?
                            cell = cell[1:]
                            p,ct = peel_uint(cell)
                            if not ct:
                                error('p command requires number')
                                cell = []
                            cell = cell[ct:]
                            ch.patch(p)
                        # BANK SELECT
                        elif c2=='bs': 
                            cell = cell[2:]
                            num,ct = peel_uint(cell)
                            cell = cell[ct:]
                            b = num
                            if cell and cell[0]==':':
                                cell = cell[1:]
                                num2,ct = peel_uint(cell)
                                if not ct:
                                    error(': params require number')
                                    cell = []
                                cell = cell[ct:]
                                b = num2 # second val -> lsb
                                b |= num << 8 # first value -> msb
                            ch.bank(b)
                        # NOTE LENGTH
                        elif c=='*':
                            dots = count_seq(cell)
                            if notes:
                                notevalue = '*' * dots
                                cell = cell[dots:]
                                num,ct = peel_uint_s(cell)
                                if ct:
                                    num = float('0.'+num)
                                    cell = cell[ct:]
                                else:
                                    num = 1.0
                                if dots==1:
                                    duration = num
                                    events.append(Event(num, lambda _: ch.release_all(), ch))
                                else:
                                    duration = num*pow(2.0,float(dots-1))
                                    events.append(Event(num*pow(2.0,float(dots-1)), lambda _: ch.release_all(), ch))
                            else:
                                cell = cell[dots:]
                            if self.showtext:
                                showtext.append('duration(*)')
                        # PLACEHOLDER
                        elif c=='.':
                            dots = count_seq(cell)
                            if len(c)>1 and notes:
                                cell = cell[dots:]
                                if ch.arp_enabled:
                                    dots -= 1
                                notevalue = '.' * dots
                                if dots:
                                    num,ct = peel_uint_s(cell)
                                    if ct:
                                        num = int('0.' + num)
                                        cell = cell[ct:]
                                    else:
                                        num = 1.0
                                    duration = num*pow(0.5,float(dots))
                                    events.append(Event(num*pow(0.5,float(dots)), lambda _: ch.release_all(), ch))
                            else:
                                cell = cell[dots:]
                            if self.showtext:
                                showtext.append('shorten(.)')
                        # NOTE TIME SHIFT
                        elif c=='(' or c==')': # note shift (early/delay)
                            num = ''
                            cell = cell[1:]
                            s,ct = peel_uint(cell, 5)
                            if ct:
                                cell = cell[ct:]
                            delay = -1*(c=='(')*float('0.'+num) if num else 0.5
                            if delay < 0.0:
                                error('delay >= 0')
                                cell = []
                                continue
                        # MARKER (ignore -- already parsed)
                        elif c=='|':
                            cell = []
                        # MARKER (ignore -- already parsed)
                        elif c==':':
                            cell = []
                        # FULL ACCENT
                        elif c2=='!!':
                            accent = '!!'
                            cell = cell[2:]
                            vel,ct = peel_uint_s(cell,127)
                            if ct:
                                cell = cell[ct:]
                                ch.vel = vel # persist if numbered
                            else:
                                if ch.max_vel >= 0:
                                    vel = ch.max_vel
                                else:
                                    vel = 127
                            if self.showtext:
                                showtext.append('accent(!!)')
                        # ACCENT
                        elif c=='!':
                            accent = '!'
                            cell = cell[1:]
                            # num,ct = peel_uint_s(cell)
                            # if ct:
                            #     vel = constrain(int(float('0.'+num)*127.0),127)
                            #     cell = cell[ct:]
                            # else:
                            if ch.accent_vel >= 0:
                                vel = ch.accent_vel
                            else:
                                vel = constrain(int(ch.vel + 0.5*(127.0-ch.vel)),127)
                            if self.showtext:
                                showtext.append('accent(!)')
                        # GHOST NOTE
                        elif c2=='??':
                            accent = '??'
                            if ch.ghost_vel >= 0:
                                vel = ch.ghost_vel
                            else:
                                vel = max(0,int(ch.vel*0.25)) 
                            cell = cell[2:]
                            if self.showtext:
                                showtext.append('soften(??)')
                        # SOFT NOTE
                        elif c=='?':
                            accent = '?'
                            if ch.soft_vel >= 0:
                                vel = ch.soft_vel
                            else:
                                vel = max(0,int(ch.vel*0.5))
                            cell = cell[1:]
                            if self.showtext:
                                showtext.append('soften(?)')
                        # elif cell.startswith('$$') or (c=='$' and lennotes==1):
                        # STRUM/SPREAD/TREMOLO
                        elif c=='$':
                            sq = count_seq(cell)
                            cell = cell[sq:]
                            num,ct = peel_uint_s(cell,'0')
                            if ct:
                                cell = cell[ct:]
                            num = float('0.'+num)
                            strum = 1.0
                            if len(notes)==1: # tremolo
                                notes = notes * 2
                                # notes = [notes[i:i + sq] for i in range(0, len(notes), sq)]
                            # log('strum')
                            if spacer:
                                ch.soft_vel = vel 
                            if self.showtext:
                                showtext.append('strum($)')
                        # ARPEGGIO
                        elif c=='&':
                            count = count_seq(cell)
                            arpcount,ct = peel_uint(cell[count:],0)
                                # notes = list(itertools.chain.from_iterable(itertools.repeat(\
                                #     x, count) for x in notes\
                                # ))
                            cell = cell[ct+count:]
                            if count==2: arpreverse = True
                            if not notes:
                                # & restarts arp (if no note)
                                ch.arp_restart()
                                # ch.arp_sustain = sustain
                            else:
                                arpnotes = True
                                arppattern = []
                                while True:
                                    if not (not arppattern and cell.startswith(':')) or\
                                        (arppattern and cell.startswith('|')):
                                        break
                                    out(cell[1:])
                                    num,ct = peel_int(cell[1:],1)
                                    if not ct:
                                        break
                                    arppattern += [num]
                                    cell = cell[1+ct:]
                            if self.showtext:
                                showtext.append('arpeggio(&)')
                        # TUPLETS
                        elif c=='t':
                            tuplets = True
                            tups = count_seq(cell,'t')
                            Tups = count_seq(cell[tups:],'T')
                            cell = cell[tups+Tups:]
                            if not ch.tuplets:
                                ch.tuplets = True
                                pow2i = 0.0
                                num,ct = peel_uint(cell,'3')
                                cell = cell[ct:]
                                ct2=0
                                denom = 0
                                if cell and cell[0]==':':
                                    denom,ct2 = peel_float(cell[1:])
                                    cell = cell[1+ct2:]
                                if not ct2:
                                    for i in itertools.count():
                                        denom = 1 << i
                                        if denom > num:
                                            break
                                # out('denom' + str(denom))
                                # out('num ' + str(num))
                                ch.note_spacing = denom/float(num) # !
                                ch.tuplet_count = int(num)
                                ch.tuplet_offset = 0.0
                        # elif c==':':
                        #     if not notes:
                        #         cell = []
                        #         continue # ignore marker
                        # GLOABL VARS (ignore -- already parsed)
                        elif c=='%':
                            # ctrl line
                            cell = []
                            break
                        # MIDI CC
                        elif c2 in CC:
                            cell = cell[2:]
                            num,ct = peel_uint_s(cell)
                            if ct:
                                num = float('0.'+num) 
                                cell = cell[ct:] 
                            else:
                                if cell and cell[0]=='!':
                                    cell = cell[1:]
                                num = 1.0
                            ch.cc(CC[c2],constrain(int(num*127.0),127))
                        # PERSISTENT VELOCITY
                        elif c in '0123456789':
                            # set persistent track velocity for accent level
                            num,ct = peel_uint(cell)
                            cell = cell[ct:]
                            if accent=='?':
                                ch.soft_vel = num
                            elif accent=='??':
                                ch.ghost_vel = num
                            elif accent=='!':
                                ch.vel = num
                            elif accent=='!!':
                                ch.max_vel = num
                            else:
                                ch.vel = num
                            vel = num 
                        # MIDI CC
                        elif c in CC:
                            cell = cell[1:]
                            num,ct = peel_uint_s(cell)
                            if ct:
                                num = float('0.'+num)
                                cell = cell[ct:]
                            else:
                                num = 1.0
                            ch.cc(CC[c],constrain(int(num*127.0),127))
                        # PARSE ERROR
                        else:
                            # if self.cmdmode in 'cl':
                            log(FG.BLUE + self.line)
                            indent = ' ' * (len(fullcell)-len(cell))
                            log(FG.RED + indent +  "^ Unexpected " + cell[0] + " here")
                            cell = []
                            ignore = True
                            break
                        
                        # elif c=='/': # bend in
                        # elif c=='\\': # bend down
                    
                    base =  (OCTAVE_BASE+octave) * 12 - 1 + self.transpose + ch.transpose
                    p = base
                    
                    if arpnotes:
                        ch.arp(notes, arpcount, sustain, arppattern, arpreverse, octave)
                        arpnext = ch.arp_next(self.shell or self.cmdmode in 'lc')
                        notes = [ch.arp_note - (octave*12)] # [HACK] first note already has frame octave offset above
                        delay = ch.arp_delay
                        # if not fcmp(delay):
                        #     pass
                            # schedule=True

                    if notes and not tuplets and not sustain:
                        ch.release_all()

                    for ev in events:
                        self.schedule.add(ev)
                    events = []
                    
                    delta = 0 # how much to separate notes
                    if strum < -EPSILON:
                        notes = notes[::-1] # reverse
                        strum -= strum
                    if strum > EPSILON:
                        ln = len(notes)
                        delta = (1.0/(ln*forr(duration,1.0))) # t between notes

                    if self.showtext:
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

                    if not tuplets:
                        ch.tuplet_stop();
                    delay += ch.tuplet_next()
                    
                    i = 0
                    for n in notes:
                        # if no schedule, play note immediately
                        # also if scheduled, play first note of strum if there's no delay
                        if fzero(delay):
                        # if not schedule or (i==0 and strum>=EPSILON and delay<EPSILON):
                            ch.note_on(p + n, vel, sustain)
                        else:
                            # schedule note to occur later
                            f = lambda _, p=p,n=n,s=sustain,v=vel: \
                                ch.note_on(p + n, v, s)
                            self.schedule.add(Event(delay,f,ch))
                        delay += delta
                        i += 1
                    
                    cell_idx += 1
         
                while True:
                    try:
                        # don't delay on ctrl lines or file header
                        if not ctrl and not self.header:
                            await self.schedule.logic(60.0 / self.tempo / self.grid)
                            break
                        else:
                            break
                    except KeyboardInterrupt:
                        if self.shell or not self.pause():
                            self.quitflag = True
                            break
                    except SignalError:
                        if self.shell or not self.pause():
                            self.quitflag = True
                            break
                    except:
                        raise
                        # log(FG.RED + traceback.format_exc())
                        # if self.shell or self.pause():
                        #     self.quitflag = True
                        #     break

                if self.quitflag:
                    break
                 
            except KeyboardInterrupt:
                if self.shell or not self.pause():
                    self.quitflag = True
                    break
            except SignalError:
                if self.shell or not self.pause():
                    self.quitflag = True
                    break
            except:
                log(FG.RED + traceback.format_exc())
                self.quitflag = True
                break

            self.row += 1

    async def next_row(self, prompt_session:PromptSession) -> LoopResult:
        try:
            self.line = self.buf[self.row]
            if self.row == self.startrow:
                self.startrow = -1
            if self.stoprow!=-1 and self.row == self.stoprow:
                self.buf = []
                raise IndexError
            return LoopResult.PROCEED
        except IndexError:
            if self.has_flags(Player.Flag.LOOP):
                self.row = 0
                return LoopResult.CONTINUE
            
            self.row = len(self.buf)
            # done with file, finish playing some stuff
            
            arps_remaining = 0
            if self.interactive or self.cmdmode in ['c','l']: # finish arps in shell mode
                for ch in self.tracks[:self.tracks_active]:
                    if ch.arp_enabled:
                        if ch.arp_cycle_limit or not ch.arp_once:
                            arps_remaining += 1
                            self.line = '.'
                if not arps_remaining and not self.shell and self.cmdmode not in ['c','l']:
                    return LoopResult.BREAK
                self.line = '.'
            
            if not arps_remaining and not self.schedule.pending():
                if self.interactive:
                    for ch in self.tracks[:self.tracks_active]:
                        ch.release_all()
                    
                    if self.shell:
                        self.buf += await self.mk_prompt(prompt_session)
                    # elif self.remote:
                    #     pass # not yet implemented
                    else:
                       assert False
                    return LoopResult.CONTINUE
                
                else:
                    return LoopResult.BREAK
            return LoopResult.PROCEED

    async def mk_prompt(self, prompt_session:PromptSession):
        """Creates a new prompt for the current line"""
        # self.shell PROMPT
        # log(orr(self.tracks[0].scale,self.scale).mode_name(orr(self.tracks[0].mode,self.mode)))
        # cur_oct = self.tracks[0].octave
        # cline = FG.GREEN + 'txbt> '+FG.BLUE+ '('+str(int(self.tempo))+'bpm x'+str(int(self.grid))+' '+\
        #     note_name(self.tracks[0].transpose) + ' ' +\
        #     orr(self.tracks[0].scale,self.scale).mode_name(orr(self.tracks[0].mode,self.mode,-1))+\
        #     ')> '
        modename = orr(self.tracks[0].scale,self.scale).mode_name(orr(self.tracks[0].mode,self.mode,-1))
                        
        keynote = note_name(self.transpose + self.tracks[0].transpose)
        keynote = keynote if keynote!='C' else ''
        parts = [
            str(int(self.tempo))+'bpm', # tempo
            'x'+str(int(self.grid)), # subdiv
            keynote,
            ('' if modename=='ionian' else modename)
        ]
        cline = 'txbt> ('+ \
            ' '.join(filter(lambda x: x, parts))+ \
            ')> '
        # if bufline.endswith('.txbt'):
            # play file?
        # bufline = raw_input(cline)
        bufline = await prompt_session.prompt_async(cline)
        bufline = list(filter(None, bufline.split(' ')))
        bufline = list(map(lambda b: b.replace(';',' '), bufline))
        
        return bufline
