from parsimonious.grammar import Grammar
from parsimonious.nodes import Node

int_grammar = Grammar(
r'''
int = sig? (hex / bin / dec)
dec = ~r'[0-9]+'
hex = '0x' ~r'[0-9a-fA-F]+'
bin = '0b' ~r'[0-1]+'
sig = '-' / '+'
space = ~'\s*'
''')

float_grammar = Grammar(
r'''
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
bool = true / false / '1' / '0'
true = ('T' / 't') ('R' / 'r') ('U' / 'u') ('E' / 'e')
false = ('F' / 'f') ('A' / 'a') ('L' / 'l') ('S' / 's') ('E' / 'e')
space = ~'\s*'
'''
)

array_grammar = Grammar(
r'''
array = text more_text*
text = escaping_comma / ~'[^,]*'
more_text = ',' text
space = ~'\s*'
escaping_comma = '\\,'
'''
)

def parse_int(text: str):
    striped = text.strip()
    (optional_sig, one_of_integer) = int_grammar.parse(striped)
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
    striped = text.strip()
    (optional_sig, one_of_pat) = float_grammar.parse(striped)
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
    striped = text.strip()
    content = bool_grammar.parse(striped).text.lower()
    if content in ('true', '1'):
        return True
    elif content in ('false', '0'):
        return False

def parse_string(text: str):
    return text

def _parse_array_text_node(node: Node):
    body = node.children[0]
    if body.expr_name == 'escaping_comma':
        return ','
    else:
        return body.text

def _parse_array_node(node: Node):
    (text_node, maybe_many_more_text) = node
    val = [_parse_array_text_node(text_node)]
    for child in maybe_many_more_text.children:
        (_, more_text_node) = child
        val.append(_parse_array_text_node(more_text_node))
    return val

def parse_array(text: str):
    striped = text.strip()
    if striped[0] == '[' and striped[-1] == ']':
        striped = striped[1:-1]
    array_node = array_grammar.parse(striped)
    return _parse_array_node(array_node)

def parse_tuple(text: str):
    striped = text.strip()
    if striped[0] == '(' and striped[-1] == ')':
        striped = striped[1:-1]
    return tuple(parse_array(striped))

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
    # array
    print(parse_array('123,\,,2,3,,abc,()'))
    print(parse_array('[1,2,  3]'))
    # tuple
    print(parse_tuple('(1,),,3)'))
    print(parse_tuple('a,b,c()'))

