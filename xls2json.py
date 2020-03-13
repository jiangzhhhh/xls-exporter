# -*- coding: utf-8 -*-
import re
import sys
import entry
from utils import add_quote
from formatter import Formatter


class JsonFormatter(Formatter):
    def as_key(self, key):
        return add_quote(str(key))

    def as_struct(self, value_tree, ident):
        return self.as_dict(value_tree, ident)

    def as_array(self, value_tree, ident):
        # root node
        if ident == 0:
            lst = []
            for (_, m) in value_tree.members:
                if ident > 0 and m.is_empty():
                    continue
                lst.append(self.as_any(m, ident + 1))
            return '[\n%s\n]' % (','.join(lst))
        else:
            lst = []
            for (_, m) in value_tree.members:
                if ident > 0 and m.is_empty():
                    continue
                lst.append(self.as_any(m, ident + 1))
            return '[%s]' % (','.join(lst))

    def as_dict(self, value_tree, ident):
        if ident == 0:
            lst = []
            for (k, m) in value_tree.members:
                if ident > 0 and m.is_empty():
                    continue
                lst.append('%s:%s' % (self.as_key(k), self.as_any(m, ident + 1)))
            return '{\n%s\n}' % (',\n'.join(lst))
        else:
            lst = []
            for (k, m) in value_tree.members:
                if ident > 0 and m.is_empty():
                    continue
                lst.append('%s:%s' % (self.as_key(k), self.as_any(m, ident + 1)))
            return '{%s}' % (','.join(lst))

    def as_tuple(self, value_tree, ident):
        return self.as_array(value_tree, ident)

    def as_int(self, value_tree, ident):
        return str(value_tree.value)

    def as_float(self, value_tree, ident):
        return str(value_tree.value)

    def as_bool(self, value_tree, ident):
        if value_tree.value == False:
            return 'false'
        elif value_tree.value == True:
            return 'true'

    def as_string(self, value_tree, ident):
        return add_quote(value_tree.value)

    def as_nil(self, value_tree, ident):
        return 'none'


if __name__ == '__main__':
    sys.exit(entry.main(sys.argv, 'json', JsonFormatter()))
