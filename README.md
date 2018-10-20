# textbeat

Plaintext music sequencer and interactive shell.

Write music in vim or your favorite text editor.

Open-source under MIT License (see LICENSE file for information)

![Screenshot](https://i.imgur.com/HmzNhXf.png)

Copyright (c) 2018 Grady O'Connell

- [Project Board](https://trello.com/b/S8AsJaaA/textbeat)
- Vim integration: [vim-textbeat](https://github.com/flipcoder/vim-textbeat)

**This project is still very new.  Despite number of features, you may quickly
run into issues, especially with editor integration.**

# Overview

Compose music in a plaintext format or type music directly in the shell.
The format is vertical and column-based, similar to early music trackers,
but with syntax inspired by jazz/music theory.

# Features

Textbeat is a new project, but you can already do lots of cool things:

- Strumming
- Arpeggiation
- Tuplets and polyrhythms
- MIDI CC automation
- Vibrato, pitch, and mod wheel control
- Dynamics
- Accents
- Velocity
- Inversions
- Midi channel stacking
- Note length
- Delays
- Scales and modes by name
- Markers, repeats, callstack

# Setup

You can use the shell with General Midi out-of-the-box on windows, which is great for learning,
but sounds bad without a decent soundfont.

I'm currently working on headless VST rack generation.

If you want to use VST instruments, you'll need to route the MIDI out to something that hosts them, like a DAW.

For windows, you can use a virtual midi driver, such as [loopMIDI](http://www.tobias-erichsen.de/software/loopmidi.html) for usage with a VST host or DAW.

If you're on Linux, you can use soundfonts through qsynth or use a software instrument like helm or dexed.  VSTs should work here as well.

If you feed the MIDI into a DAW you'll be able to record the output through the DAW itself.
I'm currently looking into recording via a headless host.

# Tutorial

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

## Note Numbers

Both note numbers and letters are supported.
This tutorial will use 1,2,3,4,5,6,7 instead of C,D,E,F,G,A,B.
I'm a fan of thinking about notes without implying a key.
For this reason, textbeat prefers the relative/transposed note numbers
over arbitrary note names.
If you're writing a song in D minor, you may choose to set the global or track key
to D, making D note 1. (You could also set D to 6 if you're thinking modally)
If this is confusing or not beneficial to you: don't worry, it's optional!

In this format, flats and sharps are prefixed instead of suffixed (b7 ("flat 7") instead of Bb ("B flat")).

Be aware that this flexibility introduces a few limits with chord names:
- B7 chords should not be written as 'b7', because this means flat 7
- 7 is a note when used alone, not a chord:
    - Write it as dom7
    - Alternatively write 1:7, R7, or C7
- 27 is not a 7 chord on 2, it's note 27
    - Write it as 2:7 or 2dom7

## Transposing Octaves

In the first example, the apostrophe character (') was used to play the note in the next octave.
For an octave below, use a comma (,).

Repeat these for additional octaves (,,, for 3 down, '' for 2 up, etc).

To make octave changes persist, use a number for the octave count instead of repeating (,2).

## Holding Muting

Notes will continue playing automatically, until they're muted or another note is played in the same track.

You can mute all notes in a track with -

To control releasing of notes, use dash (-).
```

; hold note 1 until next note
1
 
 
 

; auto-mute by specifying note value (*):
1*
 
 
 
 
; manually mute with '-'
1
 
 
-

```

Note durations can be manually controlled by adding * to increase value by powers of two, 
You can also add a fractional value to multiply this.  These types of fraction
values are used throughout textbeat.
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

Now with dots for staccato:

```
1.

1..

1.30
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

## Chords

Unlike traditional trackers, you can write chords directly: 1maj or Cmaj.
1 ('C') is not required here. as chords without note names are positioned on 1
('C') (ex. "maj" = "Cmaj" = "1maj").
Other shorthand names that work: "ma", "major", "M", or roman numeral "I"

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

There are lots of chords and voicings (check def/ files) and I'll be adding a lot more.
All scales and modes are usable as chords, so arpeggiation and strumming is usable with those as well.

Remember: The note goes *before* the chord, so 7maj is a maj chord on note 7 (i.e. Bmaj), NOT a maj7.

## Arpeggios and Strumming

Chords can be walked if they are suffixed by '&'
Be sure to rest in your song long enough to hear it cycle.

```
maj&
 
 
 
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

## Velocity and Accents

Use a ! or ? to accent or soften a note respectively.

You can use these on arpeggios as well.

```
1!
2?
3
4?
1!
2?
3
4?
```

Use values after accent to set a specific velocity:

```
1!!    # 100%
1!90
2!75
3!5    # 50%
4!333  # 33.3%
5!05   # 5%
```

## Note grouping

For readability, notes can be indented to imply downbeat or grouping

```
1
 2
 3
 4
1
 2
 3
 4
```

## Volume

Usually you'll want to control velocity through accenting('!') or softening('?')
or using values (!30 for 30%)

If you wish to control volume/gain directly, use @v
 
```
1maj@v9
-
1maj@v6
-
1maj@v4
-
1maj@v2
-
```

Unlike accents, volume changes persist.

Interpolation is not yet impl

## Vibrato, Pitch, and Mod Wheel

To add vibrato to a note, suffix it with a tilda (~).

Vibrato uses the mod wheel right now, but will eventually use pitch wheel oscillation.

In the future, articulation will be programmable, per-track or per-song.

## Arpeggio Modulation

Notes of arpeggios can be modified as they're running,
by having effects in the grid space they occur, for example:

```
maj7&
 .?
 .?
 .?
!
 .?
 .?
 .?
```

maj7& starts a repeating 4-note arpeggio, and we indent to show this.

Certain notes of the sequence are modulated with short/staccato '.', soft '?', and accent '!'

For staccato usage w/o a note name, an extra dot is required since '.' is simply a placeholder.

## Tracks

Columns are separate tracks, line them up for more than one instrument.

The dots are placeholders.

```
1,2  1
.    4
.    5
.    1'
.    4'
.    5'
.    1''
```

Columns can be detected (in some cases), but you'll probably want to 
specify the column width manually at the top,
which allows vim to mark the columns.

```
# sets column width to 8
%c=8
```

For best view in an editor, it is recommended that you offset the first column by -2:

```
# sets column width to 8, offset -2
%c=8,-2
```

## Patches

Another useful global var is 'p', which sets midi patches by name or number
across the tracks.  The midi names support both patch numbers and partial case-insensitive
matches of GM instruments.

```
%t120 x2 p=piano,guitar,bass,drums c8,-2
```

For a full list of GM names, see [def/gm.yaml](https://github.com/flipcoder/textbeat/blob/master/config/gm.yaml).

## Tuplets

The 'T' (tuplet) gives us access to the musical concept of tuplets (called triplets in cases of 3).
which allows note timing and durations to fall along a ratio instead of the usual note subdivisions.

Tuplets are marked by 'T' and have an optional value at the first occurence in that group.
Ratios provided will control expansion.  Default is 3:4.
If no denominator is given, it will default to the next power of two
(so 3:4, 5:8, 7:8, 11:16).
So in other words, T5 is the same as T5:8, but if you need a 5:6, you'll need to write T5:6.
The ratio of the tuplet persists for the rest of the grouping.
For nested tripets, group those by adding an extra 'T'.

The two tracks below are a basic usage of triplets:

```
1     1T
2     2T
3     3T
4
1     1T
2     2T
3     3T
4
```

The first column is playing notes along the grid normally, while the
2nd column is playing 3 notes in the space of the others' 4 notes.

Even though there is visual spacing between the triplet groups, the 'T' value effective
stretches the notes so they occur along a slower grid according to that ratio.

The spaces that occur after (and between) tuplet groupings should remain empty,
since they are spacers to make the expansion line up.

## Picking

[Currently designing this feature](https://trello.com/c/D01rlTWp/26-picking)

## Key changes

```
# change key (this will change the key of the current scale to 3 (E))
%k=3

# to set a relative key, this will go from a major scale to relative minor scale
%k+6

# you can also go downwards
%k-6

# scale names are supported, this changes the scale shape to dorian
%s=dorian

# you can also use mode numbers
%s=2
```

## Chords (Advanced)

In textbeat, slash (/) chords do not imply inversions,
but are for spanning chord voicings across octaves.  Additionally, note names alone do no imply chords.
For example, C/E means play a C note with an E in a lower octave, whereas a musician might
interpret this as a specific chord voicing.  Inversions in textbeat uses shift operator (>) instead (maj> for maj first inversion))

```
b7maj7#4/sus2/1
# same thing with note names: Bbmaj7#4/Csus2/C
# suffix this with & to hear the notes walked individually
```

The above chord voicing spans 3 octaves and contains 9 notes.
It is a Bbmaj7 chord w/ an added #4 (relative to Bb, which is E), followed by a lower octave Csus2.
Then at the bottom, there is a C bass note.

## Examples

Check out the examples/ folder.  Play them with textbeat from the
command line:

```
./txbt examples/jazz.txbt
``` 

# Advanced

## Markers / Repeats

Here are the marker/repeat commands:

```
- |: set marker
- |name: set marker 'name'
- :| goes back to last marker, or start
- :name| goes back to last marker 'name'
- :N| goes back to last marker N number of times
- :name*N| goes back to last marker 'name' N number of times
- || return/pop to last position after marker jump
- ||| end the song here
``` 

## Command line parameters (use -):

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

## Global commands:

```
- %: set var (ex. %P=piano T=120x2 S=dorian)
    - K: set key/transpose
        - Both absolute and relative values supported
        - Relative values are 1-indexed using numbered note name
            - whole step: %k+2 whole step
            - half step: %k+#1 or %k+b2
            - invalid example (because of 1-index): %k+1
    - O: set global octave
    - R: set scale (relative)
        - Names and numbers supported
    - S: set scale (parallel)
        - Names and numbers supported
    - P: set patch(s) across channels (comma-separated)
        - Matches GM midi names
        - Supports midi patch numbers
        - General MIDI name matching
- ;: comment
- ;;: cell comment (not yet impl)

To do relative values, drop the equals sign:
%k-2
```

## Track commands

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
- `: mod
- ch: assign track to a midi channel
    - midi channels exceeding max value will be spanned across outputs
- p: program assign
    - Set program to a given number
    - Global var (%) p is usually prefered for string matching
- c: control change (midi CC param)
    - setting CC5 to 25 would be c5:25
- q: play recording
- Q: record
- midi cc mappings
    - bs: bank select (not impl)
    - at: aftertouch
    - bc: breath controller
    - fc: foot controller
    - pt: portamento time
    - v: volume
    - bl: balance
    - pn: pan
    - e: expression
    - ga: general purpose CC 16
    - gb: " 17
    - gc: " 18
    - gd: " 19
    - sp: sustain pedal
    - ps: portamento switch
    - st: sostenuto pedal
    - sf: soft pedal
    - lg: legato pedal
    - hd: hold w/ release fade
    - o: oscillator
    - R: resonance
    - r: release
    - a: attack
    - f: filter
    - sa: sound ctrl
    - sb: " 2
    - sc: " 3
    - sd: " 4
    - se: " 5
    - pa: portmento amount
    - rv: reverb
    - tr: tremolo
    - cr: chorus
    - ph: phaser
    - mo: mono

Track commands that start with letters should be separated
from notedata by prefixing '@':
Example: 1~ is fine, but 1v is not. Use 1@v You only need one to combine: 1@v5e5

Note: Fractional values specified are formated like numbers after a decimal point:
Example: 3, 30, and 300 all mean 30% (read like .3, .30, etc.)

CC mapping is customizable inside [def/cc.yaml](https://github.com/flipcoder/textbeat/blob/master/textbeat/def/default.yaml).

```

## Scales, Modes, Chords, Voicings

```
# note: some of these features are not finished

- < or >: inversion suffix
    - ex: maj> means maj 1st inversion
    - repeatable (ex. maj>> means 2nd inversion: 5 1' 3' or G C' E')
        - or specify a number (like maj>2), meaning 2nd inversion (this will be useful for scale modes later)
- /: slash: layer chords across octaves (note: different from music theory interpretation)
    - repeat slash for multiple octaves (ex. maj//1)
- add (suffix), add note to chord (ex. maj7add11)
- no (suffix): remove a note by number
- |: stack: combines chords/notes manually (ex. maj|sus|#11)
```

## Defs

A majority of the music index is contained in inside these files:

- Default: [def/default.yaml](https://github.com/flipcoder/textbeat/blob/master/textbeatdef/default.yaml).
- Informal: [def/informal.yaml](https://github.com/flipcoder/textbeat/blob/master/textbeat/def/informal.yaml).
- Experimental: [def/exp.yaml](https://github.com/flipcoder/textbeat/blob/master/textbeat/def/exp.yaml).

These lists does not include certain chord modifications (add, no, drop, etc.).

# What else?

I'm improving this faster than I'm documenting it.  Because of that, not everything is explained.

Check out the project board for more information on current/upcoming features.

Also, check out the basic examples in the examples/ and tests/ folder.

# What's the plan?

Not everything is listed here because I just started this project.
More to come soon!

Things I'm planning on adding soon:

```
- Improved chord interpretation
- MIDI input/output
- MIDI stabilization
- Headless VST rack integration
- Csound and supercollider instrument integration
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

Yes!  Contact [flipcoder](https://github.com/flipcoder).

