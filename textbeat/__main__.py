#!/usr/bin/python
"""textbeat
Copyright (c) 2018 Grady O'Connell
Open-source under MIT License

Examples:
    textbeat                  shell
    textbeat -T               start tutorial
    textbeat song.txbt        play song

Usage:
    textbeat [--dev=<device>] [--midi=<fn>] [--ring] [--follow] [--stdin] [-adeftnpsrxvL] [INPUT]
    textbeat [+RANGE] [--dev=<device>] [--midi=<fn>] [--ring] [--follow] [--stdin] [-adeftnpsrxL] [INPUT]
    textbeat [-rhT]
    textbeat -c [COMMANDS ...]
    textbeat -l [LINE_CONTENT ...]

Options:
    -h --help             show this
    -v --verbose          verbose
    -T --tutorial         (STUB) tutorial
    -t --tempo=<bpm>      (STUB) set tempo [default: 120]
    -x --grid=<g>         (STUB) set grid [default: 4]
    -n --note=<n>         (STUB) set grid using note value [default: 1]
    -s --speed=<s>        (STUB) playback speed [speed: 1.0]
    --dev=<device>        output device, partial match
    -p --patch=<patch>    (STUB) default midi patch, partial match
    -f --flags            comma-separated global flags
    -c                    execute commands sequentially
    -l                    execute commands simultaenously
    --stdin               read entire file from stdin
    -r --remote           (STUB) realtime remote (control through stdin/out)
    --ring                don't mute midi on end
    -L --loop             loop song
    --midi=<fn>           generate midi file
    +<range>              play from line or maker, for range use start:end
    -e --edit             (STUB) open file in editor
    --vi                  (STUB) shell vi mode
    -H --transpose        transpose (in half steps)
    --sustain             start with sustain enabled
    --numbers             use note numbers in output
    --notenames           use note names in output
    --flats               prefer flats in output (default)
    --sharps              prefer sharps in output
    --lint                (STUB) analyze file
    --follow              tracks file output for editors by printing newlines every line
    --quiet               no output
    -a --analyze          (STUB) midi input chord analyzer
"""
from __future__ import absolute_import, unicode_literals, print_function, generators
# try:
from .defs import *
# except:
#     from .defs import *
def main():
# if __name__!='__main__':
#     sys.exit(0)
    # ARGS = docopt(__doc__.replace('textbeat',os.path.basename(sys.argv[0]).lower()))
    ARGS = docopt(__doc__)
    set_args(ARGS)

    from . import support
    # from .support import *
    # from .support import *

    # style = style_from_dict({
    #     Token:          '#ff0066',
    #     Token.Prompt:   '#00aa00',
    #     Token.Info:     '#000088',
    # })
    colorama.init(autoreset=True)

# logging.basicConfig(filename=LOG_FN,level=logging.DEBUG)

    player = Player()

# class Marker:
#     def __init__(self,name,row):
#         self.name = name
#         self.line = row

    midifn = None

    for arg,val in iteritems(ARGS):
        if val:
            if arg == '--tempo': player.tempo = float(val)
            elif arg == '--midi':
                midifn = val
                player.midifile = mido.MidiFile()
                player.cansleep = False
            elif arg == '--grid': player.grid = float(val)
            elif arg == '--note': player.grid = float(val)/4.0
            elif arg == '--speed': player.speed = float(val)
            elif arg == '--verbose': player.showtext = True
            elif arg == '--dev':
                player.portname = val
            elif arg == '--vi': player.vimode = True
            elif arg == '--patch':
                vals = val.split(',')
                for i in range(len(vals)):
                    val = vals[i]
                    if val.isdigit():
                        player.tracks[i].patch(int(val))
                    else:
                        player.tracks[i].patch(val)
            elif arg == '--sustain': player.sustain=True
            elif arg == '--ring': player.ring=True
            elif arg == '--remote': player.remote = True
            elif arg == '--lint': LINT = True
            elif arg == '--quiet': set_print(False)
            elif arg == '--follow':
                set_print(False)
                player.canfollow = True
            elif arg == '--flats': FLATS = True
            elif arg == '--sharps': SHARPS= True
            elif arg == '--edit': pass
            elif arg == '-l': player.cmdmode = 'l'
            elif arg == '-c': player.cmdmode = 'c'
            elif arg == '-T': player.tutorial = Tutorial(player)
            elif arg =='--flags':
                vals = val.split(',')
                player.add_flags(map(player.FLAGS.index, vals))
            elif arg == '--loop': player.add_flags(Player.Flag.LOOP)
            # elif arg == '--renderman': player.renderman = True

    if player.cmdmode=='l':
        player.buf = ' '.join(ARGS['LINE_CONTENT']).split(';') # ;
    elif player.cmdmode=='c':
        player.buf = ' '.join(ARGS['COMMANDS']).split(' ') # spaces
    elif not player.tutorial: # mode n
        # if len(sys.argv)>=2:
        #     FN = sys.argv[-1]
        FN = ARGS['INPUT']
        from_stdin = False
        if FN=='-' or ARGS['--stdin']:
            FN = 0 # TEMP: doesnt work with py2
            from_stdin = True
        else:
            from_stdin = False
        if FN or from_stdin:
            # player.markers[''] = 0 # start marker
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
                            if not bm in player.markers:
                                player.markers[bm] = lc
                        elif ls.startswith('|') and ls.endswith(':'):
                            bm = ls[1:-1]
                            # only store INITIAL marker positions
                            if not bm in player.markers:
                                player.markers[bm] = lc

                    lc += 1
                    player.buf += [line]
                    # player.rowno.append(lc)
                player.shell = False
        else:
            if player.cmdmode == 'n':
                player.cmdmode = ''
            player.shell = True

    player.interactive = player.shell or player.remote or player.tutorial

    pygame.midi.init()
    if pygame.midi.get_count()==0:
        error('No midi devices found.')
        sys.exit(1)    
    dev = -1

