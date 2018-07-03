from . import get_args
ARGS = get_args()
SUPPORT = set(['midi'])
SUPPORT_ALL = set(['supercollider','csound','midi']) # gme,mpe
psonic = None
if ARGS['--supercollider']:
    import osc
    SUPPORT.add('supercollider')

csound = None
if ARGS['--csound']:
    csound_proc = subprocess.Popen(['csound', '-odac', '--port='+str(CSOUND_PORT)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    csound = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    SUPPORT.add('csound')

def csound_send(s):
    assert csound
    return csound.sendto(s,('localhost',CSOUND_PORT))

# Currently not used, caches text to speech stuff in a way compatible with jack
# current super slow, need to write stabilizer first
class BackgroundProcess:
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
            self.processses = list(filter(lambda p: p.poll()==None, self.processes))
        self.con.close()
        for tmp in self.words:
            tmp.close()
        for proc in self.processes:
            proc.wait()

def bgproc_run(con):
    proc = BackgroundProcess(con)
    proc.run()

BGPROC = None
# BGPIPE, child = Pipe()
# BGPROC = Process(target=bgproc_run, args=(child,))
# BGPROC.start()

def support_stop():
    if csound and csound_proc:
        csound_proc.kill()
    if BGPROC:
        BGPIPE.send((BGCMD.QUIT,))
        BGPROC.join()

