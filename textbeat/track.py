from .defs import *
import math

class Recording(object):
    def __init__(self, name, slot):
        self.name = slot
        self.content = []

class Tuplet(object):
    def __init__(self):
        # self.tuplets = False
        self.note_spacing = 1.0
        self.tuplet_count = 0
        self.tuplet_offset = 0.0

class Lane(object):
    def __init__(self, ctx, idx, midich, parent=None):
        self.idx = idx
        self.midi = ctx.midi
        self.ctx = ctx
        self.schedule = self.ctx.schedule
    def master(self):
        return self.parent if self.parent else self
    def reset(self):
        self.notes = [0] * RANGE
        self.sustain_notes = [False] * RANGE

class Track(Lane):
    class Flag:
        ROMAN = bit(0)
        # TRANSPOSE = bit(1)
    FLAGS = [
        'roman', # STUB: fit roman chord in scale shape
        # 'transpose', # allow transposition of note letters
    ]
    def __init__(self, ctx, idx, midich):
        Lane.__init__(self,ctx,idx,midich)
        # self.midis = [player]
        self.channels = [(0,midich)]
        self.midich = midich # tracks primary midi channel
        self.initial_channel = midich
        self.non_drum_channel = midich
        self.reset()
    def us(self):
        # microseconds
        # return int(self.ctx.t)*1000000
        return math.floor(mido.second2tick(self.ctx.t, self.ctx.grid, self.ctx.tempo))
    def reset(self):
        Lane.reset(self)
        self.mode = 0 # 0 is NONE which inherits global mode
        self.scale = None
        # self.instrument = 0
        self.octave = 0 # rel to OCTAVE_BASE
        self.modval = 0 # dont read in mod, just track its change by this channel
        self.sustain = False # sustain everything?
        self.arp_note = None # current arp note
        self.arp_notes = [] # list of notes to arpegiate
        self.arp_idx = 0
        self.arp_notes_left = 0
        self.arp_cycle_limit = 0 # cycles remaining, only if limit != 0
        self.arp_pattern = [] # relative steps to
        self.arp_enabled = False
        self.arp_once = False
        self.arp_delay = 0.0
        self.arp_sustain = False
        self.arp_note_spacing = 1.0
        # self.arp_reverse = False
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
        self.tuplet = [] # future
        self.tuplets = False
        self.note_spacing = 1.0
        self.tuplet_count = 0
        self.tuplet_offset = 0.0
        self.use_sustain_pedal = False # whether to use midi sustain instead of track
        self.sustain_pedal_state = False # current midi pedal state
        # self.schedule.clear_channel(self)
        self.flags = 0 # set()
        self.enabled = True
        self.soloed = False
        # self.muted = False
        self.volval = 1.0
        self.slots = {} # slot -> Recording
        self.slot = None # careful, this can be 0
        self_slot_idx = 0
        self.lane = None
        self.lanes = []
        self.ccs = {}
        self.dev = 0
        
        # pitch wheel oscillation
        self.vibrato_enabled = False # don't set this directly, call vibrato()
        self.vibrato_amp = 0.0
        self.vibrato_freq = 0.0 
        # self.vibrato_offset = 0.0 # value that gets added to pitch

    def vibrato(self, b, amp=0.0, freq=0.0):
        self.vibrato_amp = amp
        self.vibrato_freq = freq
        self.vibrato_t = 0.0
        if b == self.vibrato_enabled:
            return
        if b:
            try:
                self.ctx.vibrato_tracks.remove(self)
            except KeyError:
                pass
        else:
            self.ctx.vibrato_tracks.add(self)
        self.pitch(self.pitchval)
        self.vibrato_enabled = b

    def vibrato_logic(self, t):
        # TODO: test this
        self.vibrato_t += t
        v = math.sin(self.vibrato_t * self.vibrato_freq * math.tau) * self.vibrato_amp
        self.pitch(self.pitchval + v, False) # don't save new pitchval on call

    # def _lazychannelfunc(self):
    #     # get active channel numbers
    #     return list(map(filter(lambda x: self.channels & x[0], [(1<<x,x) for x in range(16)]), lambda x: x[1]))
    def get_device(self):
        return self.ctx.devices[self.dev]
    def set_device(self, dev, stackidx=-1):
        if stackidx == -1:
            self.dev = dev
            for ch in self.channels:
                self.device(dev,ch)
            return
        ch = self.channels[stackidx]
        self.channels[stackidx] = (dev,ch[1])
    def master(self):
        return self
    def get_track(self):
        return self.lanes[self.lane] if self.lane!=None else self
    # def get_lane(self):
    #     return self.lanes[self.lane] if self.lanes else lane
    def volume(self,v=None):
        if v==None:
            return self.volval
        self.volval = v
        self.cc(7,int(v*127.0))
        self.ccs[1] = v
    def refresh(self):
        self.cc(1,0)
        self.volume(self.volval)
        self.ccs[7] = v
    def add_flags(self, f):
        if isinstance(f, str):
            f = 1 << FLAGS.index(f)
        else:
            assert f > 0
        # if f != f & FLAGS:
        #     raise ParseError('invalid flags')
        self.flags |= f
    def has_flags(self, f):
        if isinstance(f, str):
            f = 1 << FLAGS.index(f)
        else:
            assert f > 0
        # if f != f & FLAGS:
        #     raise ParseError('invalid flags')
        return self.flags & f
    def midifile_write(self, ch, msg):
        # ch: midi channel index, not midi channel # (index 0 of self.channels tuple item)
        while ch >= len(self.ctx.midifile.tracks):
            self.ctx.midifile.tracks.append(mido.MidiTrack())
        # print(msg)
        self.ctx.midifile.tracks[ch].append(msg)
    def enable(self, v=True):
        was = v
        if not was and v:
            self.enabled = v
            self.panic()
    def disable(self, v=True):
        self.enable(not v)
    def stop(self):
        self.release_all(True)
        for ch in self.channels:
            status = (MIDI_CC<<4) + ch[1]
            if self.ctx.showmidi: log(FG.YELLOW + 'MIDI: CC (%s, %s, %s)' % (status,120,0))
            if self.ctx.midifile:
                self.midifile_write(ch[0], mido.UnknownMetaMessage(status,data=[120, 0],time=self.us()))
            else:
                self.midi[ch[0]].write_short(status, 120, 0)
            if self.modval>0:
                self.refresh()
                self.modval = False
    def panic(self):
        self.release_all(True)
        for ch in self.channels:
            status = (MIDI_CC<<4) + ch[1]
            if self.ctx.showmidi: log(FG.YELLOW + 'MIDI: CC (%s, %s, %s)' % (status,123,0))
            if self.ctx.midifile:
                self.midifile_write(ch[0], mido.UnknownMetaMessage(status, [123, 0], time=self.us()))
            else:
                self.midi[ch[0]].write_short(status, 123, 0)
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
                if self.ctx.midifile:
                    self.midifile_write(ch[0], mido.Message(
                        'note_on',note=n,velocity=v,time=self.us(),channel=ch[1]
                    ))
                else:
                    self.midi[ch[0]].note_on(n,v,ch[1])
    def note_off(self, n, v=-1):
        if v == -1:
            v = self.vel
        if n < 0 or n >= RANGE:
            return
        if self.notes[n]:
            # log("off " + str(n))
            for ch in self.channels:
                if self.ctx.showmidi: log(FG.YELLOW + 'MIDI: NOTE OFF (%s, %s, %s)' % (n,v,ch))
                if not self.ctx.midifile:
                    self.midi[ch[0]].note_on(self.notes[n],0,ch[1])
                    self.midi[ch[0]].note_off(self.notes[n],v,ch[1])
                self.notes[n] = 0
                self.sustain_notes[n] = 0
                if self.ctx.midifile:
                    self.midifile_write(ch[0], mido.Message(
                        'note_on',note=n,velocity=0,time=self.us(),channel=ch[1]
                    ))
                    self.midifile_write(ch[0], mido.Message(
                        'note_off',note=n,velocity=v,time=self.us(),channel=ch[1]
                    ))

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
                    self.midi[ch[0]].note_on(n,0,ch[1])
                    self.midi[ch[0]].note_off(n,v,ch[1])
                    self.notes[n] = 0
                    self.sustain_notes[n] = 0
                # log("off " + str(n))
        # self.notes = [0] * RANGE
        if self.modval>0:
            self.cc(1,0)
        # self.arp_enabled = False
        # self.schedule.clear_channel(self)
    # def cut(self):
    def midi_channel(self, midich, stackidx=-1):
        if midich==DRUM_CHANNEL: # setting to drums
            if self.channels[stackidx][1] != DRUM_CHANNEL:
                self.non_drum_channel = self.channels[stackidx][1]
            self.octave = DRUM_OCTAVE
        else:
            for ch in self.channels:
                if ch!=DRUM_CHANNEL:
                    midich = ch[1]
            if midich != DRUMCHANNEL: # no suitable channel in span?
                midich = self.non_drum_channel
        if stackidx == -1: # all
            self.release_all()
            self.channels = [(0,midich)]
        elif midich not in self.channels:
            self.channels.append(midich)
    def write_short(self, ch, status, val, val2):
        if self.ctx.midifile:
            self.midifile_write(ch,mido.UnknownMetaMessage(status,data=[val,val2], time=self.us()))
        else:
            self.midi[ch].write_short(status,val,val2)
    def pitch(self, val, save=True): # [-1.0,1.0]
        if save:
            self.pitchval = val
        val = min(max(0,int((1.0 + val)*0x2000)),16384)
        val2 = (val>>0x7f)
        val = val&0x7f
        for ch in self.channels:
            status = (MIDI_PITCH<<4) + ch[1]
            if self.ctx.showmidi: log(FG.YELLOW + 'MIDI: PITCH (%s, %s)' % (val,val2))
            self.write_short(ch[0], status, val, val2)
    def cc(self, cc, val): # control change
        if type(val) ==type(bool): val = 127 if val else 0 # allow cc bool switches
        for ch in self.channels:
            status = (MIDI_CC<<4) + ch[1]
            if self.ctx.showmidi: log(FG.YELLOW + 'MIDI: CC (%s, %s, %s)' % (status, cc,val))
            self.write_short(ch[0], status, cc, val)
            self.ccs[cc] = v
        if cc==1:
            self.modval = val
        if cc==7:
            self.volval = val/127.0
    def mod(self, val):
        self.modval = 0
        return self.cc(1,val)
    def patch(self, p, stackidx=-1):
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
                        break
                    elif lengw==0:
                        log(FG.RED + 'Patch \"'+p+'\" not found')
                        assert False
                assert len(gmwords) > 0
                if self.ctx.shell:
                    log(FG.GREEN + 'GM Patch: ' + STYLE.RESET_ALL +  gmwords[0])
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
        if stackidx==-1:
            for ch in self.channels:
                status = (MIDI_PROGRAM<<4) + ch[1]
                if self.ctx.showmidi: log(FG.YELLOW + 'MIDI: PROGRAM (%s, %s)' % (status,p))
                self.midi[ch[0]].write_short(status,p)
        else:
            status = (MIDI_PROGRAM<<4) + self.channels[stackidx][1]
            if self.ctx.showmidi: log(FG.YELLOW + 'MIDI: PROGRAM (%s, %s)' % (status,p))
            self.midi[self.channels[stackidx][0]].write_short(status,p)

    def bank(self, b):
        self.ccs[0] = b
        self.cc(0,b)
    def arp(self, notes, count=0, sustain=False, pattern=[], reverse=False, octave=0):
        self.arp_enabled = True
        if reverse:
            notes = notes[::-1]
        self.arp_notes = list(map(lambda n: n + (octave*12), notes))
        self.arp_cycle_limit = count
        self.arp_cycle = count
        self.arp_pattern = pattern if pattern else [1]
        self.arp_pattern_idx = 0
        self.arp_notes_left = len(notes) * max(1,count)
        self.arp_idx = 0 # use inversions to move this start point (?)
        self.arp_once = False
        self.arp_sustain = sustain
    def arp_stop(self):
        self.arp_enabled = False
        self.release_all()
    def arp_next(self, stop_infinite=True):
        stop = False
        assert self.arp_enabled
        # if not self.arp_enabled:
        #     self.arp_note = None
        #     return False
        # out(self.arp_idx + 1)
        if self.arp_notes_left != -1 or stop_infinite:
            if self.arp_notes_left != -1:
                self.arp_notes_left = max(0, self.arp_notes_left - 1)
            if self.arp_notes_left <= 0:
                if self.arp_cycle_limit or stop_infinite:
                    self.arp_note = None
                    self.arp_enabled = False
        self.arp_note = self.arp_notes[self.arp_idx]
        self.arp_idx = self.arp_idx + self.arp_pattern[self.arp_pattern_idx]
        self.arp_pattern_idx = (self.arp_pattern_idx + 1) % len(self.arp_pattern)
        self.arp_delay = (self.arp_delay + self.arp_note_spacing) - 1.0
        if self.arp_idx >= len(self.arp_notes) or self.arp_idx < 0: # cycle?
            self.arp_once = True
            if self.arp_cycle_limit:
                self.arp_cycle -= 1
                if self.arp_cycle == 0:
                    self.arp_enabled = False
            self.arp_idx = 0
        # else:
        #     self.arp_idx += 1
        return self.arp_note != None
    def arp_restart(self, count = None):
        self.arp_enabled = True
        # self.arp_sustain = False
        if count != None: # leave same (could be -1, so use -2)
            self.arp_count = count
        self.arp_idx = 0
    def tuplet_next(self):
        delay = 0.0
        if self.tuplets:
            delay = self.tuplet_offset
            self.tuplet_offset += self.note_spacing - 1.0
            # if self.tuplet_offset >= 1.0 - EPSILON:
            #     out('!!!')
                # self.tuplet_offset = 0.0
            self.tuplet_count -= 1
            if not self.tuplet_count:
                self.tuplet_stop()
        # else:
        #     self.tuplet_stop()
        # if feq(delay,1.0):
        #     return 0.0
        # out(delay)
        return delay
    def tuplet_stop(self):
        self.tuplets = False
        self.tuplet_count = 0
        self.note_spacing = 1.0
        self.tuplet_offset = 0.0

