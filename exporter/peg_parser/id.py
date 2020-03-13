from parsimonious.grammar import Grammar
from parsimonious.nodes import Node
from exporter.type_tree import TypeTree
from exporter.type_define import Types
from exporter.span import Span

grammar = Grammar(
    r'''
    expr = id expr_tail*
    expr_tail = (struct_visit / array_visit)
    struct_visit = space '.' space id
    array_visit = space '[' space numeral space ']'
    id = ~'[^\[\.]+'
    numeral = ~'[0-9]+'
    space = ~'\s*'
    '''
)


def _get_key(node: Node):
    expr_name = node.expr_name
    if expr_name == 'struct_visit':
        (_, _, _, id) = node.children
        return id.text
    elif expr_name == 'array_visit':
        (_, _, _, numeral, _, _) = node.children
        return int(numeral.text)


def _get_or_create_parent(node: Node, parent_key: str, grandpa: TypeTree, span: Span):
    key = _get_key(node)
    parent = grandpa.get_member(parent_key)
    if parent is None:
        parent_type = Types.array_t if isinstance(key, int) else Types.struct_t
        parent = TypeTree(parent_type)
        parent.set_span(span)
        grandpa.add_member(parent_key, parent)
    return parent, key


# 返回父节点和key
def get_or_create_parent(id_text: str, root: TypeTree, span: Span):
    id_grammar_tree = grammar.parse(id_text)
    (id, maybe_many_expr_tail) = id_grammar_tree
    if maybe_many_expr_tail.children:
        parent_key = id.text
        grandpa = root
        for child in maybe_many_expr_tail.children[:-1]:
            node = child.children[0]
            (parent, parent_key) = _get_or_create_parent(node, parent_key, grandpa, span)
            grandpa = parent
        last_node = maybe_many_expr_tail.children[-1].children[0]
        (parent, parent_key) = _get_or_create_parent(last_node, parent_key, grandpa, span)
        return parent, parent_key
    else:
        return root, id.text


if __name__ == '__main__':
    root = TypeTree(Types.struct_t)
    span = Span("sheet", 0, 0)
    get_or_create_parent('skills[1].id.percent', root, span)
    print(root)
