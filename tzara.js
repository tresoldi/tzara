/**
 * The Tzara Engine is a system for the generation of text from a
 * specification, based on the principle of *recursive transition
 * networks* or *recursive grammars*. In particular, the Tzara Engine
 * is well suited for natural language generation, as the its
 * specifications (sets of rules in the form of a grammar) allow both
 * deterministic and non-deterministic results. The Tzara Engine is
 * heavily inspired and almost compatible with the Dada Engine, a
 * system developed in 1995--6 by Andrew C. Bulhak, and was developed
 * as a single-file Python module, oriented by the principle of
 * KISS (Keep It Simple, Stupid) and the possibility of future
 * translation or transpilation in other programming languages; it
 * should be considered a software toy.
 *
 * @author Tiago Tresoldi <tresoldi@gmail.com>
 * @copyright 2016, Tiago Tresoldi.
 * @file Main file for the Tzara Engine.
 */
/* require libraries */
var fs = require("fs");
var path = require("path");
var parser = require(path.join(__dirname, "grammar"));

/**
 * Returns the contents of a file.
 * @param {string} filename - The filename to be read; the current
 *     path is automatically appended.
 * @returns {string} The contents of the file.
 */
function readFile(filename) {
    "use strict";

    var source = fs.readFileSync(path.join(__dirname, filename), {
        encoding: "utf8"
    });

    return source;
}

/**
 * A weighted random function, returns an index for arrays.
 * @param {Number|Array} weights - An array with the weights of the options.
 * @return {Number} The randomly selected index.
 */
function wRandom(weights) {
    "use strict";

    /* the reduce() sums the elements of the array */
    var idx, sum = 0,
        r = Math.random() * weights.reduce(function (a, b) {
            return a + b;
        }, 0);

    /* can't replace easily with a forEach loop */
    for (idx = 0; idx < weights.length; idx += 1) {
        sum += weights[idx];
        if (r < sum) {
            return idx;
        }
    }

    /* control flow will get here if the random element is the
     * last one
     */
    return weights.length - 1;
}

function shannon(arr) {
    /* for calculation */
    var h = 0,
        p;
    var numElements = arr.length;

    /* get unique values and counts ("Set" is not supported in IE...) */
    var counts = {};
    for (var i = 0; i < arr.length; i++) {
        counts[arr[i]] = (counts[arr[i]] || 0) + 1;
    }

    /* updates the entropy for each unique element */
    for (var key in counts) {
        /* skip if the property is from prototype */
        if (!counts.hasOwnProperty(key)) {
            continue;
        }

        p = counts[key] / numElements;
        h -= p * (Math.log(p) / Math.log(2));
    }

    return h;
}

/**
 * Parses with pegjs the contents of a grammar, provided as a string,
 * and performs data manipulation for returning an object for textual
 * generation.
 * @param {string} source - A string the full source of the grammar.
 * @param {Object} A Grammar object for textual generation.
 */
function parsePBGrammar(source) {
    "use strict";

    /* the grammar object to be returned */
    var grammar = {};

    /* parses the source with pegjs */
    var parsedGrammar = parser.parse(source);

    parsedGrammar.forEach(function (v) {
        /* collect options */
        grammar[v.name] = {
            opts: v.opts,
            weights: [],
            cache: []
        };

        /* collect (caches) weights */
        v.opts.forEach(function (o) {
            grammar[v.name].weights.push(o.weight);
        });

    });

    return grammar;
}

/**
 * Applies a post-processing function to a text.
 * @param {string} text - The text to be modified.
 * @param {string} func_name - The post-processing function name.
 * @returns {string} The modified text.
 */
function apply_func(text, func_name) {
    switch (func_name) {
    case "upper":
        text = text.toUpperCase();
        break;

    case "lower":
        text = text.toLowerCase();
        break;

    case "upcase-first":
        text = text.substr(0, 1).toUpperCase() + text.substr(1, text.length);
        break;

    case "capitalize":
        text = text.substr(0, 1).toUpperCase() +
            text.substr(1, text.length).toLowerCase();
        break;

        /* English specific functions */
    case "trim-e":
        if (text.charAt(text.length - 1) === "e") {
            text = text.substr(0, text.length - 1);
        }
        break;
    case "strip-the":
        if (text.substr(0, 4) === "The" ||
            text.substr(0, 4) === "the") {
            text = text.substr(4, text.length);
        }
        break;
    case "pluralise":
        if (text.charAt(text.length - 1) === "y") {
            text = text.substr(0, text.length - 1) + "ies";
        } else if (text.charAt(text.length - 1) === "s") {
            text = text + "es";
        } else {
            text = text + "s";
        }
        break;
    case "past-tensify":
        if (text.charAt(text.length - 1) === "e") {
            text = text + "d";
        } else {
            text = text + "ed";
        }
        break;
    default:
        console.log("FUNCTION [" + func_name + "] not available!");
    }

    return text;
}

/**
 * Performs in-line replacement in a symbol call.
 * @param {string} sym - The symbol in which to perform the replacement.
 * @param {object} grammar - The grammar used for the replacement.
 * @returns {string} The modified symbol, with in-line replacements.
 */
