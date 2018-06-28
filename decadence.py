#!/usr/bin/python
"""decadence
Copyright (c) 2018 Grady O'Connell
Open-source under MIT License

Examples:
    decadence.py          shell
    decadence.py song.dc  play song

Usage:
    decadence.py [--ring | --follow | --csound | --sonic-pi] [-eftnpsrxh] [SONGNAME]
    decadence.py [+RANGE] [--ring || --follow | --csound | --sonic-pi] [-eftnpsrxh] [SONGNAME]
    decadence.py -c [COMMANDS ...]
    decadence.py -l [LINE_CONTENT ...]

Options:
    -h --help             show this
    -v --verbose          verbose
    -t --tempo=<bpm>      (STUB) set tempo
    -x --grid=<g>         (STUB) set grid
    -n --note=<n>         (STUB) set grid using note value
    -s --speed=<s>        (STUB) playback speed
    --dev=<device>        output device, partial match
    -p --patch=<patch>    (STUB) default midi patch, partial match
    -c                    execute commands sequentially
    -l                    execute commands simultaenously
    -r --remote           (STUB) remote, keep alive as daemon
    --ring                don't mute midi on end
    +<range>              play from line or maker, for range use start:end
    -e --edit             (STUB) open file in editor
    --vi                  (STUB) shell vi mode
    -h --transpose        transpose (in half steps)
    --sustain             sustain by default
    --numbers             use note numbers in output
    --notenames           use note names in output
    --flats               prefer flats in output
    --sharps              prefer sharps in output
    --lint                (STUB) analyze file
    --follow              (old) print newlines every line, no output
    --quiet               no output
    --csound              (STUB) enable csound
    --sonic-pi            (STUB) enable sonic-pi
"""
from __future__ import unicode_literals, print_function, generators
from src import *
if __name__!='__main__':
    sys.exit(0)
ARGS = docopt(__doc__)
set_args(ARGS)

from src.support import *

style = style_from_dict({
    Token:          '#ff0066',
    Token.DC:       '#00aa00',
    Token.Info:     '#000088',
})
colorama.init(autoreset=True)

# logging.basicConfig(filename=LOG_FN,level=logging.DEBUG)

dc = Context()

# class Marker:
#     def __init__(self,name,row):
#         self.name = name
#         self.line = row

for arg,val in iteritems(ARGS):
    if val:
        if arg == '--tempo': dc.tempo = float(val)
        elif arg == '--grid': dc.grid = float(val)
        elif arg == '--note': dc.grid = float(val)/4.0
        elif arg == '--speed': dc.speed = float(val)
        elif arg == '--verbose': dc.showtext = True
        elif arg == '--dev': dc.portname = val
        elif arg == '--vi': dc.vimode = True
        elif arg == '--patch':
            vals = val.split(',')
            for i in range(len(vals)):
                val = vals[i]
                if val.isdigit():
                    dc.tracks[i].patch(int(val))
                else:
                    dc.tracks[i].patch(val)
        elif arg == '--sustain': dc.sustain=True
        elif arg == '--ring': dc.ring=True
        elif arg == '--remote': dc.remote = True
        elif arg == '--lint': LINT = True
        elif arg == '--quiet': set_print(False)
        elif arg == '--follow':
            set_print(False)
            dc.canfollow = True
        elif arg == '--flats': FLATS = True
        elif arg == '--sharps': SHARPS= True
        elif arg == '--edit': pass
        elif arg == '-l' and val: dc.dcmode = 'l'
        elif arg == '-c' and val: dc.dcmode = 'c'

if dc.dcmode=='l':
    dc.buf = ' '.join(ARGS['LINE_CONTENT']).split(';') # ;
elif dc.dcmode=='c':
    dc.buf = ' '.join(ARGS['COMMANDS']).split(' ') # spaces
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
                        if not bm in dc.markers:
                            dc.markers[bm] = lc
                    elif ls.startswith('|') and ls.endswith(':'):
                        bm = ls[1:-1]
                        # only store INITIAL marker positions
                        if not bm in dc.markers:
                            dc.markers[bm] = lc

                lc += 1
                dc.buf += [line]
            dc.shell = False
    else:
        if dc.dcmode == 'n':
            dc.dcmode = ''
        dc.shell = True

dc.interactive = dc.shell or dc.remote

pygame.midi.init()
if pygame.midi.get_count()==0:
    print('No midi devices found.')
    sys.exit(1)    
