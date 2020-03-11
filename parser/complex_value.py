from parsimonious.grammar import Grammar

array_grammar = Grammar(
r'''
trim_space = space array space
array = text more_text*
text = escaping_comma / ~'[^,]*'
more_text = ',' text
space = ~'\s*'
escaping_comma = backslash ','
backslash = '\\'
'''
)

def parse_array_text(node):
    body = node.children[0]
    if body.expr_name == 'escaping_comma':
        return ','
    else:
        return body.text

def parse_array(text: str):
    (_, array, _) = array_grammar.parse(text)
    (text_node, maybe_many_more_text) = array
    val = [parse_array_text(text_node)]
    for child in maybe_many_more_text.children:
        (_, more_text_node) = child
        val.append(parse_array_text(more_text_node))
    return val

if __name__ == '__main__':
    print(parse_array('123,\,,2,3,,abc,()'))