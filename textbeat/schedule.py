from .defs import *

class Event(object):
    def __init__(self, t, func, ch):
        self.t = t
        self.func = func
        self.ch = ch

class Schedule(object):
    def __init__(self, ctx):
        self.ctx = ctx
        self.events = []
        # store this just in case logic() throws
        # we'll need to reenter knowing this value
        self.passed = 0.0 
        self.clock = 0.0
        self.last_clock = 0
        self.started = False
    # all note mute and play events should be marked skippable
    def pending(self):
        return len(self.events)
    def add(self, e):
        self.events.append(e)
    def clear(self):
        assert False
        self.events = []
    def clear_channel(self, ch):
        assert False
        self.events = [ev for ev in self.events if ev.ch!=ch]
    def logic(self, t):
        processed = 0
        self.passed = 0

        # if self.last_clock == 0:
        #     self.last_clock = time.clock()
        # clock = time.clock()
        # self.dontsleep = (clock - self.last_clock)
        # self.last_clock = clock

        # if self.started:
        #     tdelta = (clock - self.passed)
        #     self.passed += tdelta
        #     self.clock = clock
        # else:
        #     self.started = True
        #     self.clock = clock
        #     self.passed = 0.0
        # log(self.clock)

        # pending_events_count = sum(1 for e in self.events if e.t > 0.0 and e.t < 2.0)
        # print(pending_events_count)
        
        try:
            self.events = sorted(self.events, key=lambda e: e.t)
            for ev in self.events:
                if ev.t > 1.0:
                    ev.t -= 1.0
                else:
                    # sleep until next event
                    if ev.t >= 0.0:
                        if self.ctx.cansleep and self.ctx.startrow == -1:
                            self.ctx.t += self.ctx.speed * t * (ev.t-self.passed)
                            time.sleep(max(0,self.ctx.speed * t * (ev.t-self.passed)))
                        ev.func(0)
                        self.passed = ev.t # only inc if positive
                    else:
                        ev.func(0)

                    processed += 1
            
            slp = t * (1.0 - self.passed) # remaining time
            if slp > 0.0:
                self.ctx.t += self.ctx.speed*slp
                if self.ctx.cansleep and self.ctx.startrow == -1:
                    time.sleep(max(0,self.ctx.speed*slp))
            self.passed = 0.0
            
            self.events = self.events[processed:]
        except KeyboardInterrupt:
            self.events = self.events[processed:]
            raise
        except SignalError:
            self.events = self.events[processed:]
            raise
        except EOFError:
            self.events = self.events[processed:]
            raise