dev = -1
for i in range(pygame.midi.get_count()):
    port = pygame.midi.get_device_info(i)
    portname = port[1].decode('utf-8')
    # timidity
    # print(portname)
    devs = [
        'timidity port 0',
        'synth input port',
        'loopmidi'
        # helm will autoconnect
    ]
    if dc.portname:
        if portname.lower().startswith(dc.portname.lower()):
            dc.portname = portname
            dev = i
            break
    for name in devs:
        if portname.lower().startswith(name):
            dc.portname = portname
            dev = i
            break

# dc.player = pygame.midi.Output(pygame.midi.get_default_output_id())

dc.player = pygame.midi.Output(dev)
dc.instrument = 0
dc.player.set_instrument(0)
mch = 0
for i in range(NUM_CHANNELS_PER_DEVICE):
    # log("%s -> %s" % (i,mch))
    dc.tracks.append(Track(dc, i, mch, dc.player, dc.schedule))
    mch += 2 if i==DRUM_CHANNEL else 1

if dc.sustain:
    dc.tracks[0].sustain = dc.sustain

# show nice output in certain modes
if dc.shell or dc.dcmode in 'cl':
    dc.showtext = True

for i in range(len(sys.argv)):
    arg = sys.argv[i]
    
    # play range (+ param, comma-separated start and end)
    if arg.startswith('+'):
        vals = arg[1:].split(',')
        try:
            dc.row = int(vals[0])
        except ValueError:
            try:
                dc.row = dc.markers[vals[0]]
            except KeyError:
                log('invalid entry point')
                dc.quitflag = True
        try:
            dc.stoprow = int(vals[1])
        except ValueError:
            try:
                # we cannot cut buf now, since seq might be non-linear
                dc.stoprow = dc.markers[vals[0]]
            except KeyError:
                log('invalid stop point')
                dc.quitflag = True
        except IndexError:
            pass # no stop param

if dc.shell:
    log(FG.BLUE + 'decadence')# v'+str(VERSION))
    log('Copyright (c) 2018 Grady O\'Connell')
    log('https://github.com/flipcoder/decadence')
    active = SUPPORT_ALL & SUPPORT
    inactive = SUPPORT_ALL - SUPPORT
    if active:
        log(FG.GREEN + 'Active Modules: ' + FG.WHITE +  ', '.join(active) + FG.WHITE)
    if inactive:
        log(FG.RED + 'Inactive Modules: ' +  FG.WHITE + ', '.join(inactive))
    if dc.portname:
        log(FG.GREEN + 'Device: ' + FG.WHITE + '%s' % (dc.portname if dc.portname else 'Unknown',))
        if dc.tracks[0].midich == DRUM_CHANNEL:
            log(FG.GREEN + 'GM Percussion')
        else:
            log(FG.GREEN + 'GM Patch: '+ FG.WHITE +'%s' % GM[dc.tracks[0].patch_num])
    log('Use -h for command line options.')
    log('Read the manual and look at examples. Have fun!')
    log('')

