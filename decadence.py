#!/usr/bin/python
"""decadence
Copyright (c) 2018 Grady O'Connell
Open-source under MIT License

Examples:
    decadence.py          shell
    decadence.py song.dc  play song

Usage:
    decadence.py [--dev=<device> | --verbose | --midi=<fn> | --ring | --follow | --loop] [-eftnpsrxhv] [SONGNAME]
    decadence.py [+RANGE] [--dev=<device> | --midi=<fn> | --ring | --follow | --loop] [-eftnpsrxhv] [SONGNAME]
    decadence.py -c [COMMANDS ...]
    decadence.py -l [LINE_CONTENT ...]

Options:
    -h --help             show this
    -v --verbose          verbose
    -t --tempo=<bpm>      (STUB) set tempo [default: 120]
    -x --grid=<g>         (STUB) set grid [default: 4]
    -n --note=<n>         (STUB) set grid using note value [default: 1]
    -s --speed=<s>        (STUB) playback speed [speed: 1.0]
    --dev=<device>        output device, partial match
    -p --patch=<patch>    (STUB) default midi patch, partial match
    -c                    execute commands sequentially
    -l                    execute commands simultaenously
    -r --remote           (STUB) remote/daemon mode, keep alive
    --ring                don't mute midi on end
    --loop                loop song
    --midi=<fn>           generate midi file
    +<range>              play from line or maker, for range use start:end
    -e --edit             (STUB) open file in editor
    --vi                  (STUB) shell vi mode
    -h --transpose        transpose (in half steps)
    --sustain             start with sustain enabled
    --numbers             use note numbers in output
    --notenames           use note names in output
    --flats               prefer flats in output (default)
    --sharps              prefer sharps in output
    --lint                (STUB) analyze file
    --follow              (old) print newlines every line, no output
    --quiet               no output
    --input               (STUB) midi input chord analyzer
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

dc = Player()

# class Marker:
#     def __init__(self,name,row):
#         self.name = name
#         self.line = row

midifn = ARGS['--midi']
if midifn:
    dc.midifile = mido.MidiFile(midifn)

for arg,val in iteritems(ARGS):
    if val:
        if arg == '--tempo': dc.tempo = float(val)
        elif arg == '--grid': dc.grid = float(val)
        elif arg == '--note': dc.grid = float(val)/4.0
        elif arg == '--speed': dc.speed = float(val)
        elif arg == '--verbose': dc.showtext = True
        elif arg == '--dev':
            dc.portname = val
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
        elif arg == '--loop': dc.add_flags(Player.Flag.LOOP)
        elif arg == '--renderman': dc.renderman = True

if dc.dcmode=='l':
    dc.buf = ' '.join(ARGS['LINE_CONTENT']).split(';') # ;
elif dc.dcmode=='c':
    dc.buf = ' '.join(ARGS['COMMANDS']).split(' ') # spaces
else: # mode n
    # if len(sys.argv)>=2:
    #     FN = sys.argv[-1]
    if ARGS['SONGNAME']:
        FN = ARGS['SONGNAME']
        # dc.markers[''] = 0 # start marker
        with open(FN) as f:
            lc = 0
            for line in f.readlines():
                if line:
                    if line[-1] == '\n':
                        line = line[:-1]
                    elif len(line)>=2 and line[-2:0] == '\r\n':
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
                # dc.rowno.append(lc)
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

# if dc.showtext:
#     for i in range(pygame.midi.get_count()):
#         print(pygame.midi.get_device_info(i))

DEVS = get_defs()['dev']
if dc.showtext:
    print('MIDI Devices:')   
portnames = []
breakall = False
firstpass = True
for name in DEVS:
    for i in range(pygame.midi.get_count()):
        port = pygame.midi.get_device_info(i)
        portname = port[1].decode('utf-8')
        if port[3]!=1:
            continue
        if dc.showtext:
            print(' '*4 + portname) 
        if dc.portname:
            if dc.portname.lower() in portname.lower():
                dc.portname = portname
                dev = i
                breakall = True
                break
        else:
            if portname.lower().startswith(name):
                dc.portname = portname
                dev = i
                breakall = True
                break
        if firstpass:
            portnames += [portname]
            
        # if port[3]==1:
        #     continue
    firstpass = False
    if breakall:
        break
        
# for i in range(pygame.midi.get_count()):
#     port = pygame.midi.get_device_info(i)
#     # if port[3]==1:
#     #     continue
#     portname = port[1].decode('utf-8')
#     if dc.showtext:
#         print(' '*4 + portname) 
#     if dc.portname:
#         if dc.portname.lower() in portname.lower():
#             dc.portname = portname
#             dev = i
#             break
#     else:
#         for name in DEVS:
#             if portname.lower().startswith(name):
#                 dc.portname = portname
#                 dev = i
#                 break
#     portnames += [portname]
if dc.showtext:
    print('')  

if dev == -1:
    dev = pygame.midi.get_default_output_id()

dc.midi += [pygame.midi.Output(dev)]
dc.instrument = 0
dc.midi[0].set_instrument(0)
mch = 0
for i in range(NUM_CHANNELS_PER_DEVICE):
    # log("%s -> %s" % (i,mch))
    dc.tracks.append(Track(dc, i, mch))
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
            dc.startrow = int(vals[0])
        except ValueError:
            try:
                dc.startrow = dc.markers[vals[0]]
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
    log(FG.RED + 'Other Devices: ' + FG.WHITE + '%s' % (', '.join(portnames)))
    if dc.portname:
        if dc.tracks[0].midich == DRUM_CHANNEL:
            log(FG.GREEN + 'GM Percussion')
        else:
            log(FG.GREEN + 'GM Patch: '+ FG.WHITE +'%s' % GM[dc.tracks[0].patch_num]) 

    log('Use -h for command line options.')
    log('Read the manual and look at examples. Have fun!')
    log('')

dc.run()

if dc.midifile:
    dc.save(midifn)

# TODO: turn all midi note off
i = 0
for ch in dc.tracks:
    if not dc.ring:
        ch.panic()
    ch.midi = None

for mididev in dc.midi:
    del mididev
dc.midi = []
pygame.midi.quit()

# def main():
#     pass
    
# if __name__=='__main__':
#     curses.wrapper(main)

support_stop()

