from parsimonious.grammar import Grammar
from parsimonious.nodes import Node
from xls_exporter import TypeTree
from xls_exporter import Types

grammar = Grammar(
r'''
expr = id expr_tail*
expr_tail = (struct_visit / array_visit)
struct_visit = space '.' space id
array_visit = space '[' space numberal space ']'
id = ~'[^\[\.]+'
numberal = ~'[0-9]+'
space = ~'\s*'
'''
)

def _get_or_create_member(key: (int,str), parent: TypeTree):
    node = parent.get_member(key)
    if node is None:
        node_type = Types.array_t if key is int else Types.struct_t
        node = TypeTree(node_type)
        parent.add_member(key, node)
    return node

def build_id_node(grammar_tree: Node, parent: TypeTree):
    (id, maybe_many_expr_tail) = grammar_tree
    parent = _get_or_create_member(id.text, parent)
    for child in maybe_many_expr_tail.children:
        pat = child.children[0]
        expr_name = pat.expr_name
        key = None
        if expr_name == 'struct_visit':
            (_, _, _, id) = pat.children
            key = id.text
        elif expr_name == 'array_visit':
            (_, _, _, numberal, _, _) = pat.children
            key = int(numberal.text)
        parent = _get_or_create_member(key, parent)
    return parent

if __name__ == '__main__':
    root = TypeTree(Types.struct_t)
    node = grammar.parse('1skills[1][2].hp.percent')
    build_id_node(node, root)
    print(root)
