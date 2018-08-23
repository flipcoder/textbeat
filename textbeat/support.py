# TODO: eventually: scan and load plugins
from .defs import *
from shutilwhich import which
import tempfile
# from xml.dom import minidom
ARGS = get_args()
SUPPORT = set(['midi'])
SUPPORT_ALL = set(['carla','supercollider','csound','midi', 'fluidsynth', 'sonicpi']) # gme,mpe
gen_inited = False
if which('carla'):
    SUPPORT.add('carla')
    SUPPORT.add('gen') # auto generate
    gen_inited = True
    
if which('scsynth'):
    try:
        import oscpy
        SUPPORT.add('supercollider')
    except:
        pass

try:
    import psonic
    SUPPORT.add('sonicpi')
except ImportError:
    pass

try:
    if which('fluidsynth'):
        SUPPORT.add('fluidsynth')
except ImportError:
    pass

csound = None
# if which('csound'):
try:
    import csnd6
    SUPPORT.add('csound')
except ImportError:
    pass

def supports(dev):
    global SUPPORT
    return dev in SUPPORT

csound_inited = False
def csound_init(gen=[]):
    global csound_inited
    if not csound_inited:
        import subprocess
        csound_proc = subprocess.Popen(['csound', '-odac', '--port='+str(CSOUND_PORT)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        csound = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    csound_inited = True

carla_inited = False
carla_proc = None
carla_proj = None
def carla_init(gen):
    global carla_proc
    global carla_proj
    global carla_inited
    if not carla_proc:
        import oscpy
        fn = ARGS['SONGNAME']
        if not fn:
            fn = 'default'
        if gen:
            # generate proj file from devs
            # embedded file -> /tmp/proj
            # carla_proj = proj = fn.split('.')[0]+'.carxp' # TEMP: generate
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, os.path.join(os.path.abspath(sys.argv[0]),'presets','default.carxp'))
            shutil.copy2(path, temp_path)
        else:
            proj = fn.split('.')[0]+'.carxp'
        if os.path.exists(proj):
            carla_proc = subprocess.Popen(['carla', '--nogui', proj], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        elif not gen:
            log('To load a Carla project headless, create a \'%s\' file.' % proj)
    carla_inited = True

def gen_init(gen):
    carla_init(gen)

support_init = {
    'csound': csound_init,
    'carla': carla_init,
    'gen': gen_init,
}

def csound_send(s):
    assert csound
    return csound.sendto(s,('localhost',CSOUND_PORT))

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
    if gen_inited and carla_proj:
        try:
            os.remove(carla_proj[1])
        except OSError:
            pass
        except FileNotFoundError:
            pass

