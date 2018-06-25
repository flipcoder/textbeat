# Decadence
Plaintext music tracker and midi shell.
Write music in vim or your favorite text editor.

Open-source under MIT License (see LICENSE file for information)

![Decadence](https://imgur.com/N3yNWyJl.png)

Copyright (c) 2018 Grady O'Connell

- [Gitter Chat](https://gitter.im/flipcoder/decadence)
- [Project Board](https://trello.com/b/S8AsJaaA/decadence)
- Vim integration: [vim-decadence](https://github.com/flipcoder/vim-decadence)

# Overview

Compose music in a plaintext format or type music directly in the shell.
The format is vertical and column-based, similar to early music trackers,
but with syntax inspired by jazz/music theory.

This project is still very new.  Despite number of features, you may quickly
run into issues.  Feel free to [communicate](https://gitter.im/flipcoder/decadence) your experiences to me.

# Features

Decadence is a new project, but you can already do lots of cool things:

- Strumming
- Arpeggiation
- Tuplets and polyrhythms
- CC automation
- Vibrato, pitch, and mod wheels
- Dynamics
- Accents
- Velocity
- Inversions
- Midi channel stacking
- Note length
- Delays
- Markers, repeats
- Scales and modes by name

# Setup

You can use the shell with General Midi out-of-the-box on windows, which is great for learning,
but sounds bad without a decent soundfont.

If you want to use VST instruments, you'll need to route the MIDI out to something that hosts them, like a DAW.

For windows, you can use a virtual midi driver, such as [loopMIDI](http://www.tobias-erichsen.de/software/loopmidi.html) for usage with a VST host or DAW.

If you're on Linux, you can use soundfonts through qsynth or use a software instrument like helm or dexed.  VSTs should work here as well.

If you feed the MIDI into a DAW you'll be able to record the output through the DAW itself.
I'm currently looking into recording via a headless host.

# Command line parameters (use -):

```
- (default) starts midi shell
- (filename): plays file
- c: play a given sequence
    - Passing "1 2 3 4 5" would play those note one after another
- l: play a single line from the file
    - Not too useful yet, since it doesn't parse context
- +: play range, comma-separated (+start,end)
    - Line numbers and marker names work
- t: tempo
- x: grid
- n: note value
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

# Global commands:

```
- %: set var (ex. %P=piano T=120x2 S=dorian)
    - R: set scale (relative)
        - Names and numbers supported
    - S: set scale (parallel)
        - Names and numbers supported
    - P: set patch(s) across channels (comma-separated)
        - Matches GM midi names
        - Supports midi patch numbers
        - General MIDI name matching
- ;: comment
- :: set marker (requires name)
- @: go back to last marker, or start
- @@: pop mark, go back to last area
- @start: return to start
- @end: end song

Future: Repeat and region markers may be changed to '|:' and ':|' symbols.
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
    - future: will be moved from track commands to chord parser
- <: lower inversion (repeatable)
    - future: will be moved from track commands to chord parser
- ch: assign track to a midi channel
    - midi channels exceeding max value will be spanned across outputs
- pc: program assign
    - Set program to a given number
    - Global var (%) p is usually prefered for string matching
- cc: control change (midi CC param)
    - setting CC5 to 25 would be c5:25
- bs: bank select (not impl)
- ~: vibrato and pitch wheel
- `: mod wheel
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

Note: Fractional values specified are formated like numbers after a decimal point:
Example: 3, 30, and 300 all mean 30% (read like .3, .30, etc.)

```
# Chord Parsing

```
- /: slash: layer chords across octaves (note: different from music theory interpretation)
    - repeat slash for multiple octaves (ex. maj//1)
- add (suffix), add note to chord (ex. maj7add11)
- no (suffix): remove a note by number
- |: stack: combines chords/notes manually (ex. maj|sus|#11) (not yet impl)
- < or >: inversion suffix, repeatable (ex. maj>> means 5 1' 3' or G C' E')
```

# The Basics

If you're familiar with trackers, you may pick this up quite easily.
Music flows vertically, with separate columns that are separated by whitespace or
manually setting a column width.

Each column represents a track, which defaults to separate midi channel numbers.
Tracks play sequences of notes.  You'll usually play at least 1 track per instrument.
This doesn't mean you're limited to just one note per track though,
you can keep notes held down and play chords as you wish.

Each cell row in a track can contain both note data and associated effects.

By default, any note event in a track will mute previous notes on that track

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
You can use a number value instead to make the octave changes persistent (,2).

## Holding Muting

Notes will continue playing automatically, until they're muted or another note is played in the same track.

You can mute all notes in a track with -

To control releasing of notes, use dash (-).  The period (.) is simply a placeholder, so notes continue to be played through them.
```

; hold note 1 until next note (dots aren't notes, just empty placeholders for example)
1
.
.
.

; auto-mute by specifying note value (*):
1*
.
.
.
 
; manually mute with '-'
1
.
.
-

```

Note durations can be manually controlled by adding * to increase value by powers of two, 
You can also add a fractional value to multiply this.  These types of fraction
values are used throughout decadence.
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

Notes that are played in the same track as other notes mute the previous notes.
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

If you want to hold a series of notes like a sustain pedal, simply use two underscores (__)
and all future notes will be held until a mute is received.

## Chord

You can play notes individually or use chord names.

Let's play a scale with some chords:

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

There are lots of chords and voicings (check config/def.yaml) and I'll be adding a lot more.
All scales and modes are usable as chords, so arpeggiation and strumming is usable with those as well.

# Arpeggios and Strumming

Chords can be walked if they are suffixed by '&'
Be sure to rest in your song long enough to hear it cycle.

```
maj&
.
.
.
```

After the &, you can put a number to denote the number of cycles.
By default, it cycles infinitely until muted (or until the song ends)

The dollar sign is similar, but walks an entire set of notes within a single grid space:
```
maj$
```
Scales and modes are also accessible the same way:

```
dorian$
```

To strum, use the hold (_) symbol with this.

```
maj$_
```

# Accents

Use a ! or ? to accent or soften a note respectively.

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

Tilda(~) does vibrato.
Vibrato uses the mod wheel right now, but will eventually use pitch wheel oscillation.

In the future, articulation will be programmable, per-track or per-song.

# Tracks

Columns are separate tracks, line them up for more than one instrument

```
1,2  1
.    4
.    5
.    1'
.    4'
.    5'
.    1''
```

# Markers

Still working on this feature, it might be broken

':' sets marker and '@' loops to it.

```
:markername
@makername
```

Repeat counting, callstack, etc. coming shortly.  Code almost done.

# Tuplets

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
to make them line up in a default ratio of 3:4.

# Notes

In a traditional tracker, individual notes would take place over multiple
channels.  You can do this in decadence if it fits your writing style,
but it is not the only way.

For instance, a C major chord would be specified in a way a
computer would understand it: 3 notes across 3 separate channels: C,E,G (or 1,3,5).
Writing this in a tracker with 1 note per channel is specific enough for a computer,
but annoyingly lacking context from the perspective of a performer.

In decadence, you can write the chord directly: 1maj or Cmaj.
1 (C) is not required here. as chords without note names are positioned on 1 (C) (ex. "maj" = "Cmaj" = "1maj").
Other shorthand names that work: "ma", "major", "M", or roman numeral "I"

So, you may find yourself writing a huge voicing spanning octaves like this:

b7maj7#4/sus2/1

(same thing with note names: Bbmaj7#4/Csus2/C)
    
(suffix this with & to hear the notes walked individually)

The above chord voicing spans 3 octaves and contains 9 notes.
It is a Bbmaj7 chord w/ an added #4 (relative to Bb, which is E), followed by a lower octave Csus2.
Then at the bottom, there is a C bass note.
As cryptic as it may seem to non-musicians, condensed chord voicings are going
to make more sense to your ear over time than seeing random note letters fly by.
To build an association between the chords and how they sound,
you can type these directly into the decadence shell.

I'm a fan of thinking about music and chords in a relative way that is not dependent on key.
For this reason, decadence prefers relative note numbers/names
over arbitrary note names (even though both are valid).

If you're writing a song in D minor, you will want to set the global or track key
to D, making D note 1. (You could also set D to 6 if you're thinking modally)
If this is confusing or not beneficial to you: don't worry, it's optional!

Note to musicians: There are a few quirks with the parser that make the chord interpretation different than
what musicians would expect.  For example, slash chords do not imply inversions,
but are for stacking across octaves.  Additionally, note names alone do no imply chords.
For example, C/E means play a C note with an E in a lower octave, whereas a musician might
interpret this as a specific chord voicing.  (Inversions use shift operator (maj> for first inversion))

# Full list of scales, modes, chords, and voicings

- Default: [def/default.yaml](https://github.com/flipcoder/decadence/blob/master/def/default.yaml).
- Informal: [def/informal.yaml](https://github.com/flipcoder/decadence/blob/master/def/informal.yaml).
- Experimental: [def/dc.yaml](https://github.com/flipcoder/decadence/blob/master/def/dc.yaml).

These lists does not include certain chord modifications (add, no, drop, etc.)

# What else?

I'm improving this faster than I'm documenting it.  Because of that, not everything is explained.

Check out the project board for more information on current/upcoming features.

Also, check out the basic text examples in the test/ folder.

# What's the plan?

Not everything is listed here because I just started this project.
More to come soon!

Things I'm planning on adding soon:

```
- Improved chord interpretation
- MIDI input/output
- MIDI stabilization
- Headless VST rack integration
- Csound and Sonic Pi instrument integration
- libGME for classic chiptune
- Text-to-speech and singing (Espeak/Festival)
```

Features I'm adding eventually:

```
- Recording and encoding output of a project
- Midi controller input and recording
- Midi input chord analysis
- MPE support for temperment and dynamic tonality
```

I'll be making use of python's multiprocessing or
separate processes to achieve as much as I can do for timing critical stuff
without doing a C++ rewrite.

# Can I Help?

Yes!  Join the [chat](https://gitter.im/flipcoder/decadence) or contact [flipcoder](https://github.com/flipcoder).

