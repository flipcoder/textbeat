#!/usr/bin/env python
from textbeat.defs import *
import textbeat.instrument as instrument
from textbeat.instrument import Instrument
from shutilwhich import which
import subprocess

ERROR = False
if not which('espeak'):
    ERROR = True

# Currently not used, caches text to speech stuff in a way compatible with jack
# current super slow, need to write stabilizer first
class BackgroundProcess(object):
    def __init__(self, con):
        self.con = con
        self.words = {}
        self.processes = []
    def cache(self,word):
        try:
            tmp = self.words[word]
        except:
            tmp = tempfile.NamedTemporaryFile()
            p = subprocess.Popen(['espeak', '\"'+pipes.quote(word)+'\"','--stdout'], stdout=tmp)
            p.wait()
            self.words[tmp.name] = tmp
        return tmp
    def run(self):
        devnull = open(os.devnull, 'w')
        while True:
            msg = self.con.recv()
            # log(msg)
            if msg[0]==BGCMD.SAY:
                tmp = self.cache(msg[1])
                # super slow, better option needed
                self.processes.append(subprocess.Popen(['mpv','-ao','jack',tmp.name],stdout=devnull,stderr=devnull))
            elif msg[0]==BGCMD.CACHE:
                self.cache(msg[1])
            elif msg[0]==BGCMD.QUIT:
                break
            elif msg[0]==BGCMD.CLEAR:
                self.words.clear()
            else:
                log('BAD COMMAND: ' + msg[0])
            self.processes = list(filter(lambda p: p.poll()==None, self.processes))
        self.con.close()
        for tmp in self.words:
            tmp.close()
        for proc in self.processes:
            proc.wait()

def bgproc_run(con):
    self.proc = BackgroundProcess(con)
    self.proc.run()

class ESpeak(Instrument):
    NAME = 'espeak'
    def __init__(self, args):
        Instrument.__init__(self, ESpeak.NAME)
        self.initialized = False
        self.proc = None
        self.espeak = None
    def enable(self):
        if not initialized:
            self.pipe, child = Pipe()
            self.proc = Process(target=bgproc_run, args=(child,))
            self.proc.start()

            self.initialized = True
    def enabled(self):
        return self.initialized
    def supported(self):
        return not ERROR
    def support(self):
        return ['espeak']
    # def note_on(self, t, n, v):
    #     self.fs.noteon(t, n, v)
    # def note_off(self, t, n, v):
    #     self.fs.noteoff(t, v)
    #     pass
    def stop(self):
        if self.proc:
            self.pipe.send((BGCMD.QUIT,))
            self.proc.join()

        # self.proc.kill()
        pass

export = ESpeak

