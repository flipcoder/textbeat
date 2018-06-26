from . import load_cfg
MIDI_CC = 0B1011
MIDI_PROGRAM = 0B1100
MIDI_PITCH = 0B1110
GM = load_cfg('gm')
GM_LOWER = [""]*len(GM)
for i in range(len(GM)): GM_LOWER[i] = GM[i].lower()
