from parsimonious.grammar import Grammar
from parsimonious.nodes import Node

# 需要兼容浮点写法
int_grammar = Grammar(
    r'''
    int = space sig? (hex / bin / dec)
    hex = '0x' ~r'[0-9a-fA-F]+'
    bin = '0b' ~r'[0-1]+'
    dec = ~r'[0-9]+'
    sig = '-' / '+'
    space = ~'\s*'
    ''')

float_grammar = Grammar(
    r'''
    float = space sig? (floor_float / fact_float)
    floor_float = numberals fact?
    fact_float = numberals? fact
    fact = '.' numberals
    numberals = ~r'[0-9]+'
    sig = '-' / '+'
    space = ~'\s*'
    ''')

# 兼容浮点值
bool_grammar = Grammar(
    r'''
    bool = space (true / false / '1' / '0')
    true = ('T' / 't') ('R' / 'r') ('U' / 'u') ('E' / 'e')
    false = ('F' / 'f') ('A' / 'a') ('L' / 'l') ('S' / 's') ('E' / 'e')
    space = ~'\s*'
    '''
)

comma_grammar = Grammar(
    r'''
    text = escaping_comma / ~'[^,]*'
    escaping_comma = '\\,'
    '''
)


def parse_int(text: str):
    result = int_grammar.match(text)
    (_, optional_sig, one_of_integer) = result
    integer = one_of_integer.children[0]
    expr_name = integer.expr_name
    val = None
    if expr_name == 'hex':
        (prefix, hex) = integer.children
        val = int(hex.text, 16)
    elif expr_name == 'bin':
        (prefix, bin) = integer.children
        val = int(bin.text, 2)
    elif expr_name == 'dec':
        val = int(integer.text)
    if optional_sig.children and optional_sig.children[0].text == '-':
        val = -val;
    return val, (result.end - result.start)


def parse_float(text: str):
    result = float_grammar.match(text)
    (_, optional_sig, one_of_pat) = result
    pat = one_of_pat.children[0]
    val = 0
    expr_name = pat.expr_name
    if expr_name == 'fact_float':
        (optional_floor, (dot, fact)) = pat.children
        if optional_floor.children:
            val = int(optional_floor.children[0].text)
        val += float('0.' + fact.text)
    elif expr_name == 'floor_float':
        (floor, optional_fact) = pat.children
        val = int(floor.text)
        if optional_fact.children:
            (dot, fact) = optional_fact.children[0]
            val += float('0.' + fact.text)
    if optional_sig.children and optional_sig.children[0].text == '-':
        val = -val;
    return val, (result.end - result.start)


def parse_bool(text: str):
    result = bool_grammar.match(text)
    (_, one_of_word) = result
    content = one_of_word.text.lower()
    if content in ('true', '1'):
        return True, (result.end - result.start)
    elif content in ('false', '0'):
        return False, (result.end - result.start)


def parse_string(text: str):
    return text, len(text)


def find_comma_pos(text: str):
    result = comma_grammar.match(text)
    pos = result.end - result.start
    return pos


if __name__ == '__main__':
    text = '13'
    pos = find_comma_pos(text)
    print(text, pos, text[pos:])
    text = '0x123,123,sss'
    (val, pos) = parse_int(text)
    print(val, pos, text[pos:], 0x123)
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

