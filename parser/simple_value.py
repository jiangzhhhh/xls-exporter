from parsimonious.grammar import Grammar

int_grammar = Grammar(
r'''
trim_space = space int space
int = sig? (hex / bin / dec)
dec = ~r'[0-9]+'
hex = '0x' ~r'[0-9a-fA-F]+'
bin = '0b' ~r'[0-1]+'
sig = '-' / '+'
space = ~'\s*'
''')

float_grammar = Grammar(
r'''
trim_space = space float space
float = sig? (floor_pat / fact_pat)
floor_pat = numberals fact?
fact_pat = numberals? fact
fact = '.' numberals
numberals = ~r'[0-9]+'
sig = '-' / '+'
space = ~'\s*'
''')

bool_grammar = Grammar(
r'''
trim_space = space bool space
bool = true / false / '1' / '0'
true = ('T' / 't') ('R' / 'r') ('U' / 'u') ('E' / 'e')
false = ('F' / 'f') ('A' / 'a') ('L' / 'l') ('S' / 's') ('E' / 'e')
space = ~'\s*'
'''
)

def parse_int(text: str):
    (_, int_syntax, _) = int_grammar.parse(text)
    (optional_sig, one_of_integer) = int_syntax.children
    integer = one_of_integer.children[0]
    expr_name = integer.expr_name
    val = None
    if expr_name == 'dec':
        val =  int(integer.text)
    elif expr_name == 'hex':
        (prefix, hex) = integer.children
        val = int(hex.text, 16)
    else:
        (prefix, bin) = integer.children
        val = int(bin.text, 2)
    if optional_sig.children and optional_sig.children[0].text == '-':
        val = -val;
    return val

def parse_float(text: str):
    (_, float_syntax, _) = float_grammar.parse(text)
    (optional_sig, one_of_pat) = float_syntax
    pat = one_of_pat.children[0]
    val = 0
    expr_name = pat.expr_name
    if expr_name == 'fact_pat':
        (optional_floor, (dot, fact)) = pat.children
        if optional_floor.children:
            val = int(optional_floor.children[0].text)
        val += float('0.' + fact.text)
    elif expr_name == 'floor_pat':
        (floor, optional_fact) = pat.children
        val = int(floor.text)
        if optional_fact.children:
            (dot, fact) = optional_fact.children[0]
            val += float('0.' + fact.text)
    if optional_sig.children and optional_sig.children[0].text == '-':
        val = -val;
    return val

def parse_bool(text: str):
    (_, bool_syntax, _) = bool_grammar.parse(text)
    text = bool_syntax.text.lower()
    if text in ('true', '1'):
        return True
    elif text in ('false', '0'):
        return False

def parse_string(text: str):
    return text

if __name__ == '__main__':
    # int
    print(parse_int('0x123'), 0x123)
    print(parse_int('0b110'), 0b110)
    print(parse_int('123'), 123)
    print(parse_int('-123'), -123)
    print(parse_int('+123'), 123)
    # float
    print(parse_float('0.1'), 0.1)
    print(parse_float('-0.1'), -0.1)
    print(parse_float('-.2'), -.2)
    print(parse_float('123.0'), 123.0)
    print(parse_float('123'), 123)
    # bool
    print(parse_bool('TRUE'), True)
    print(parse_bool('true'), True)
    print(parse_bool('1'), True)
    print(parse_bool('FALSE'), False)
    print(parse_bool('false'), False)
    print(parse_bool('0'), False)
    # string
    print(parse_string(r'ab"c\tdef\gh'), r'ab"c\tdef\gh')


