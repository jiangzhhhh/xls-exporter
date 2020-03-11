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

def collect_tuple_members(tuple_members):
    (tuple_member, *maybe_many_tuple_member) = tuple_members
    ret = [tuple_member]
    if maybe_many_tuple_member:
        for (_, _, tuple_more_member) in maybe_many_tuple_member[0]:
            ret += [tuple_more_member]
    return ret

def build_type(node: Node):
    expr_name = node.expr_name
    if expr_name == 'trim_space':
        (_, type, _) = node.children
        return build_type(type)
    elif expr_name == 'non_array':
        return build_type(node.children[0])
    elif expr_name == 'array':
        (elem_type, array_suffix) = node
        array_dim = max(1, len(array_suffix.children))
        elem_node = build_type(elem_type)
        array_node = None
        for dim in range(array_dim):
            array_node = TypeTree('embedded_array')
            array_node.set_embedded_type(elem_node)
            elem_node = array_node
        return array_node
    elif expr_name == 'tuple':
        (_, tuple_members, _) = node.children
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
        return TypeTree(node.text)
    else:
        return build_type(node.children[0])

if __name__ == '__main__':
    data = '((string,int,float)[])[]'
    grammar_tree = type_grammar.parse(data)
    root = build_type(grammar_tree)
    print(root)
