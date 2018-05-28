# Decadence
Plaintext music tracker and midi shell

Open-source under MIT License (see LICENSE file for information)

Copyright (c) 2018 Grady O'Connell

This is an early prototype of a plaintext music tracker.

I wanted to track music in my text editor because I'm quite fast with it.
The available options weren't good enough.
This is my attempt at making a column-oriented (vertical) music tracker
that works from a text editor and includes an interactive midi shell.

Vim plug-in: [vim-decadence](https://github.com/flipcoder/vim-decadence)

I currently test on Linux using qsynth.  Helm also works.

This is constantly being updated, so this readme may contain some old information (sorry)!

# Command line parameters (use -):

```
- (default) starts midi shell
- (filename): plays file
- c: play a given sequence
    - Passing "1 2 3 4 5" would play those note one after another
- l: play a multi-channel line
    - Not too useful w/o file context atm
- +: play range, comma-separated (+start,end)
    - Line numbers and marker names work
- t: start tempo
- x: start grid
- n: start note value
- c: columns
    - specify width and optional shift, instead of using auto-detect
    - positive shift values create a "gutter" to the left
    - negative values eat into the size of the first column
- p: set midi patches
    - command-separated list of patches across tracks
    - GM instruments names fuzzy match (Example: Piano,Organ,Flute)
- --sharps: Prefer sharps
- --solfege: Use solfege in output (input not yet supported)
- --flats: Prefer flats (currently default)
- --device=DEVICE: Set midi-device (partial match supported)
```

# Chord/Notes

```
- Note numbers, letters, roman numerals w/ sharps, flats and doubles
- Chord and common voicing names
- Slash chords and layering (eg. 1maj/b7 and )
    - Spread additional octaves by adding extra /
- Drop voicings (not yet impl)
```

# Global commands:

```
- %: set vars
- ;: comment
- :: set marker (requires name)
- @: go back to last marker, or start
- @@: pop mark, go back to last area
- @start: return to start
- @end: end song
- R: set scale (relative)
    - Scale and mode names suppored
- S: set scale (parallel)
    - Scale and mode names suppored
- P: set patch(s) across channels (comma-separated)
    - Matches GM midi names
    - Supports midi patch numbers
    - General MIDI name matching
```

# Track commands

```
- ': play in octave above
    - repeat for each additional octave (''')
    - for octave shift to persist, use a number instead of repeats ('3)
- ,: play in octave below
    - number provided for octave count, default 1 (,,,)
    - for octave shift to persist, use a number instead of repeats (,3)
- >: inversion (repeatable)
- <: lower inversion (repeatable)
- ch: assign track to a midi channel
    - midi channels exceeding max value will be multiplexed to different outputs
- pc: program assign
    - Set program to a given number
    - Global var (%) p is usually prefered for string matching
- cc: control change (midi CC param)
    - setting CC5 to 25 would be c5:25
- bs: bank select (not impl)
- ~: vibrato, currently set to mod wheel
- ": repeat last cell (ignoring dots, blanks, mutes, modified repeats don't repeat)
- *: set note length
    - defaults to one beat when used (default is hold until mute)
    - repeating symbol doubles note length
    - add a number for multiply percentage (*50)
- .: half note length
    - halfs note value with each dot
    - add extra dot for using w/o note event (i.e. during arpeggiator), since lone dots dont mean anything
    - add a number to do multiplies (i.e. C.2)
- !: accent a note (or set velocity)
    - set velocity by provided percentage
    - !! for louder notes
    - !! for louder accent
    - !! w/ number set future velocity
- ?: play note quietly (or set velocity)
    - repeat or pass value for quieter notes
- T: tuplet: triplets by default, provide ratio A:B for subdivisions
- ): delay: set note delay
- \: bend: (not yet implemented)
- &: arpeggio: plays the given chord in a sequence
    - infinite sequence unless number given
    - more params coming soon
- $: strum
    - plays the chord in a sequence, held by default
    - notes automatically fit into 1 grid beat

Note: Percentage values specified are formated like numbers after a decimal point:
Example: 3, 30, and 300 all mean 30% (read like .3, .30, etc.)

```
# The Basics

If you're familiar with trackers, you may pick this up quite easily.
Music flows vertically, with separate columns that are separated by whitespace or setting separators.

Each column is represents a track and they default to separate midi channel numbers.
Tracks sequence notes.  You'll usually play at least 1 track per instrument.
This doesn't mean you're limited to just one note per track though,
you can keep notes held down and play chords as you wish, using the right note effects.

By default, any note event in a track will mute previous notes on that track

Numbered notes, note letter names, and roman numerals are supported.

I've almost got the scale/mode system in (not yet impl).

The following will play the C major scale using numbered notation:
```
; Major Scale -- this is a comment, write whatever you want here!

; 120bpm subdivided into 2 (i.e., eighth notes)

%t120 x2

1
2
3
4
5
6
7
1'
```

The tempo is in BPM, and the grid is based in subdivisions.
Musicians can think of grid as fractions of quarter note,
The grid is the beat/quarter-note subdivision.

Both Tempo and Grid can be decimal numbers as well.

## Transposition and Octaves

Notice the bottom line has an extra apostrophe character (').  This plays the note in the next octave
For an octave below, use a comma (,).
If you prefer to have these octave shifts persist, the < and > symbols can be used instead.
You can use a number value instead to make the octave changes persistent.

## Holding Muting

Notes will continue playing automatically, until they're muted or another note is played in the same track.

You can mute all notes in a track with -

To control releasing of notes, use dash (-).  The period (.) is simply a placeholder, so notes continue to be played through them.
```

; 1 beat and then mute
1
.
.
.

; OR auto-mute with note value (*):
1*
.
.
.
 
; long note
1
.
.
-

```

Note durations can be controlled by adding * to increase value by powers of two, 
You can also add a fractional component to multiply this.
The opposite of this is the dot (.) which halves note values

```
; set note based on percentage (this means 30%)
1*3

; set note based on percentage (33%)
1*33

; set note based on percentage (33.3%)
1*333

; etc...
```


Notes that are played in the same track as other notes mute previous notes.
In order to overide this, hold a note by suffixing it with underscore (_).

A (-) character will then mute them all.

```
; Let's hold some notes
1_
3_
5_
7_
-
```

## Chord

You can choose to play notes separately in tracks, or use chords to put all
the notes in a single track.

Let's try some chords:

```
%t120 g2
1maj
2m
3m
4maj
5maj
6m
7dim
1maj'
```

There are lots of chords and voicing (check the .py file under CHORDS and CHORDS_ALT) and I'll be adding a lot more.
All scales and modes are usable as chords, so arpeggiation and strumming is usable with those as well.

# Arpeggios and Strumming

Chords can be walked if they are suffixed by '&'
Be sure to rest in your song long enough to hear it cycle.

```
1maj&
.
.
.
```

After the &, you can put a number to denote the number of cycles.
By default, it cycles infinitely until muted

The dollar sign is similar, but walks an entire chord or scale within a single grid space:
```
ionian$
```

# Velocity and Gain/Volume

Control velocity and volume of notes using the %v## or !## flags respectfully
Example: %v0 in min, %v9 is 90%.  But also: %v00 is minimum, %v99 is 99% (%v by itself is full)

Interpolation not yet impl
    
```
1maj%v9
-
1maj%v6
-
1maj%v4
-
1maj%v2
-
```

# Articulation

Tilda(~) is another command, but sets mod wheel value
It is intended to be used for vibrato.
Vibrato functionality will change to pitch wheel oscillation in the future

# Tracks

Columns are separate tracks, line them up for more than one instrument

```
1<2  1
.    4
.    5
.    1'
.    4'
.    5'
.    1'2
```
# Markers

still working on this feature, almost ready

':' sets marker and '@' loops to it.

```
:markername
@makername
```

Repeat counting, callstack, etc. coming shortly.  Code almost done.

# Tuplets

(Almost fully implemented)

Very early support for this. See tuplet.dc example.
The 't' command spreads a set of notes across a tuplet grid,
starting at the first occurence of t in that group.
Ratios provided will control expansion.  Default is 3:4.
If no denominator is given, it will default to the next power of two
(so 3:4, 5:8, 7:8, 11:16).
So in other words if you need a 5:6, you'll need to write t5:6. :)
The ratio of the beat saves.  You only need to specify it once per group.
For nested tripets, group those by adding an extra 't'.

Consider the 2 tracks:

```
1     1t
2     2t
3     3t
4
1     1t
2     2t
3     3t
4
```

The spacing is not even between the sets, but the 't' value stretches them
to make them even in a default ratio of 3:4

# What's the plan?

Not everything is listed here because I just started this project.
More to come soon!

Things I'm adding soon:

```
- Output to MIDI file
- A better scheduler to increase timing consistency
- Csound integration
    - Csound is decent for dabbling around when wanting somethnig better than GM
    - This is a good one because it doesn't require vsts and we can throw in our own instrument presets
- Text-to-speech and singing (Espeak/Festival)
    - I added this but had issues with timing and playback device issues
    - Once I fix, I'll add it back in
- Improved chord interpretation
```

Features I'm adding eventually:

```
- A way to display midi controller -> commands
- Midi controller recording to a track or file position
- Chord analysis
- (And finally...) Recording and encoding audio output of a project
```

I eventually will rewrite this in C++ to achieve better speed.
Until then, I'll make use of python's multiprocessing and possibly
separate processes to achieve as much as I can do for timing critical stuff.

>:)
