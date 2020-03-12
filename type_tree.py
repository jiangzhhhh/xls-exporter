import re
from type_define import Types, value_types
from utils import to_xls_col
from span import Span

default_option_pat = re.compile(r'.*def\s*:\s*(.+)$')


class TypeTree(object):
    type: str = None
    elem_type: 'TypeTree' = None
    span: Span = None
    unique: bool = False
    required: bool = False

    def __init__(self, type: str):
        assert type, type
        self.type = type
        self.members = []
        self.default = None

    def set_span(self, span: Span):
        self.span = span
        if self.elem_type:
            self.elem_type.span = self.span

    def add_member(self, key: [str, int], member: 'TypeTree'):
        self.members.append((key, member))

    def get_member(self, member_name: [str, int]):
        for (key, m) in self.members:
            if key == member_name:
                return m

    def set_option(self, option: str):
        self.unique = 'unique' in option
        self.required = 'required' in option
        m = default_option_pat.match(option)
        if m:
            self.default = m.group(1)

    def set_embedded_type(self, elem_type: 'TypeTree'):
        self.elem_type = elem_type

    # 是否唯一项,不允许出现重复值
    def is_unique(self):
        return self.unique

    # 是否必填项
    def is_required(self):
        return self.required

    def __str__(self):
        def to_str_recursion(tree: 'TypeTree'):
            s = ''
            if tree.type == Types.embedded_array_t:
                s += '%s[]' % (str(tree.elem_type))
            elif tree.type == Types.tuple_t:
                s += '(%s)' % (','.join([to_str_recursion(m) for (_, m) in tree.members]))
            elif tree.type in value_types:
                s += tree.type
            # if tree.span:
            #     s += '(%s:%s)' % (tree.span.sheet, tree.span.xls_col)
            # if tree.is_unique():
            #     s += 'u'
            # if tree.is_required():
            #     s += '!'

            if tree.type == Types.struct_t or tree.type == Types.dict_t:
                s += '{%s}' % (','.join([str(k) + ':' + to_str_recursion(m) for (k, m) in tree.members]))
            elif tree.type == Types.array_t:
                s += '[%s]' % (','.join([to_str_recursion(m) for (_, m) in tree.members]))

            return s

        return to_str_recursion(self)