# if player.showtext:
#     for i in range(pygame.midi.get_count()):
#         log(pygame.midi.get_device_info(i))

    DEVS = get_defs()['dev']
    if player.showtext:
        log('MIDI Devices:')
    portnames = []
    breakall = False
    firstpass = True
    for name in DEVS:
        for i in range(pygame.midi.get_count()):
            port = pygame.midi.get_device_info(i)
            portname = port[1].decode('utf-8')
            if port[3]!=1:
                continue
            if player.showtext:
                log(' '*4 + portname) 
            if player.portname:
                if player.portname.lower() in portname.lower():
                    player.portname = portname
                    dev = i
                    breakall = True
                    break
            else:
                if portname.lower().startswith(name):
                    player.portname = portname
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
#     if player.showtext:
#         log(' '*4 + portname) 
#     if player.portname:
#         if player.portname.lower() in portname.lower():
#             player.portname = portname
#             dev = i
#             break
#     else:
#         for name in DEVS:
#             if portname.lower().startswith(name):
#                 player.portname = portname
#                 dev = i
#                 break
#     portnames += [portname]
    if player.showtext:
        log('')

    if dev == -1:
        dev = pygame.midi.get_default_output_id()

    player.midi += [pygame.midi.Output(dev)]
    player.instrument = 0
    player.midi[0].set_instrument(0)
    mch = 0
    for i in range(NUM_CHANNELS_PER_DEVICE):
        # log("%s -> %s" % (i,mch))
        player.tracks.append(Track(player, i, mch))
        mch += 2 if i==DRUM_CHANNEL else 1

    if player.sustain:
        player.tracks[0].sustain = player.sustain

# show nice output in certain modes
    if player.shell or player.cmdmode in 'cl':
        player.showtext = True

    player.init()

    if player.shell:
        log(FG.BLUE + 'textbeat')# v'+str(VERSION))
        log('Copyright (c) 2018 Grady O\'Connell')
        log('https://github.com/flipcoder/textbeat')
        active = support.SUPPORT_ALL & support.SUPPORT
        inactive = support.SUPPORT_ALL - support.SUPPORT
        if active:
            log(FG.GREEN + 'Active Modules: ' + STYLE.RESET_ALL +  ', '.join(active) + STYLE.RESET_ALL)
        if inactive:
            log(FG.RED + 'Inactive Modules: ' +  STYLE.RESET_ALL + ', '.join(inactive))
        if player.portname:
            log(FG.GREEN + 'Device: ' + STYLE.RESET_ALL + '%s' % (player.portname if player.portname else 'Unknown',))
        log(FG.RED + 'Other Devices: ' + STYLE.RESET_ALL + '%s' % (', '.join(portnames)))
        if player.portname:
            if player.tracks[0].midich == DRUM_CHANNEL:
                log(FG.GREEN + 'GM Percussion')
            else:
                log(FG.GREEN + 'GM Patch: '+ STYLE.RESET_ALL +'%s' % GM[player.tracks[0].patch_num]) 

        # log('')
        # log(FG.BLUE + 'New? Type help and press enter to start the tutorial.')
        log('')

    player.run()

    if player.midifile:
        player.midifile.save(midifn)

    # TODO: turn all midi note off
    i = 0
    for ch in player.tracks:
        if not player.ring:
            ch.panic()
        ch.midi = None

    for mididev in player.midi:
        del mididev
    player.midi = []
    pygame.midi.quit()

# if __name__=='__main__':
#     curses.wrapper(main)

    support.support_stop()

if __name__=='__main__':
    main()