function resolve_symbol(sym, grammar) {
    var idx_a = sym.indexOf("{"),
        idx_b = sym.indexOf("}");

    sym = sym.substr(0, idx_a) +
        evaluate(sym.substr(idx_a + 1, idx_b - 1), grammar) +
        sym.substr(idx_b + 1, sym.length);

    return sym;
}

/**
 * Adds a simple rule, consisting of a single option with a single
 * token, to a grammar. As JavaScript passes by reference, no return
 * is needed.
 * @param {string} text - The literal token to be specified as option.
 * @param {string} ruleName - The name of the rule to be created or
 *                            replaced.
 * @param {object} grammar - The grammar in which the rule will be included.
 */
function grammarAddLiteral(text, ruleName, grammar) {
    var v = {
        tokens: [{
            type: "literal",
            value: text
        }],
        weight: 1

    };
    grammar[ruleName] = {
        opts: [v],
        weights: [1],
        cache: [text]
    };

}

/**
 * Main function for the evaluation, recursively generating the text.
 * @param {string} ruleName - The name of the rule to be generated.
 * @param {object} grammar - The grammar to be used for generation.
 * @returns {string} The generated text.
 */
function generate(ruleName, grammar) {
    var optIdx; /* the index of the random option, selected below */
    var genText;

    // select the single option, or a random one
    if (grammar[ruleName].weights.length === 1) {
        optIdx = 0;
    } else {
        optIdx = wRandom(grammar[ruleName].weights);
    }

    // generate text for tokens
    var tokens = grammar[ruleName].opts[optIdx].tokens;
    var tokensText = [];
    tokens.forEach(function (t) {
        /* evaluate according to token type */
        if (t.type === "literal") {
            tokensText.push(t.value);
        } else { /* symbol */
            var buf, write_s1 = false;
            var s1 = t.value.s1,
                s2 = t.value.s2;

            /* resolve any in-line replacements, 's2' first */
            if (s2) { /* 's2' might be undefined */
                if (s2.indexOf("{") > -1) {
                    s2 = resolve_symbol(s2, grammar);
                }
            }

            if (s1.indexOf("{") > -1) {
                s1 = resolve_symbol(s1, grammar);
            }

            /* actual evaluation of symbols; for 'set' and 'override',
             * here we only evaluated the value, the actual grammar
             * update is done later (as there may be post-processing
             * operations.
             */
            if (t.value.type === "override") {
                buf = evaluate(s2, grammar);
                write_s1 = true;
            } else if (t.value.type === "set" && grammar.hasOwnProperty(
                    s1)) {
                buf = evaluate(s1, grammar);
            } else if (t.value.type == "set") {
                buf = evaluate(s2, grammar);
                write_s1 = true;
            } else { /* direct */
                buf = evaluate(s1, grammar);
            }

            /* apply requested post-processing functions, if any */
            if (t.value.hasOwnProperty("func")) {
                buf = apply_func(buf, t.value.func);
            }

            /* change grammar if needed */
            if (write_s1) {
                grammarAddLiteral(buf, s1, grammar);
            }

            /* emit symbol if requested (i.e., not silent) */
            if (t.value.output) {
                tokensText.push(buf);
            }

        }

    });

    /* condense the tokens into a single string, for storing in the
     * cache and returning if appropriate */
    genText = tokensText.join('');
    grammar[ruleName].cache.push(genText);

    return genText;
}

/**
 * Main function for rule evaluation, taking care of grammar updates and
 * cache for non repated answers (if possible).
 * @param {string} ruleName - The name of the rule to be generated.
 * @param {object} grammar - The grammar to be used for generation.
 * @returns {string} The generated text.
 */
function evaluate(ruleName, grammar) {
    var MIN_CACHE = 5;
    var genText;
    var tmpText;

    /* generate text for the given rule and push to the cache */
    genText = generate(ruleName, grammar);

    /* if there is more than one result in the cache */
    if (grammar[ruleName].cache.length > 1) {
        /* if the two last evaluations are equal */
        var items = grammar[ruleName].cache.slice(-2);
        if (items[0] === items[1]) {
            var newText;

            /* the two last evaluations are equal; let's
             * first search the entire cache, from the end to the
             * beginning, for the first different evaluation,
             * if any */
            grammar[ruleName].cache.reverse().forEach(function (e) {
                if (!newText && e !== items[1]) {
                    newText = e;
                }
            });

            /* if we still haven't got a different result, let's
             * fill the cache with up to MIN_CACHE items, hoping
             * that a different value is found */
            if (!newText) {
                while (grammar[ruleName].cache.length < MIN_CACHE) {
                    tmpText = generate(ruleName, grammar);
                    if (tmpText !== items[1]) {
                        newText = tmpText;
                        break;
                    }
                }
            }

            /* giving up and returning the repeated text, more strategies
             * could be implemented later */
            if (newText) {
                genText = newText;
            }

        }

    }

    return genText;
}

/* program starts here */

var filename = 'pomo.jpb';
var grammar = parsePBGrammar(readFile(filename));
console.log(evaluate('output', grammar));

