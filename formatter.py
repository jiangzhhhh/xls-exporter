from type_define import Types
from utils import add_quote


class Formatter(object):
    def as_any(self, value_tree: 'ValueTree', ident: int):
        type = value_tree.type_tree.type
        if type == Types.struct_t:
            return self.as_struct(value_tree, ident)
        elif type in (Types.array_t, Types.embedded_array_t):
            return self.as_array(value_tree, ident)
        elif type == Types.dict_t:
            return self.as_dict(value_tree, ident)
        elif type == Types.tuple_t:
            return self.as_tuple(value_tree, ident)
        elif value_tree.is_empty():
            return self.as_nil(value_tree, ident)
        elif type == Types.int_t:
            return self.as_int(value_tree, ident)
        elif type == Types.float_t:
            return self.as_float(value_tree, ident)
        elif type == Types.bool_t:
            return self.as_bool(value_tree, ident)
        elif type == Types.string_t:
            return self.as_string(value_tree, ident)

    def as_struct(self, value_tree: 'ValueTree', ident: int):
        s = '{'
        if ident == 0: s += '\n'
        for (k, m) in value_tree.members:
            s += '%s:%s,' % (k, self.as_any(m, ident + 1))
            if ident == 0: s += '\n'
        s += '}'
        return s

    def as_array(self, value_tree: 'ValueTree', ident: int):
        s = '['
        if ident == 0: s += '\n'
        for (k, m) in value_tree.members:
            s += '%s,' % (self.as_any(m, ident + 1))
            if ident == 0: s += '\n'
        s += ']'
        return s

    def as_dict(self, value_tree: 'ValueTree', ident: int):
        s = '{'
        if ident == 0: s += '\n'
        for (k, m) in value_tree.members:
            s += '%s:%s,' % (k, self.as_any(m, ident + 1))
            if ident == 0: s += '\n'
        s += '}'
        return s

    def as_tuple(self, value_tree: 'ValueTree', ident: int):
        s = '('
        if ident == 0: s += '\n'
        for (k, m) in value_tree.members:
            s += '%s,' % (self.as_any(m, ident + 1))
            if ident == 0: s += '\n'
        s += ')'
        return s

    def as_int(self, value_tree: 'ValueTree', ident: int):
        return str(value_tree.value)

    def as_float(self, value_tree: 'ValueTree', ident: int):
        return str(value_tree.value)

    def as_bool(self, value_tree: 'ValueTree', ident: int):
        return str(value_tree.value)

    def as_string(self, value_tree: 'ValueTree', ident: int):
        return add_quote(value_tree.value)

    def as_nil(self, value_tree: 'ValueTree', ident: int):
        return 'None'
