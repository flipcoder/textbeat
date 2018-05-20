# Decadence
Use your text editor as a music tracker

Copyright (c) 2018 Grady O'Connell

I wanted to track music in my text editor because I'm quite fast with it.
The available options weren't good enough.
This is my attempt at making a column-oriented, music tracker that works from
a text editor.

I plan to make a vim plugin for this as well to follow the song and hear individual sections

If you're using this with vim, set virtualedit=all to edit beyond EOL

Status: Just started this!  More features soon, currently very prototypish.

## Features

- Implemented
    - Numbered and lettered note notation
    - Built-in chords
    - Velocity, Transposition, Vibrato
    - Note holding
    - Chord and Voicing support
    - Markers w/ Callstack (use :name to set, and @name to jump, @@ to return)
    - MIDI CC events
    - Chord Arpeggiator
- Planned
    - Scales and key signature (not yet impl)

## Tutorial

INCOMPLETE
    
Each column is called a channel (not to be confused with midi channel).
Channels sequence notes.  
By default, any note event in a channel will mute previous notes on that channel

Separate each column by at least 2 spaces.

Numbered note notation is encouraged as it can better support
transposition and can take advantage of the scale/mode system (not yet impl).

The following will play the C major scale using numbered notation:
```
; Major Scale -- this is a comment, write whatever you want here!

; 120bpm subdivided into 2 (i.e., eighth notes)
%tempo=120 grid=2

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
whereas grid=1 is quarter, grid=2 is eighth notes, grid=3 is eighth triplet, etc.

Both Tempo and Grid can be decimal numbers as well.

## Transposition and Octaves

Notice the bottom line has an extra apostrophe character (').  This plays the note in the next octave
For an octave below, use a comma (,).
If you prefer to have these octave shifts persist, the < and > symbols can be used instead.
You can add a number at the end of these to increase the shift (For example, >2 puts 2 octaves above and persists).

## Holding Muting

Notes will continue playing automatically, until they're muted or another note is played in the same channel.

You can mute notes with -

To control muting of notes, use Dash (-).  The period (.) is simply a placeholder, so notes continue to be played through them.
```

; short note
1
-

; long note
1
.
.
.
-

```

Notes that are played in the same channel as other notes mute previous notes.
In order to overide this, hold a note by suffixing it with underscore (_).

A (-) character will then mute them all.

```
; Let's hold some notes
%tempo
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
%tempo=120 grid=2
1maj
2m
3m
4maj
5maj
6m
7dim
1maj'
```

