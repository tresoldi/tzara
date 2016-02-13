# The Tzara Engine

## Basics

The Tzara Engine is a system for the generation of text from a
specification, based on the principle of *recursive transition
networks* or *recursive grammars*. In particular, the Tzara Engine
is well suited for natural language generation, as the its
specifications (sets of rules in the form of a grammar) allow both
deterministic and non-deterministic results. The Tzara Engine is
heavily inspired and almost compatible with the Dada Engine, a
system developed in 1995--6 by Andrew C. Bulhak, and was developed
as a single-file Python module, oriented by the principle of
KISS (Keep It Simple, Stupid) and the possibility of future
translation or transpilation in other programming languages; it
should be considered a software toy.

While this software does not include any actual code from the Dada Engine,
it is in part compatible with it, and this documentation includes parts of
and expands the manual for the Dada Engine.

This system must be considered a software toy, in a very beta stage.
I wrote in one long afternoon to solve a different problem, and only
decided to make it public after realizing that it was still better of
nothing (considering the dozens of people that asked me for help with
an horrible, similar JavaScript module I wrote in 2008). Feel free to
contribute and, in particular, to curse the internal cache system (the one
that should guarantee that no rule gerates the same output twice in
a row).

### Overview

The Dada Engine is based on the principle of *recursive transition
networks*, or *recursive grammars*. A recursive transition network (RTN) is
a diagram which shows how a task, such as the construction of a sentence,
may be carried out. A RTN consists of paths which may be followed and of
operations along these paths which must be carried out.

These recursive transition networks are represented in text as rules; one
example of RTN, for a random adjective, is the following:

```
adjective: "large" | "big" | "narrow" | "small";
```

A collection of rules makes up a *grammar*, which defines the space of
possible sentences. For exemple, the grammar below allows the generation of
sentences such as `I like apples` and `You love oranges`:

```
sentence: pronoun verb fruit;
pronoun: "I" | "You";
verb: "like" | "love";
fruit: "apples" | "oranges";
```

To define a system of RTNs or rules to the Dada Engine, write it in the
notation specified in this manual (the language known as `pb`) in an utf-8 or
ASCII text file; this file is known as a script. Please remember that, while
similar and to some extent compatible, this `pb` language is different from
the one used in the Dada Engine.

## The evaluation process

When you start the Tzara Engine, you do so with the `tzara` command, where the
first argument is the file containing the grammar and the second, optional,
argument the rule to generate from (if no rule is specified, the engine will
output the parsed grammar, mostly for inspection and debugging). 

```
$ ./tzara.py myscript.pb rule
```

The command reads the complete input before it emits anything. Once it has
read everything, it evaluates the optionally specified rule (also known as
the start symbol); in turn, this causes any rules invoked from the initial
rule to be evaluated.

As the rules are evaluated, the text generated is appended to a buffer in
memory; once everything has been evaluated, the buffer's contents are
emitted.

# The `pb` language

## Lexical elements

### Comments

Comments in `pb` are handled as in Python. A comment of any length may be enclosed between an hashtag symbol and the end of the line. Please rememeber
that C++/Java style comments, as used in the Dada Engine, are *not* supported.

The following are valid comments:

```
# This is a two-line comment.
# See?

alpha = "a" | "b"; # You are not expected to understand this.
```
### Identifiers

An identifier in `pb` is any sequence of letters, digits, underscores
and hyphens which starts with a letter or underscore.
Identifiers are case-sensitive. 

The following are valid identifiers:

```
futplex

sort-of-vague-ambiguous-noun

_298R
```

*(Please note: in this beta version of the Engine, the identifiers are not
checked and, in fact, you pretty much can use any non space and non colon
character in their names; however, it is strongly recommended to limit to
the definitio above)*

### Literal strings

A literal string in `pb` is any sequence of characters embedded in quotes.
A string may contain unquoted newlines. The backslash character serves a
similar function as in C, but in the Tzara Engine it is only used to escape
quotes and backslash characters: any special meanings depends on the Python
handling of the string.

The following are valid literal strings:

```
"Hello, world!"
"He said \"Hello\" to her."
"You can escape backslashes with \\."
```

## Grammars and rules

### Atoms

Atoms are the building blocks of rules. Each atom is a self-contained element
which performs a function, usually generating text.

Atoms are divided into several types. These are: 