header = True # set this to false as we reached cell data
while not dc.quitflag:
    try:
        dc.line = '.'
        try:
            dc.line = dc.buf[dc.row]
            if dc.stoprow!=-1 and dc.row == dc.stoprow:
                dc.buf = []
                raise IndexError
        except IndexError:
            dc.row = len(dc.buf)
            # done with file, finish playing some stuff
            
            arps_remaining = 0
            if dc.interactive or dc.dcmode in ['c','l']: # finish arps in shell mode
                for ch in dc.tracks[:dc.tracks_active]:
                    if ch.arp_enabled:
                        if ch.arp_cycle_limit or not ch.arp_once:
                            arps_remaining += 1
                            dc.line = '.'
                if not arps_remaining and not dc.shell and dc.dcmode not in ['c','l']:
                    break
                dc.line = '.'
            
            if not arps_remaining and not dc.schedule.pending():
                if dc.interactive:
                    for ch in dc.tracks[:dc.tracks_active]:
                        ch.release_all()
                    
                    if dc.shell:
                        # dc.shell PROMPT
                        # log(orr(dc.tracks[0].scale,dc.scale).mode_name(orr(dc.tracks[0].mode,dc.mode)))
                        cur_oct = dc.tracks[0].octave
                        # cline = FG.GREEN + 'DC> '+FG.BLUE+ '('+str(int(dc.tempo))+'bpm x'+str(int(dc.grid))+' '+\
                        #     note_name(dc.tracks[0].transpose) + ' ' +\
                        #     orr(dc.tracks[0].scale,dc.scale).mode_name(orr(dc.tracks[0].mode,dc.mode,-1))+\
                        #     ')> '
                        cline = 'DC> ('+str(int(dc.tempo))+'bpm x'+str(int(dc.grid))+' '+\
                            note_name(dc.transpose + dc.tracks[0].transpose) + ' ' +\
                            orr(dc.tracks[0].scale,dc.scale).mode_name(orr(dc.tracks[0].mode,dc.mode,-1))+\
                            ')> '
                        # if bufline.endswith('.dc'):
                            # play file?
                        # bufline = raw_input(cline)
                        bufline = prompt(cline, history=HISTORY, vi_mode=dc.vimode)
                        bufline = list(filter(None, bufline.split(' ')))
                        bufline = list(map(lambda b: b.replace(';',' '), bufline))
                    elif dc.remote:
                        pass
                    else:
                        assert False
                        
                    dc.buf += bufline
                    
                    continue
                
                else:
                    break
            
        log(FG.MAGENTA + dc.line)
        
        # cells = line.split(' '*2)
        
        # if line.startswith('|'):
        #     dc.separators = [] # clear
        #     # column setup!
        #     for i in range(1,len(line)):
        #         if line[i]=='|':
        #             dc.separators.append(i)
        
        # log(BG.RED + line)
        fullline = dc.line[:]
        dc.line = dc.line.strip()
        
        # LINE COMMANDS
        ctrl = False
        cells = []

        if dc.line:
            # COMMENTS (;)
            if dc.line[0] == ';':
                dc.follow(1)
                dc.row += 1
                continue
            
            # set marker
            if dc.line[-1]==':': # suffix marker
                # allow override of markers in case of reuse
                dc.markers[dc.line[:-1]] = dc.row
                dc.follow(1)
                dc.row += 1
                continue
                # continue
            elif dc.line[0]==':': #prefix marker
                # allow override of markers in case of reuse
                dc.markers[dc.line[1:]] = dc.row
                dc.follow(1)
                dc.row += 1
                continue
            
            # TODO: global 'silent' commands (doesn't take time)
            if dc.line.startswith('%'):
                dc.line = dc.line[1:].strip() # remove % and spaces
                for tok in dc.line.split(' '):
                    if not tok:
                        break
                    if tok[0]==' ':
                        tok = tok[1:]
                    var = tok[0].upper()
                    if var in 'TGNPSRMCXK':
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
                            if var=='G': dc.grid/=float(val)
                            elif var=='X': dc.grid/=float(val)
                            elif var=='N': dc.grid/=float(val) #!
                            elif var=='T': dc.tempo/=float(val)
                        elif op=='*':
                            if var=='G': dc.grid*=float(val)
                            elif var=='X': dc.grid*=float(val)
                            elif var=='N': dc.grid*=float(val) #!
                            elif var=='T': dc.tempo*=float(val)
                        elif op=='=':
                            if var=='G': dc.grid=float(val)
                            elif var=='X': dc.grid=float(val)
                            elif var=='N': dc.grid=float(val)/4.0 #!
                            elif var=='T':
                                vals = val.split('x')
                                dc.tempo=float(vals[0])
                                try:
                                    dc.grid = float(vals[1])
                                except:
                                    pass
                            elif var=='C':
                                vals = val.split(',')
                                dc.columns = int(vals[0])
                                try:
                                    dc.column_shift = int(vals[1])
                                except:
                                    pass
                            elif var=='P':
                                vals = val.split(',')
                                for i in range(len(vals)):
                                    p = vals[i]
                                    if p.strip().isdigit():
                                        dc.tracks[i].patch(int(p))
                                    else:
                                        dc.tracks[i].patch(p)
                            elif var=='F': # flags
                                for i in range(len(vals)):
                                    dc.tracks[i].add_flags(val.split(','))
                            elif var=='K':
                                dc.transpose = int(val)
                                # for ch in TRACKS:
                                #     ch.transpose = int(val)
                            elif var=='R' or var=='S':
                                try:
                                    if val:
                                        val = val.lower()
                                        # ambigous alts
                                        
                                        if val.isdigit():
                                            modescale = (dc.scale.name,int(val))
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
                                            dc.scale = SCALES[modescale[0]]
                                            dc.mode = modescale[1]
                                            inter = dc.scale.intervals
                                            dc.transpose = 0
                                            # log(dc.mode-1)
                                            
                                            if var=='R':
                                                for i in range(dc.mode-1):
                                                    inc = 0
                                                    try:
                                                        inc = int(inter[i])
                                                    except ValueError:
                                                        pass
                                                    dc.transpose += inc
                                            elif var=='S':
                                                pass
                                        except ValueError:
                                            raise NoSuchScale()
                                    else:
                                        dc.transpose = 0
                                
                                except NoSuchScale:
                                    print(FG.RED + 'No such scale.')
                                    pass
                                    
                dc.follow(1)
                dc.row += 1
                continue
            
            # jumps
            if dc.line.startswith(':') and dc.line.endswith("|"):
                jumpline = dc.line[1:-1]
            else:
                jumpline = dc.line[1:]
            if dc.line[0]=='@':
                if len(jumpline)==0:
                    dc.row = 0
                    continue
                if len(jumpline)>=1 and jumpline == '@': # @@ return/pop callstack
                    frame = CALLSTACK[-1]
                    CALLSTACK = CALLSTACK[:-1]
                    dc.row = frame.row
                    continue
                jumpline = jumpline.split('*') # * repeats
                bm = jumpline[0] # marker name
                count = 0
                if len(jumpline)>=1:
                    count = int(jumpline) if len(jumpline)>=1 else 1
                frame = CALLSTACK[-1]
                frame.count = count
                if count: # repeats remaining
                    CALLSTACK.append(StackFrame(dc.row))
                    dc.row = dc.markers[bm]
                    continue
                else:
                    dc.row = dc.markers[bm]
                    continue
            
        
        # this is not indented in blank lines because even blank lines have this logic
        gutter = ''
        if dc.shell:
            cells = list(filter(None,dc.line.split(' ')))
        elif dc.columns:
            cells = fullline
            # shift column pos right if any
            cells = ' ' * max(0,-dc.column_shift) + cells
            # shift columns right, creating left-hand gutter
            # cells = cells[-1*min(0,dc.column_shift):] # create gutter (if negative shift)
            # separate into chunks based on column width
            cells = [cells[i:i + dc.columns] for i in range(0, len(cells), dc.columns)]
            # log(cells)
        elif not dc.separators:
            # AUTOGENERATE CELL dc.separators
            cells = fullline.split(' ')
            pos = 0
            for cell in cells:
                if cell:
                    if pos:
                        dc.separators.append(pos)
                    # log(cell)
                pos += len(cell) + 1
            # log( "dc.separators " + str(dc.separators))
            cells = list(filter(None,cells))
            # if fullline.startswith(' '):
            #     cells = ['.'] + cells # dont filter first one
            autoseparate = True
        else:
            # SPLIT BASED ON dc.separators
            s = 0
            seplen = len(dc.separators)
            # log(seplen)
            pos = 0
            for i in range(seplen):
                cells.append(fullline[pos:dc.separators[i]].strip())
                pos = dc.separators[i]
            lastcell = fullline[pos:].strip()
            if lastcell: cells.append(lastcell)
        
        # make sure active tracks get empty cell
        len_cells = len(cells)
        if len_cells > dc.tracks_active:
            dc.tracks_active = len_cells
        else:
            # add empty cells for active tracks to the right
            cells += ['.'] * (len_cells - dc.tracks_active)
        del len_cells
        
        cell_idx = 0
        
        # CELL LOGIC
        for cell in cells:
            
            cell = cells[cell_idx]
            ch = dc.tracks[cell_idx]
            fullcell = cell[:]
            ignore = False
            
            # if dc.instrument != ch.instrument:
            #     dc.player.set_instrument(ch.instrument)
            #     dc.instrument = ch.instrument

            cell = cell.strip()
            if cell:
                header = False
            
            if cell.count('\"') == 1: # " is recall, but multiple " means speak
                cell = cell.replace("\"", dc.track_history[cell_idx])
            else:
                dc.track_history[cell_idx] = cell
            
            fullcell_sub = cell[:]
            
            # empty
            # if not cell:
            #     cell_idx += 1
            #     continue

            if cell and cell[0]=='-':
                if dc.shell:
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
 
            notecount = len(ch.scale.intervals if ch.scale else dc.scale.intervals)
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
                    for amb in ('ion','dor','dom','alt','dou'): # I dim or D dim conflict w/ ionian and dorian
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
                                m = orr(ch.mode,dc.mode,-1)-1
                                steps = orr(ch.scale,dc.scale).intervals
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
                            # addhigherroot = False
                            
                            # cut chord name from text after it
                            for char in tok:
                                if cut==0 and char in CCHAR_START:
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
                            if 'add' in chordname:
                                # print(chordname)
                                addtoks = chordname.split('add')
                                # print(addtoks)
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

            # if frets:
            #     ch.strings = notes
            #     notes = []

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
                    # dc.track_history[cell_idx] = fullcell_sub
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
                # dc.sustain
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
                    if dc.showtext:
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
                    if dc.showtext:
                        showtext.append('duration(*)')
                elif c=='.':
                    dots = count_seq(cell)
                    if len(c)>1 and notes:
                        notevalue = '.' * dots
                        cell = cell[dots:]
                        if ch.arp_enabled:
                            dots -= 1
                        if dots:
                            num,ct = peel_uint_s(cell)
                            if ct:
                                num = int('0.' + num)
                            else:
                                num = 1.0
                            cell = cell[ct:]
                            duration = num*pow(0.5,float(dots))
                            events.append(Event(num*pow(0.5,float(dots)), lambda _: ch.release_all(), ch))
                    else:
                        cell = cell[dots:]
                    if dc.showtext:
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
                elif c2=='!!': # full accent
                    vel,ct = peel_uint_s(cell[1:],127)
                    cell = cell[2+ct:]
                    if ct>2:
                        ch.vel = vel # persist if numbered
                    else:
                        if ch.max_vel >= 0:
                            vel = ch.max_vel
                        else:
                            vel = 127
                    if dc.showtext:
                        showtext.append('accent(!!)')
                elif c=='!': # accent
                    curv = ch.vel
                    num,ct = peel_uint_s(cell[1:])
                    if ct:
                        vel = min(127,int(float('0.'+num)*127.0))
                    else:
                        if ch.accent_vel >= 0:
                            vel = ch.accent_vel
                        else:
                            vel = min(127,int(curv + 0.5*(127.0-curv)))
                    cell = cell[ct+1:]
                    if dc.showtext:
                        showtext.append('accent(!!)')
                elif c2=='??': # ghost
                    if ch.ghost_vel >= 0:
                        vel = ch.ghost_vel # max(0,int(ch.vel*0.25))
                    else:
                        vel = 1
                    cell = cell[2:]
                    if dc.showtext:
                        showtext.append('soften(??)')
                elif c=='?': # soft
                    if ch.soft_vel >= 0:
                        vel = ch.soft_vel
                    else:
                        vel = max(0,int(ch.vel*0.5))
                    cell = cell[1:]
                    if dc.showtext:
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
                        notes = notes * 2
                        # notes = [notes[i:i + sq] for i in range(0, len(notes), sq)]
                    # log('strum')
                    if dc.showtext:
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
                    if dc.showtext:
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
                    if dc.dcmode in 'cl':
                        log(FG.BLUE + dc.line)
                    indent = ' ' * (len(fullcell)-len(cell))
                    log(FG.RED + indent +  "^ Unexpected " + cell[0] + " here")
                    cell = []
                    ignore = True
                    break
                
                # elif c=='/': # bend in
                # elif c=='\\': # bend down
            
            base =  (OCTAVE_BASE+octave) * 12 - 1 + dc.transpose + ch.transpose
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
                dc.schedule.add(ev)
            
            delta = 0 # how much to separate notes
            if strum < -EPSILON:
                notes = notes[::-1] # reverse
                strum -= strum
            if strum > EPSILON:
                ln = len(notes)
                delta = (1.0/(ln*forr(duration,1.0))) #t between notes

            if dc.showtext:
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
                    dc.schedule.add(Event(delay,f,ch))
                delay += delta
                i += 1
            
            cell_idx += 1

        while True:
            try:
                if not ctrl and not header:
                    dc.schedule.logic(60.0 / dc.tempo / dc.grid)
                    break
                else:
                    break
            except KeyboardInterrupt:
                # log(FG.RED + traceback.format_exc())
                dc.quitflag = True
                break
            except:
                log(FG.RED + traceback.format_exc())
                if dc.shell:
                    dc.quitflag = True
                    break
                if not dc.shell and not dc.pause():
                    dc.quitflag = True
                    break

        if dc.quitflag:
            break
         
    except KeyboardInterrupt:
        dc.quitflag = True
        break
    except SignalError:
        dc.quitflag = True
        break
    except:
        log(FG.RED + traceback.format_exc())
        if dc.shell:
            dc.quitflag = True
            break
        if not dc.shell and not dc.pause():
            break

    dc.follow(1)
    dc.row += 1

# TODO: turn all midi note off
i = 0
for ch in dc.tracks:
    if not dc.ring:
        ch.panic()
    ch.player = None

del dc.player
pygame.midi.quit()

# def main():
#     pass
    
# if __name__=='__main__':
#     curses.wrapper(main)

support_stop()

