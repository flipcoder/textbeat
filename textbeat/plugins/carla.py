#!/usr/bin/env python
import textbeat.instrument as instrument
from textbeat.instrument import Instrument
from shutilwhich import which

ERROR = False
if which('carla'):
    ERROR = True

class Carla(Instrument):
    NAME = 'carla'
    def __init__(self, args):
        Instrument.__init__(self, Carla.NAME)
        self.initialized = False
        self.enabled = False
        self.soundfonts = []
        self.proc = None
        self.args = args
        self.gen_inited = False
    def enabled(self):
        return self.initialized
    def enable(self, rack):
        if not self.proc:
            fn = self.args['SONGNAME']
            if not fn:
                fn = 'default'
            if rack:
                self.self.temp_proj = tempfile.mkstemp('.carxp',fn)
                os.close(self.temp_proj[0])
                self.temp_proj = self.temp_proj[1]
                os.unlink(self.temp_proj)
                base_proj = os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)),'presets','default.carxp'))
                shutil.copy2(base_proj, self.temp_proj)

                # add instruments to temp proj file
                filebuf = ''
                with open(self.temp_proj,'r') as f:
                    filebuf = f.read()
                instrumentxml = ''
                i = 0
                for instrument in rack:
                    fnparts = instrument.split('.')
                    name = fnparts[0]
                    try:
                        ext = fnparts[1].upper()
                    except IndexError:
                        ext = 'LV2'
                    instrumentxml += '<!--'+name+'-->\n'+\
                        '<Plugin><Info>\n'+\
                        '<Type>'+ext+'</Type>\n'+\
                        '<Name>'+name+'</Name>\n'+\
                        '<URI>x</URI>'+\
                        '</Info>\n'+\
                        '<Data>\n'+\
                            '<ControlChannel>N</ControlChannel>\n'+\
                            '<Active>Yes</Active>\n'+\
                            '<Options>'+hex(i)+'</Options>\n'+\
                        '</Data>'+\
                        '</Plugin>\n\n'
                    i += 1
                filebuf = filebuf.replace('</EngineSettings>', '</EngineSettings>'+instrumentxml)
                with open(self.temp_proj,'w') as f:
                    f.write(filebuf)
                
                self.proj = self.temp_proj
                self.gen_inited = True
            else:
                self.proj = fn.split('.')[0]+'.carxp'
        if os.path.exists(proj):
            log(proj)
            self.proc = subprocess.Popen(['carla',proj], stdout=subprocess.PIPE, stderr=subprocess.PIPE) # '--nogui', 
        elif not rack:
            log('To load a Carla project headless, create a \'%s\' file.' % proj)

        self.initialized = True
    def supported(self):
        return not ERROR
    def support(self):
        return ['auto','carla']
    def stop(self):
        if self.gen_inited and self.proj:
            try:
                os.remove(carla_proj[1])
            except OSError:
                pass
            except FileNotFoundError:
                pass

        if self.self.temp_proj:
            os.unlink(self.temp_proj)
        if self.self.proc:
            self.proc.kill()

# instrument.export(FluidSynth)
export = Carla