* Literal text

A literal text atom consists of a sequence of characters enclosed by double
quotes.

Examples:

```
"foo"

"\"Come into my parlour,\" said the spider to the fly."

"Friends, Romans, Countrymen,\nLend me your ears"
```

* Symbols

A symbol is an atom which names a rule to be evaluated. A symbol name
may be any sequence of letters, digits, underscores and hyphens with
the restriction that the first character must be a letter or an underscore.
Symbol identifiers are not enclosed by quotes. The following are examples
of possible symbol names:

```
foo

noun2

abstract-adjective
```

### Declaring grammatical rules

In `pb`, the form of a rule declaration is:

```
rule: <rulename>;

rule: <literal>;

rule: <rule> | <rule> *(| ...)*;
```

If a rule has several options, one will be selected randomly at the time of
evaluation. The atoms of the chosen option will be evaluated in sequence and
their results joined into a string, which shall be returned as the result of
the rule.

For example, in the following grammar:

```
sentence: "The ball is " colour "." ;

colour: "red"
        | "green"
        | "blue"
;
```

`colour` will evaluate to either "red", "green" or "blue"; hence, sentence
will evaluate to "The ball is red.", "The ball is green.", or "The ball
is blue." Please note that the Tzara Engine does *not* have inline choices
as the Dada Engine.

The Dada Engine manual state that if a rule has several options, the same
option will never be chosen twice in immediate succession. This
does not seem to be true in the code available, but it *is* true for the
Tzara Engine up to a limit. The Tzara Engine implements a (rudimentary and
that should be replaced, but working) cache system that keeps a list of
the previous calls to a rule, calculating its entropy at each call to check
if it is probable that a different output can be generated -- the hard part,
probably the source of the limitation in the Dada Engine, is that without
a brute forcing it is impossible to be sure of the universe of outputs of
a rule, considering the randomness of the calls and, in particular, the
recursiveness (a rule can call itself, directly or indirectly). For the user,
it is enough to know that the engine will try not to generate the same
output in immediate sucession if reasonably possible.

The Tzara Engine has an innovation in comparison to the Dada Engine, the
weight of options. Each option has a "weight" that indicates how probable
its random selection should be. The default value, is 1 and the syntax uses
the % symbol. Thus, in:

```
letter: "a" % 2 | "b" % 10 | "c";
```

the weights for "a", "b" and "c" are, respectively, two, ten and one, with
"a" being twice as likely to be generated as "c" and "b" being five times as
likely as "a" and ten times as likely as "c". The weight must be an
integer number. This syntax replaces the `*` and `+` operators of the Dada
Engine, making it much easier to write scripts.

### Variables

The language of the Dada Engine allowed to use *variables*. These are not
available in the Tzara Engine, but with a similar syntax you can create
(and manipulate) *rules*.

The two available operations are *set* and *override*: with *set* a rule
is never changed, but created if it does not exist. You can use it to store
a recurring part of a text, such as the name of an author in the
Post-Modernist generator.

With *override*, a rule is changed (or created, if necessary) no matter its
previous value.

```
sent1: "I like " favorite<artist;
sent2: "I like " favorite<<artist;
artist: "Burroughs" | "Joyce" | "Gibson"
	| "Stone" | "Pynchon" | "Spelling" | "Tarantino" | "Madonna" 
	| "Rushdie" | "Eco" ;
```

In the `sent1`, the new rule `favorite` is set the first time the rule is
generated, and its value does not change no matter how many times the rule is
called. In `sent2` (note that we have two `<` signs, and not one), the value
(i.e., the generated output) of favorite is changed each time the rule is
called.

One interesting feature is that you can "silence" a *set* or an *override*, by
appending a quotation mark: the operation will be performed, but no text
will be generated. This is particularly useful for the emulation of
parametric rules, as below.

### Parametric rules

The Tzara Engine does *not* support parametric rules, as the Dada Engine.
However, given the availability of silent *set* and *override* operations,
these can be simulated with the following idiom, that gives much more
power to the writer of a grammar:

```
sent: ?favorite<<artist "He said he " sent-on-artist "; " but-who;
sent-on-artist: verb favorite;
verb: "likes" | "loves";
but-who: "but who doesn't like " favorite "?";
```

