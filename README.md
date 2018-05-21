# Decadence
Plaintext music tracker and shell

Copyright (c) 2018 Grady O'Connell

Status: Just started. Still prototyping.

I wanted to track music in my text editor because I'm quite fast with it.
The available options weren't good enough.
This is my attempt at making a column-oriented, music tracker that works from
a text editor and includes an interactie midi shell.

I plan to make a vim plugin for this as well to follow the song and hear individual sections (see integration.vim for temporary usage)

Currently I test on Linux using the Helm and qsynth

NOTE: I'll probably rewrite this in C++ once I'm done prototyping, as python isn't the best choice for audio :)

# Overview

If you're familiar with trackers, you should pick this up quite easily.
Music flows vertically, with separate columns that are separated by whitespace or setting separators.

Each column is a "channel" and they default to separate midi channel numbers.
Channels sequence notes.  You'll usually play at least 1 channel per instrument.
This doesn't mean you're limited to just one note per channel though,
you can keep notes held down and play chords as you wish, using the right note effects.

By default, any note event in a channel will mute previous notes on that channel

Numbered notes, note letter names, and roman numerals are supported.

I've almost got the scale/mode system in (not yet impl).

The following will play the C major scale using numbered notation:
```
; Major Scale -- this is a comment, write whatever you want here!

; 120bpm subdivided into 2 (i.e., eighth notes)

%t120 g2

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
Grid is the beat subdivision.

Both Tempo and Grid can be decimal numbers as well.

## Transposition and Octaves

Notice the bottom line has an extra apostrophe character (').  This plays the note in the next octave
For an octave below, use a comma (,).
If you prefer to have these octave shifts persist, the < and > symbols can be used instead.
You can add a number at the end of these to increase the shift (For example, >2 puts 2 octaves above and persists).

## Holding Muting

Notes will continue playing automatically, until they're muted or another note is played in the same channel.

You can mute all notes in a channel with -

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
; set note length to fraction
1*3

; set note based on percentage (33%)
1*33
```


Notes that are played in the same channel as other notes mute previous notes.
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


You'll notice completely blank lines are ignored, so be careful to always have a dot if you want the row to take time to play

## Chord

You can choose to play notes separately in channels, or use chords to put all
the notes in a single channel.

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

# Velocity and Gain/Volume

Control velocity and gain of notes using the v## or g## flags respectfully
Example: v0 in min, v9 is 90%.  But also: v00 is minimum, v99 is 99% (v by itself is full)

Interpolation not yet impl
    
```
1majv9
-
1majv6
-
1majv4
-
1majv2
-
```

# Articulation

Tilda(~) is another command, but sets mod wheel value
It is intended to be used for vibrato.
Vibrato functionality will change to pitch wheel oscillation in the future

# Channels

Columns are separate channels, line them up for more than one instrument

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

not yet impl

# Commands

Command line parameters (use -):

- c: issue command
- l: play a single line (string)

Command line AND global (% line) variables:
- t: start tempo
- g: start grid
- n: start note value
- p: set midi patches
    - command-separated list of patches across channels
    - GM instruments names fuzzy match (Example: Piano,Organ,Flute)

Global commands:

- %: set vars
- ;: comment
- :: set marker (requires name)
- @: go to mark
- @@: pop mark, go back to last
- @@@: exit
- |: set separators
    - allows you to draw separate each column by a fixed size
    - allows you to have spaces in note events on the same channel

Channel commands:

- >: shift octave up (persists)
    - number provided for octave count, default 1
- <: shift octave down (persists)
    - number provided for octave count, default 1
- ': play in octave above
    - number provided for octave count, default 1
- ,: play in octave below
    - number provided for octave count, default 1
- ch: assign channel to a midi channel
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
    - defaults to one beat when used
    - repeating symbol doubles note length
    - add a number to do multiplies (i.e. .5)
- .: half note length
    - halfs note value with each dot
    - add extra dot for using w/o note event (i.e. during arpeggiator), since lone dots dont mean anything
    - add a number to do multiplies (i.e. C.2)
- !: accent a note (or set velocity)
    - repeat for louder notes
- ?: play note quietly (or set velocity)
    - repeat for quieter notes

That's all I have so far!

