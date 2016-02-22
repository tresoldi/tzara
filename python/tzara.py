#!/usr/bin/python
# encoding: utf-8

# The Tzara Engine is a system for the generation of text from a
# specification, based on the principle of *recursive transition
# networks* or *recursive grammars*. In particular, the Tzara Engine
# is well suited for natural language generation, as the its
# specifications (sets of rules in the form of a grammar) allow both
# deterministic and non-deterministic results. The Tzara Engine is
# heavily inspired and almost compatible with the Dada Engine, a
# system developed in 1995--6 by Andrew C. Bulhak, and was developed
# as a single-file Python module, oriented by the principle of
# KISS (Keep It Simple, Stupid) and the possibility of future
# translation or transpilation in other programming languages; it
# should be considered a software toy.

"""Tzara engine module for deterministic and non-deterministic
natural language generation.
"""

import math
import pprint
import random
import sys

###############################
## Syntax/parsing definitions
SPACE_CHARS = ' \t'
NEWLINE_CHARS = '\r\n'

########################
## Grammar definitions

MIN_CACHE = 5 # minimum number of cache elements for each
              # symbol; check implementation in evaluate()

ENTROPY_THRESHOLD = 0.8 # minimum entropy for looking for an alternative
                        # evaluation for a symbol after cache analysis

# The fundamental "class" for the language generator is an abuse of
# Python's list and dictionary. As this implementation is intended to
# 1) be simple, stupid and 2) be easily traspiled/rewritten in other
# languages, I decided to adopt an extremely simple data structure, where
# each rule is a list in Python whose first element is an integer
# indicating what kind of object it actually is (such as a literal,
# a map, etc.). If you do some creative programming philology, you can
# probably tell that I have not forgotten my days with C data
# structures, and likely will understand why I decided to do this
# even in Python (dreams of virtual machines, anyone?). A Pythonic
# solution, with different objects and instances, would be far more
# elegant, but it is beyond the scope
# of this single-file project, written as a "common denominator" for
# my projects. Feel free to extend, improve, and correct this, I might
# even incorporate a python solution to the project, but I am likely
# to at least keep this "Python with C-mindset" solution around. Oh,
# the joys of open source! :)

LITERAL = 1             # "name"
SYMBOL = 2              # val
SYMBOL_SET = 3          # var<val
SYMBOL_SET_SIL = 4      # ?var<val
SYMBOL_OVERRIDE = 5     # var<<val
SYMBOL_OVERRIDE_SIL = 6 # ?var<<val

#############################
## Syntax/parsing functions

def split_rules(source):
    """
    Split a source string (e.g., the contents of a grammar as read from a
    file) into a list of single rule sources, removing comments and
    new-line characters.

    Arguments:
    `source` -- a string with the source to be split.

    Returns:
    A list with strings, each with a single rule to be parsed later.
    """

    # appends a bogus white-space to the beginning of the source: it
    # does not affect the parsing (rules are later stripped) and prevents
    # a bug when the source starts with a quote (which would be
    # irregular, anyway), as there is no previous character; to fix this
    # in the logic of the code would make it far more complex than
    # necessary.
    source = ' ' + source

    # the main loop, checks character by character, removing any
    # comments and progressively updating the list of rules. In-quote
    # hashtags (the comment symbol) and quotes are preserved.
    in_quote = False
    in_comment = False
    rule_src = ''
    rules = []
    for index in range(len(source)):
        char = source[index]

        # the action depends on the current context
        if in_quote:
            # if we are in-quote, append everything (even newline
            # characters) except non-escaped quotes, which end
            # the current context
            rule_src += char
            if char == '"' and source[index-1] != '\\':
                in_quote = False
        elif in_comment:
            # if we are in-comment, don't append anything until
            # a new-line is found, which ends the comment
            # context; note that this does not start a new
            # rule, as we must allow comments inside rules (for
            # example, to describe each option)
            if char in NEWLINE_CHARS:
                in_comment = False
        else:
            if char == '"':
                # beginning of a new literal
                in_quote = True
                rule_src += char
            elif char == '#' and not in_quote:
                # beginning of a new comment
                in_comment = True
            elif char in NEWLINE_CHARS:
                # add a white-space and skip
                rule_src += ' '
            elif char == ';':
                # end of rule
                rules.append(rule_src + ';')
                rule_src = ''
            else:
                rule_src += char

    # strip any leading or trailing spaces
    rules = [rule.strip() for rule in rules]

    # remove any empty strings -- slow but pythonic
    rules = [rule for rule in rules if rule]

    return rules

