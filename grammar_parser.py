from parsimonious.grammar import Grammar
from parsimonious.nodes import Node
from xls_exporter import TypeTree

type_grammar = Grammar(
'''
trim_space = space type space
type = array / tuple / base_type
array = (tuple / base_type) '[]'+
base_type = 'int' / 'bool' / 'float' / 'string'
tuple = '(' tuple_members ')'
tuple_members = type (',' space type)*
space = ~'\s*'
''')

int_grammar = Grammar(
r'''
int = hex / bin / dec
dec = ~r'[0-9]+'
hex = '0x' ~r'[0-9a-fA-F]+'
bin = '0b' ~r'[0-1]+'
''')

float_grammar = Grammar(
r'''
float = numberal? float_tail
float_tail = '.' fact
fact = numberal 
numberal = ~r'[0-9]+'
''')

bool_grammar = Grammar(
r'''
bool = true_false / one_zero
true_false = 'TRUE' / 'FALSE' / 'true' / 'false'
one_zero = ~r'[0-1]'
'''
)

string_grammar = Grammar(
r'''
string = character+
character = escaping / non_backslash
non_backslash = ~r'[^\\]'
escaping = backslash ~'.'
backslash = '\\'
'''
)

def build_type(grammar_tree: Node):
    expr_name = grammar_tree.expr_name
    if expr_name == 'trim_space':
        (_, type, _) = grammar_tree.children
        return build_type(type)
    elif expr_name == 'non_array':
        return build_type(grammar_tree.children[0])
    elif expr_name == 'array':
        (elem_type, array_suffix) = grammar_tree
        array_dim = max(1, len(array_suffix.children))
        elem_node = build_type(elem_type)
        array_node = None
        for dim in range(array_dim):
            array_node = TypeTree('embedded_array')
            array_node.set_embedded_type(elem_node)
            elem_node = array_node
        return array_node
    elif expr_name == 'tuple':
        (_, tuple_members, _) = grammar_tree.children
        tuple_node = TypeTree('tuple')
        (tuple_member, *maybe_many_tuple_member) = tuple_members
        members = [tuple_member]
        if maybe_many_tuple_member:
            for (_, _, tuple_more_member) in maybe_many_tuple_member[0]:
                members += [tuple_more_member]
        index = 0
        for member_type in members:
            tuple_node.add_member(index, build_type(member_type))
            index += 1
        return tuple_node
    elif expr_name == 'base_type':
        return TypeTree(grammar_tree.text)
    else:
        return build_type(grammar_tree.children[0])

if __name__ == '__main__':
    grammar_tree = type_grammar.parse('((string,int,float)[])[]')
    root = build_type(grammar_tree)
    print(int_grammar.parse('0x123'))
    print(float_grammar.parse('.1'))
    print(bool_grammar.parse('true'))
    print(string_grammar.parse(r'abc\d1234\5\\'))
    print(string_grammar.parse('\t'))

