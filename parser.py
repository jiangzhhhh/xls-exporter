from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor
from parsimonious import expressions as exprs
from xls_exporter import TypeTree
type_grammar = Grammar(
'''
type = space (array / non_array) space
array = non_array array_suffix
non_array = base_type / tuple
array_suffix = '[' ']' array_suffix?
base_type = 'int' / 'bool' / 'float' / 'string'
tuple = '(' tuple_members ')'
tuple_members = type (',' space type)*
space = ~r'\s'*
''')

data = 'string[][]'
tree = type_grammar.parse(data)

def pre_order_traveral(node, parent):
    expr_name = node.expr_name
    if expr_name == 'space' or (node is exprs.Literal):
        return

    if expr_name == 'type':
        (_, type_decl, _) = node
        root = pre_order_traveral(type_decl, parent)
        return parent or root
    elif expr_name == 'array':
        (elem_type, array_suffix) = node
        array_node = pre_order_traveral(array_suffix, parent)
        elem_node = pre_order_traveral(elem_type, None)
        print(1, elem_node)
        array_node.set_embedded_type(elem_node)
        return array_node
    elif expr_name == 'array_suffix':
        (_, _, optional_array_suffix) = node
        tail_array_suffix = optional_array_suffix.children
        array_node = TypeTree('embedded_array')
        parent_node = None
        if tail_array_suffix:
            parent_node = pre_order_traveral(tail_array_suffix[0], None)
            parent_node.set_embedded_type(array_node)
        return parent_node or array_node
    elif expr_name == 'base_type':
        base_type = TypeTree(node.text)
        if parent:
            parent.add_member(0, base_type)
        return base_type
    elif parent:
        for child in node.children[::-1]:
            pre_order_traveral(child, parent)
        return parent
    else:
        for child in node.children[::-1]:
            return pre_order_traveral(child, None)
root = pre_order_traveral(tree,None)
print(root)