def tokenize_rule(rule_src):
    """
    Parse a rule returning a list with the rule identifier a list of the
    tokens that make up the rule, removing spaces and performing minor
    validation. This function does *not* generate a parsing tree.

    Arguments:
    `rule_src` -- a string with the rule to be parsed.

    Returns:
    A list, whose first argument is the rule identifier and the second
    argument is a list of the tokens in the rule.
    """

    # separates key and value; TODO: verify if the key name is valid,
    # check for bugs when the rule source does not include a colon
    # (which is wrong)
    key_name, value = rule_src.split(':', 1)
    key_name = key_name.strip()
    value = value.strip()

    # get tokens from 'value'
    in_quote = False
    token = ''
    tokens = []
    for index in range(len(value)):
        if in_quote:
            if value[index] == '"' and value[index-1] != '\\':
                # end quote, append token and start new one
                tokens.append(token + '"')
                token = ''
                in_quote = False
            else:
                # just append to the string and carry on;
                # escaped quotes are processed here
                token += value[index]
        else:
            if value[index] == '"':
                # start new literal token
                tokens.append(token)
                token = '"'
                in_quote = True
            elif value[index] in SPACE_CHARS:
                # add previous token and skip space
                tokens.append(token)
                token = ''
            elif value[index] == '|':
                # end of option, append tokens and carry on
                tokens.append(token)
                tokens.append('|')
                token = ''
            elif value[index] == '%':
                # weight of option, appends previous token,
                # append weight token (this) and starts a
                # new one
                tokens.append(token)
                tokens.append('%')
                token = ''
            elif value[index] == ';':
                # end of rule, append token; it should be the last
                # char in the rule, proper checking will be done when
                # writing a decent parser
                tokens.append(token)
            else:
                token += value[index]

    # remove any empty tokens
    tokens = [token for token in tokens if token]

    return [key_name, tokens]

def tokens2options(tokens):
    """Split the list of tokens into the options it specifies, even if
    there is a single option.

    Arguments:
    `tokens` -- the list of tokens to split, as provided by the tokenizer.
    Returns:
    A list of options, suitable for parsing.
    """

    options = []
    option = []
    for index in range(len(tokens)):
        if tokens[index] == '|':
            options.append(option)
            option = []
        else:
            option.append(tokens[index])
    options.append(option)

    return options

def get_option_weights(options, default_weight=1):
    """Extract the weight of each option.

    Arguments:
    `options` -- the list of options, as provided by tokens2options()
    `default_weight` -- the default weight, to be used when weight is
        not specified. Defaults to 1.
    Returns:
    A list of integers with the weight of each option.
    """
    weights = []
    for opt_idx, opt_val in enumerate(options):
        weight = default_weight
        if len(opt_val) >= 3: # min length to have weight
            if opt_val[-2] == '%':
                weight = int(opt_val[-1])
                options[opt_idx] = opt_val[:-2]
        weights.append(weight)

    return weights