Here, when `sent` is called, the engine first selects an `artist` and
overrides `favorite` (if it exists), but without generating actual textual
output. When `sent-on-artist` and `but-who` are called, the information
will be available to integrate in the output when and where needed. You can
specify local identifiers to make sure there is no collision among rules.

# Indirection

Indirection allows the output of a rule to be used as the name of another
rule. This is useful when the ranges of valid choices are influenced by a
prior choice, and complements what is offered by parametric rules. In the
Tzara Engine, the output of a rule can be captured as part of the name 
of a second rule with curly brackets (`{` and `}`), like in the following
translation grammmar:

```
colorname: "red" | "green" | "blue";
spanish-red: "rojo";
spanish-green: "verde";
spanish-blue: "azul";
sent: "Me gusta el " spanish-{colorname};
```

## Transforming text

The Tzara Engine does not have the mapping and transformation tools of
the Dada Engine. Mappings can be replaced by indirection, and textual
transformations are replaced by coded transformation functions,
that can be called in succession when needed. For the time being, only
basic textual manipulations and functions specific to the English
language.

These functions are, with examples of their usages:

* upper - converts the string literal to upper case (`test` becomes
`TEST`)
* lower - converts the string literal to lower case (`TEST` becomes
`test`)
* upcase-first - converts the first character of the string literal
to upper case (`test` becomes `Test`, `teST` becomes `TeST`)
* capitalize - converts the first character of the string literal to upper
case and all other characters to lower case (`test` becomes `Test`,
`teST` becomes `Test`)
* trim-e - removes a trailing "e" from a string literal, used in English
for adjective manipulation (`constructive` becomes `constructiv`)
* strip-the - removes a leading "the " from a string literal, used in
English (`the house` becomes `house`)
* pluralise - a simple function for the plural of words in English,
does not take into account exceptions (`word` becomes `words`, 
`study` becomes `studies`)
* past-tensify - a simple function for the past tense of verbs in English
(`generate` becomes `generated`)

These are called with the at-symbol, and can be chained:

```
my-verb: verb@past-tensify@capitalize;
```

# In practice

## Writing a script

At first, the task of writing a script to generate random text in any
complex genre with enough flexibility to be interesting may seem daunting.
Looking at the size of some complex scripts -- such as the Postmodernism
Generator -- may not help to shake this sensation. But, as usual, there are
practical techniques which help in this task.

One approach to the task of writing a script is the bottom-up approach.
Basically, this means starting small and progressively enhancing and enlarging
the script. For example, if you're writing a script to generate journal
articles, start by writing a rule to generate sentences, and then go on to
paragraphs, sections and finally the whole article. Whilst enhancing the
script, add rules for generating titles, citations, footnotes and the like, as
well as any new sentence forms, terms and other elements that you think of.

Another approach is to take existing material in the genre, write it in and
generalise it. For example, if you are writing a script to generate travesties
of technical papers, you may want to put in a sentence fragment such as "can be
proven to be finite". If you do so, it may be an idea to think of other terms
that may be substituted for "finite" in this context; for example, "NP
-complete" or "valid" (or even "infinite"). This approach, if used carefully,
can be very effective.

Finally, keep in mind that every new alternative you add to a rule decreases
the probabilities of the other alternatives being selected. If you think that
one alternative is not quite appropriate, it may be a good idea to delete it.

# Revision history

Beta 1: February 2016. A beta version in Python, written in a long afternoon.
The code is somewhat readable and understandable, but the cache part (which
tries to guarantee that the same output is not generated twice in a row)
is an ad-hoc hack that should be replaced. It might happend when a proper
object oriented system is developed, where each rule takes care of its
own calls, having its own cache of previous calls.

js version: 2008. I wrote an horrible version in JavaScript, for a
Brazilian Portuguese translation of the Postmodernist generator. This has
been copied in dozens of websites, hardly with any improvement. 

# Acknowledgments

While it includes no code from Andrew C. Bulha, this software would not
have been possible without his Dada Engine. In his acknowledgments,
ACB was grateful to everybody who helped with the development and testing
of his package, in particular to Mitchell Porter, Jamie Cameron, Brandon Long
and Kristin Buxton.

As with myself, the inspiration for what was to become the Dada Engine came to ACB while reading "Godel, Escher, Bach: an Eternal Golden Braid" by Douglas Hofstadter; in particular, the section titled "A Little Turing Test", on page 621.

