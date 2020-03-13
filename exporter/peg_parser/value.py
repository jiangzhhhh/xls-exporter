from parsimonious.grammar import Grammar

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
    floor_float = numerals fact?
    fact_float = numerals? fact
    fact = '.' numerals
    numerals = ~r'[0-9]+'
    sig = '-' / '+'
    space = ~'\s*'
    ''')

bool_grammar = Grammar(
    r'''
    bool = space (true / false / '1' / '0')
    true = ('T' / 't') ('R' / 'r') ('U' / 'u') ('E' / 'e')
    false = ('F' / 'f') ('A' / 'a') ('L' / 'l') ('S' / 's') ('E' / 'e')
    space = ~'\s*'
    '''
)

string_grammar = Grammar(
    r'''
    string = double_quote_string / single_quote_string
    double_quote_string = space double_quote (escaping_double_quote / double_quote_literal)*  double_quote space
    single_quote_string = space single_quote (escaping_single_quote / single_quote_literal)*  single_quote space
    double_quote_literal = ~'[^"]'
    single_quote_literal = ~'[^\']'
    escaping_double_quote = backslash double_quote
    escaping_single_quote = backslash single_quote
    double_quote = '"'
    single_quote = "'"
    backslash = '\\'
    space = ~'[\s]*'
    '''
)


def match_int(text: str):
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


def match_float(text: str):
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


def match_bool(text: str):
    result = bool_grammar.match(text)
    (_, one_of_word) = result
    content = one_of_word.text.lower()
    if content in ('true', '1'):
        return True, (result.end - result.start)
    elif content in ('false', '0'):
        return False, (result.end - result.start)


def match_string(text: str):
    try:
        result = string_grammar.match(text)
        (_, _, one_of_style, _, _) = result.children[0]
        s = ''
        for x in one_of_style.children:
            expr_name = x.children[0].expr_name
            if expr_name == 'escaping_double_quote':
                s += '"'
            elif expr_name == 'escaping_single_quote':
                s += "'"
            else:
                s += x.text
        return s, result.end - result.start
    except:
        return text, len(text)


if __name__ == '__main__':
    text = '0x123,123,sss'
    (val, pos) = match_int(text)
    print(val, pos, text[pos:], 0x123)
    # int
    print(match_int('0x123'), 0x123)
    print(match_int('0b110'), 0b110)
    print(match_int('123'), 123)
    print(match_int('-123'), -123)
    print(match_int('+123'), 123)
    # float
    print(match_float('0.1'), 0.1)
    print(match_float('-0.1'), -0.1)
    print(match_float('-.2'), -.2)
    print(match_float('123.0'), 123.0)
    print(match_float('123'), 123)
    # bool
    print(match_bool('TRUE'), True)
    print(match_bool('true'), True)
    print(match_bool('1'), True)
    print(match_bool('FALSE'), False)
    print(match_bool('false'), False)
    print(match_bool('0'), False)
    # string
    single = "'abc say:\\'hello\\';\"SB\"'"
    double = '"abc say:\\"hello\\";\'SB\'"'
    raw = '\nabc"asda\'a\'s\d'
    print(match_string(single))
    print(match_string(double))
    print(match_string(raw))
