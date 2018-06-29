from . import *

class Track:
    FLAGS = set('auto_roman')
    def __init__(self, ctx, idx, midich, player, schedule):
        self.idx = idx
        self.ctx = ctx
        # self.players = [player]
        self.player = player
        self.schedule = schedule
        self.channels = [midich]
        self.midich = midich # tracks primary midi channel
        self.initial_channel = midich
        self.non_drum_channel = midich
        # self.strings = []
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
        self.max_vel = -1
        self.soft_vel = -1
        self.ghost_vel = -1
        self.accent_vel = -1
        self.non_drum_channel = self.initial_channel
        # self.off_vel = 64
        self.staccato = False
        self.patch_num = 0
        self.transpose = 0
        self.pitchval = 0.0
        self.tuplets = False
        self.note_spacing = 1.0
        self.tuplet_count = 0
        self.tuplet_offset = 0.0
        self.use_sustain_pedal = False # whether to use midi sustain instead of track
        self.sustain_pedal_state = False # current midi pedal state
        self.schedule.clear_channel(self)
        self.flags = set()
        self.enabled = True
        self.soloed = False
        self.volval = 1.0
    # def _lazychannelfunc(self):
    #     # get active channel numbers
    #     return list(map(filter(lambda x: self.channels & x[0], [(1<<x,x) for x in range(16)]), lambda x: x[1]))
    def volume(self,v=None):
        if v==None:
            return self.volval
        self.volval = v
        self.cc(7,int(v*127.0))
    def refresh(self):
        self.cc(1,0)
        self.volume(self.volval)
    def add_flags(self, f):
        if f != f & FLAGS:
            raise ParseError('invalid flags')
        self.flags |= f
    def enable(self, v=True):
        was = v
        if not was and v:
            self.enabled = v
            self.panic()
    def disable(self, v=True):
        self.enable(not v)
    def stop(self):
        for ch in self.channels:
            status = (MIDI_CC<<4) + ch
            if self.ctx.showmidi: log(FG.YELLOW + 'MIDI: CC (%s, %s, %s)' % (status,120,0))
            self.player.write_short(status, 120, 0)
            if self.modval>0:
                self.refresh()
                self.modval = False
    def panic(self):
        for ch in self.channels:
            status = (MIDI_CC<<4) + ch
            if self.ctx.showmidi: log(FG.YELLOW + 'MIDI: CC (%s, %s, %s)' % (status,123,0))
            self.player.write_short(status, 123, 0)
            if self.modval>0:
                self.refresh()
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
            if self.ctx.showmidi: log(FG.YELLOW + 'MIDI: NOTE ON (%s, %s, %s)' % (n,v,ch))
            if (not self.ctx.muted or (self.ctx.muted and self.soloed))\
                and self.enabled and self.ctx.startrow==-1:
                self.player.note_on(n,v,ch)
    def note_off(self, n, v=-1):
        if v == -1:
            v = self.vel
        if n < 0 or n >= RANGE:
            return
        if self.notes[n]:
            # log("off " + str(n))
            for ch in self.channels:
                if self.ctx.showmidi: log(FG.YELLOW + 'MIDI: NOTE OFF (%s, %s, %s)' % (n,v,ch))
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
                    if self.ctx.showmidi: log(FG.YELLOW + 'MIDI: NOTE OFF (%s, %s, %s)' % (n,v,ch))
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
        self.pitchval = val
        val2 = (val>>0x7f)
        val = val&0x7f
        for ch in self.channels:
            status = (MIDI_PITCH<<4) + self.midich
            if self.ctx.showmidi: log(FG.YELLOW + 'MIDI: PITCH (%s, %s)' % (val,val2))
            self.player.write_short(status,val,val2)
            self.mod(0)
    def cc(self, cc, val): # control change
        if type(val) ==type(bool): val = 127 if val else 0 # allow cc bool switches
        for ch in self.channels:
            status = (MIDI_CC<<4) + ch
            if self.ctx.showmidi: log(FG.YELLOW + 'MIDI: CC (%s, %s, %s)' % (status, cc,val))
            self.player.write_short(status,cc,val)
        if cc==1:
            self.modval = val
    def mod(self, val):
        self.modval = 0
        return self.cc(1,val)
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
        if self.ctx.showmidi: log(FG.YELLOW + 'MIDI: PROGRAM (%s, %s)' % (status,p))
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


