// Tzara Engine Grammar

/* First rule in the grammar, to collect the rules */
rules = 
    r:rule+ _s { return r; }

/* comments, c-style, only single lines */
/* the final _s here allows for blank lines between comments */
_c =
    '//' [^\n]* '\n' _s

/* spaces, ignored */
_s =
    _c _s /
    [\r\n\t ]*

/* identifier, any alphanumeric character plus minus, underscore and dot;
 * '{' and '}' are included for in-line replacements, but should *not*
 * be used when naming */
identifier =
    id:[-_.a-zA-Z0-9{}]+ { return id.join(''); }

/* attribution operand, with optional spaces */
attrib_op =
    _s ":" _s

or_op =
    _s "|" _s

sil_op =
    "?"

/* decimal and hexadecimal integer, which are case *insensitive*;
 * decimal are used mostly for option weight, hexadecimal for unicode
 * escaping in strings */
HEXDIG =
    [0-9a-f]i
integer "integer" =
    digits:[0-9]+ { return parseInt(digits.join(""), 10); }

/* string definition from JSON example of peg.js */
literal
  = quotation_mark chars:char* quotation_mark { return chars.join(""); }

char
  = unescaped
  / escape
    sequence:(
        '"'
      / "\\"
      / "/"
      / "b" { return "\b"; }
      / "f" { return "\f"; }
      / "n" { return "\n"; }
      / "r" { return "\r"; }
      / "t" { return "\t"; }
      / "u" digits:$(HEXDIG HEXDIG HEXDIG HEXDIG) {
          return String.fromCharCode(parseInt(digits, 16));
        }
    )
    { return sequence; }

escape         = "\\"
quotation_mark = '"'
unescaped      = [\x20-\x21\x23-\x5B\x5D-\u10FFFF]

// end of string from JSON example grammar

/* a single rule */
rule =
    _s id:identifier attrib_op o:options _s ";" _s
    { return {name: id, opts: o}; }

/* options for a single rule */
options =
    t:tokens or_op o:options {
        /* there should be a better way of collecting the options... */
        if (o.length === undefined) {
            /* only two tokens */
            o = [t, o];
        } else {
            /* `o` is already an array (as above) */
            o.push(t);
        }

        return o;
    } /
    t:tokens { return [t]; }

weight =
    _s "%" _s w:integer _s { return w; }

/* sequence of tokens for an option of a rule */
tokens =
    t:token+ w:weight* {
        /* if `w` is empty, no weight was specified, used default */
        if (w.length === 0) {
            w = [1];
        }

        return {tokens:t, weight:w[0]};
    }

/* single token */
token =
    _s l:literal _s { return {type: "literal", value: l}; } /
    _s s:symbol _s  { return {type: "symbol",  value: s}; }

symbol =
    e:expr "@" fc:identifier {
        e.func = fc; 
        return e;
    } /
    expr

expr =
    sil_op s1:identifier "<<" s2:identifier
    { return { type: "override", output: false,
               s1: s1, s2: s2 };
    } /
    sil_op s1:identifier "<" s2:identifier
    { return { type: "set", output: false,
               s1: s1, s2: s2 };
    } / 
    s1:identifier "<<" s2:identifier
    { return { type: "override", output: true,
               s1: s1, s2: s2 };
    } /
    s1:identifier "<" s2:identifier
    { return { type: "set", output: true,
               s1: s1, s2: s2};
    } / 
    s1:identifier
    { return { type: "direct", output: true,
      s1: s1}; }