def parse_rule(tokens):
    """
    Parse a list of tokens, as returned in the second element of the list
    returned by tokenize_rule(), and return a list that can be included in
    a grammar.

    Arguments:
    `tokens` -- a list of tokens to be parsed.

    Returns:
    A list whose first element are the weights for the options in the rule,
    and the second element is a list of Grammar sequences.
    """

    # get options from tokens and weights from options
    options = tokens2options(tokens)
    weights = get_option_weights(options)

    # for each element in each option sequence, prepare the object (i.e.,
    # the list) to be returned, suitable for the Grammar object
    grammar_sequence = []
    for option in options:
        grammar_option = []
        for element in option:
            if element[0] == '"':
                # element is a literal atom; remove the
                # initial and final quotes, and escape any
                # internal quote
                value = element[1:-1]
                value = value.replace('\\"', '"')
                grammar_atom = [LITERAL, value]
            elif '<<' in element:
                # element is an override, get the two components
                var1, var2 = element.split('<<')
                if var1[0] == '?':
                    grammar_atom = [SYMBOL_OVERRIDE_SIL, var1, var2]
                else:
                    grammar_atom = [SYMBOL_OVERRIDE, var1, var2]
            elif '<' in element:
                # element is a set, get the two components
                var1, var2 = element.split('<')
                if var1[0] == '?':
                    grammar_atom = [SYMBOL_SET_SIL, var1, var2]
                else:
                    grammar_atom = [SYMBOL_SET, var1, var2]
            else:
                # defaults to symbol; the third empty
                # element makes it consisent that all
                # symbols have to arguments (even it this is
                # None), so that we need fewer 'ifs' down
                # the road
                grammar_atom = [SYMBOL, element, '']

            grammar_option.append(grammar_atom)
        grammar_sequence.append(grammar_option)

    return {'weights': weights, 'sequences': grammar_sequence}

def parse_grammar(source):
    """
    Parse a grammar definition in the PB format.

    Arguments:
    `source` -- a string containing the full grammar definition.
    Returns:
    A Grammar "object" (a Python dictionary) suitable for
    text generation.
    """

    ret_grammar = {}

    rules = split_rules(source)
    for rule in rules:
        key, tokens = tokenize_rule(rule)
        ret_grammar[key] = parse_rule(tokens)

    return ret_grammar

######################
## Grammar functions
def random_wchoice(weights):
    """
    Return a random element index from a list weights.

    Arguments:
    `weights` -- A list of numbers, each indicating the weight of its
        corresponding element.
    Returns:
    The index of the randomly selected element.
    """
    rand_cut = random.uniform(0, sum(weights))
    local_sum = 0.0
    for i in range(len(weights)):
        if local_sum + weights[i] >= rand_cut:
            return i
        local_sum += weights[i]

    assert False, "Shouldn't get here"

# apply the various post-processing functions
def apply_pp(literal, pp_func):
    """
    Apply a post processing function to the provided text.

    Arguments:
    `literal` - The string to which the post-processing function will
        be applied.
    `pp_func` - The name of the post-processing function to be applied.
    Returns:
    A string with the result of the post-processing function.
   """

    if   pp_func == 'upper':
        ret = literal.upper()
    elif pp_func == 'lower':
        ret = literal.lower()
    elif pp_func == 'upcase-first':
        ret = literal[0].upper() + literal[1:]
    elif pp_func == 'capitalize':
        ret = literal.capitalize()

    # english specific functions
    elif pp_func == 'trim-e':
        if literal[-1] == 'e':
            ret = literal[:-1]
        else:
            ret = literal
    elif pp_func == 'strip-the':
        if literal.startswith('the ') or literal.startswith('The '):
            ret = literal[4:]
        else:
            ret = literal
    elif pp_func == 'pluralise':
        if literal[-1] == 'y':
            ret = literal[:-1] + 'ies'
        elif literal[-1] == 's':
            ret = literal + 'es'
        else:
            ret = literal + 's'
    elif pp_func == 'past-tensify':
        if literal[-1] == 'e':
            ret = literal + 'd'
        else:
            ret = literal + 'ed'
    else:
        raise Exception("ppfunc unknown: " + pp_func)

    return ret

def evaluate(symbol, grammar, cache=None, cache_recursion=0):
    """
    Evaluates a requested symbol for the given grammar, returning a
    literal. This function will usually recursively call itself
    multiple times; a cache of previous calls is used to reduce the
    number of equal generations when possible.

    Arguments:
    `symbol` -- the name of the symbol to be evaluated.
    `grammar` -- the grammar for the text generation.
    `cache` -- a cache of previous calls; defaults to an empty
        dictionary, to be used when calling from outside (i.e.,
        not a recursive call).
    `cache_recursion` -- the recursion level of the current call for
        cache complementation; this is used internally and is not
        intended for external calls.

    Returns:
    A tuple, whose first element is the generated text and the
        second element is the provided grammar, with any eventual rule
        modifications, and the third element is the cache of
        previous calls in the recursive call.
    """

    # initialize the cache if none is provided
    if not cache:
        cache = {}

    # select a random index
    rindex = random_wchoice(grammar[symbol]['weights'])

    # iterate over entries in the randomly selected
    # sequence; if you want this more elegant, you can
    # split into different functions and use a list
    # comprehension
    buf = []
    for entry in grammar[symbol]['sequences'][rindex]:
