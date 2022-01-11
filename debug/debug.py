#!/usr/bin/python3
import sys
from mido import MidiFile

mid = MidiFile(sys.argv[1])
for i, track in enumerate(mid.tracks):
    print("Track", str(i))
    for msg in track:
        print(msg)

