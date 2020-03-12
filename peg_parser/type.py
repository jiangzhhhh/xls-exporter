from parsimonious.grammar import Grammar
from parsimonious.nodes import Node
from type_tree import TypeTree
from span import Span

grammar = Grammar(
'''
type = array / tuple / base_type
array = (tuple / base_type) '[]'+
base_type = 'int' / 'bool' / 'float' / 'string'
tuple = '(' tuple_members ')'
tuple_members = type (',' space type)*
space = ~'\s*'
''')

def _build_type(grammar_tree: Node, span: Span):
    expr_name = grammar_tree.expr_name
    if expr_name == 'trim_space':
        (_, type, _) = grammar_tree.children
        return _build_type(type, span)
    elif expr_name == 'non_array':
        return _build_type(grammar_tree.children[0], span)
    elif expr_name == 'array':
        (elem_type, array_suffix) = grammar_tree
        array_dim = max(1, len(array_suffix.children))
        elem_node = _build_type(elem_type, span)
        array_node = None
        for dim in range(array_dim):
            array_node = TypeTree('embedded_array')
            array_node.set_span(span)
            array_node.set_embedded_type(elem_node)
            elem_node = array_node
        return array_node
    elif expr_name == 'tuple':
        (_, tuple_members, _) = grammar_tree.children
        tuple_node = TypeTree('tuple')
        tuple_node.set_span(span)
        (tuple_member, *maybe_many_tuple_member) = tuple_members
        members = [tuple_member]
        if maybe_many_tuple_member:
            for (_, _, tuple_more_member) in maybe_many_tuple_member[0]:
                members += [tuple_more_member]
        index = 0
        for member_type in members:
            tuple_node.add_member(index, _build_type(member_type, span))
            index += 1
        return tuple_node
    elif expr_name == 'base_type':
        node = TypeTree(grammar_tree.text)
        node.set_span(span)
        return node
    else:
        return _build_type(grammar_tree.children[0], span)

def parse_type_tree(text: str, span: Span):
    grammar_tree = grammar.parse(text)
    return _build_type(grammar_tree, span)

if __name__ == '__main__':
    span = Span('sheet', 0, 0)
    print(parse_type_tree('((string,int,float)[])[]', span))
