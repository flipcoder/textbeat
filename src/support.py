from . import *
from . import get_args
from shutilwhich import which
ARGS = get_args()
SUPPORT = set(['midi'])
SUPPORT_ALL = set(['auto','carla','supercollider','csound','midi','gme']) # gme,mpe
psonic = None
if which('carla'):
    SUPPORT.add('carla')
    SUPPORT.add('auto')
    
if which('scsynth'):
    try:
        import oscpy
        SUPPORT.add('supercollider')
    except:
        pass

csound = None
if which('csound'):
    SUPPORT.add('csound')

def supports(dev):
    global SUPPORT
    return dev in SUPPORT

csound_inited = False
def csound_init():
    global csound_inited
    if not csound_inited:
        import subprocess
        csound_proc = subprocess.Popen(['csound', '-odac', '--port='+str(CSOUND_PORT)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        csound = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    csound_inited = True

carla_inited = False
carla_proc = None
def carla_init(auto=False):
    global carla_proc
    if not carla_proc:
        import oscpy
        fn = ARGS['SONGNAME']
        if not fn:
            fn = 'default'
        if auto:
            # embedded file -> /tmp/proj
            # TODO: use tmp file of embedded file
            proj = fn.split('.')[0]+'.carxp' # TEMP: generate
        else:
            proj = fn.split('.')[0]+'.carxp'
        if os.path.exists(proj):
            carla_proc = subprocess.Popen(['carla', '--nogui', proj], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        elif not auto:
            log('To load a Carla project headless, create a \'%s\' file.' % proj)

def auto_init():
    carla_init(True)

support_init = {
    'csound': csound_init,
    'carla': carla_init,
    'auto': auto_init,
}

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
    if carla_proc:
        carla_proc.kill()
    if BGPROC:
        BGPIPE.send((BGCMD.QUIT,))
        BGPROC.join()