#        print entry

        if entry[0] == LITERAL:
            tmp = entry[1]
        else: # symbols
            # makes copies for manipulation
            entry_a = entry[1]
            entry_b = entry[2]

            # if it is a silent atom, remove the leading
            # question mark from 'entry_a'
            if entry[0] in [SYMBOL_SET_SIL, SYMBOL_OVERRIDE_SIL]:
                entry_a = entry_a[1:]

            # extract post-processing functions for the 1st
            # argument, if any; the calls are stored in a
            # list, as more than one call is allowed; for the
            # syntax, see manual
            if '@' in entry_a:
                entry_a, pp_funcs_a = entry_a.split('@', 1)
                pp_funcs_a = pp_funcs_a.split(',')
            else:
                pp_funcs_a = None

            # extract post-processing functions for the 2nd
            # argument, if any; the calls are stored in a
            # list, as more than one call is allowed; for the
            # syntax, see manual
            if '@' in entry_b:
                entry_b, pp_funcs_b = entry_b.split('@', 1)
                pp_funcs_b = pp_funcs_b.split(',')
            else:
                pp_funcs_b = None

            # perform in-name replacements, if any, for 1st arg
            while '{' in entry_a:
                idx_a = entry_a.index('{')
                idx_b = entry_a.index('}')
                expr = entry_a[idx_a+1:idx_b]
                evaluated, grammar, cache = evaluate(expr, grammar, cache)
                entry_a = '%s%s%s' % (entry_a[:idx_a],
                                      evaluated,
                                      entry_a[idx_b+1:])

            # perform in-name replacements, if any, for 2nd arg
            while '{' in entry_b:
                idx_a = entry_b.index('{')
                idx_b = entry_b.index('}')
                expr = entry_b[idx_a+1:idx_b]
                evaluated, grammar, cache = evaluate(expr, grammar, cache)
                entry_b = '%s%s%s' % (entry_b[:idx_a],
                                      evaluated,
                                      entry_b[idx_b+1:])

            # finally resolve symbol by its type, applying
            # post-processing functions as requested and
            # needed (sometimes it won't be necessary) --
            # btw, how do you say 'iterate if not None' in
            # Python?
            if entry[0] == SYMBOL:
                tmp, grammar, cache = evaluate(entry_a, grammar, cache)
                if pp_funcs_a:
                    for func in pp_funcs_a:
                        tmp = apply_pp(tmp, func)

            elif entry[0] in [SYMBOL_SET, SYMBOL_SET_SIL]:
                # evaluate the argument that is needed
                if entry_a in grammar:
                    tmp, grammar, cache = evaluate(entry_a,
                                            grammar, cache)
                else:
                    tmp, grammar, cache = evaluate(entry_b,
                                            grammar, cache)
                    if pp_funcs_b:
                        for func in pp_funcs_b:
                            tmp = apply_pp(tmp,
                                           func)

                    # append item to grammar, should
                    # be wrapped by a function
                    grammar[entry_a] = {'weights': [1],
                      'sequences': [[[1, tmp]]]}

                # apply post-processing to the first
                # argument if needed
                if pp_funcs_a:
                    for func in pp_funcs_a:
                        tmp = apply_pp(tmp, func)

                # if silent, don't emit it
                if entry[0] == SYMBOL_SET_SIL:
                    tmp = ''

            elif entry[0] in [SYMBOL_OVERRIDE, SYMBOL_OVERRIDE_SIL]:
                # evaluate the second argument
                tmp, grammar, cache = evaluate(entry_b, grammar, cache)
                if pp_funcs_b:
                    for func in pp_funcs_b:
                        tmp = apply_pp(tmp, func)

                # override any previous value
                # append item to grammar, should
                # be wrapped by a function
                grammar[entry_a] = {'weights': [1],
                  'sequences': [[[1, tmp]]]}

                # apply post-processing to the first
                # argument if needed
                if pp_funcs_a:
                    for func in pp_funcs_a:
                        tmp = apply_pp(tmp, func)

                # if silent, don't emit it
                if entry[0] == SYMBOL_OVERRIDE_SIL:
                    tmp = ''

        # append to buffer
        buf.append(tmp)

    # build the output and update the cache
    ret = ''.join(buf)
    if symbol not in cache:
        cache[symbol] = [ret]
    else:
        cache[symbol].append(ret)

    # check the cache to decide whether to return the last item (i.e.,
    # the one just evaluated) or to fetch more items. If the cache has a
    # single item, it is the first time this evaluation has been called,
    # and there is no need to perform any other action (it might be that
    # the item won't be called again, like 'output'); if we have few items,
    # fill the cache with more evaluations, as to be able to decide (in
    # this case, the evaluation eventually returned might be one
    # different from the one just evaluated).
    if len(cache[symbol]) > 1:
        if cache[symbol][-1] == cache[symbol][-2]:
            # extend the cache, if needed, before calculating the entropy
            while len(cache[symbol]) < MIN_CACHE:
                # discard the new grammars and texts
                tmp_text, tmp_grammar, new_cache = evaluate(symbol,
                    grammar, None, cache_recursion+1)

                # append new cache to the beginning of the list, so that the
                # "last in--last in list" structure is consistent
                cache[symbol] = new_cache[symbol] + cache[symbol]

            # we only try to replace the evaluated value after an analysis
            # of the cache if we are at the top-most level of recursion,
            # otherwise we would not be able to correctly feel the cache
            # to verify if the replacement itself is possible. We only
            # try to perform a replacement (by running evaluating again,
            # up to a number of times, until we find a different result
            # -- we cannot use the values in the cache because they might
            # refer to a different grammar, they only inform us that
            # a different value is possible given the starting rules) if
            # the entropy of the cache for the current symbol is above
            # an established threshold.

            if cache_recursion == 0:
                entropy = calc_entropy(cache[symbol])
                if entropy >= ENTROPY_THRESHOLD:
                    # calculate the number of times to look for an
                    # alternative; this number is the ceiling of the
                    # number of distinct items in the cache divided by
                    # entropy (consider it a rule of thumb, an approximation
                    # of the ideal number of tries, found after some
                    # brute forcing).
                    cache_set_len = len(set(cache[symbol]))
                    num_tries = int(math.ceil(cache_set_len/entropy))

                    for i in range(num_tries):
                        tmp_text, tmp_grammar, tmp_cache = evaluate(symbol,
                            grammar)

                        if tmp_text != cache[symbol][-1]:
                            ret = tmp_text
                            grammar = tmp_grammar
                            cache[symbol] = cache[symbol][:-1] + \
                                            tmp_cache[symbol]
                            break

    return ret, grammar, cache

def calc_entropy(elements):
    """Calculate the Shannon entropy of a list of elements.

    Arguments:
    `elements` -- a list with the elements.

    Returns:
    A float with the entropy of the list.
    """
    entropy = 0.0
    num_elements = float(len(elements))
    for element in set(elements):
        count = elements.count(element)
        prob = count/num_elements
        entropy -= prob * math.log(prob, 2)

    return entropy

def run(rule_file, symbol=None):
    """
    Main function when called from command line.

    Arguments:
    `rule_file` -- the path to the file cointaining the rules.
    `symbol` -- the symbol to be generated, if any.
    """
    # load rules
    with open(rule_file) as handler:
        grammar_source = handler.read()
    grammar = parse_grammar(grammar_source)

    if not symbol:
        pprint.pprint(grammar)
    else:
        #seed = raw_input('seed> ')
        #random.seed(seed)

        ret = evaluate(sys.argv[2], grammar)
        print ret[0]

if __name__ == '__main__':
    if len(sys.argv) == 2:
        run(sys.argv[1])
    elif len(sys.argv) == 3:
        run(sys.argv[1], sys.argv[2])
    else:
        print "Usage: tzara.py grammarfile"

