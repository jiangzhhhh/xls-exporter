# -*- coding: utf-8 -*-
import re
import sys
import entry
import xls_exporter
from xls_exporter import add_quote
vector_pat = re.compile(r'(\([^\)]*\))')

class JsonFormatter(xls_exporter.Formatter):
    def as_key(self, key):
        return add_quote(str(key))
    def as_struct(self, value_tree, ident):
        return self.as_dict(value_tree, ident)
    def as_array(self, value_tree, ident):
        # root node
        if ident == 0:
            lst = []
            for (_,m) in value_tree.members:
                if ident > 0 and m.is_empty():
                    continue
                lst.append(self.as_any(m, ident+1))
            return '{\n%s\n}' % (','.join(lst))
        else:
            lst = []
            for (_,m) in value_tree.members:
                if ident > 0 and m.is_empty():
                    continue
                lst.append(self.as_any(m, ident+1))
            return '{%s}' % (','.join(lst))
    def as_dict(self, value_tree, ident):
        if ident == 0:
            lst = []
            for (k,m) in value_tree.members:
                if ident > 0 and m.is_empty():
                    continue
                lst.append('%s:%s' % (self.as_key(k), self.as_any(m, ident+1)))
            return '{\n%s\n}' % (',\n'.join(lst))
        else:
            lst = []
            for (k,m) in value_tree.members:
                if ident > 0 and m.is_empty():
                    continue
                lst.append('%s:%s' % (self.as_key(k), self.as_any(m, ident+1)))
            return '{%s}' % (','.join(lst))
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
    def as_vector(self, value_tree, ident):
        match = vector_pat.match(value_tree.value)
        vecValues = match.group(1).replace("(", "[").replace(")", "]")
        return '{%s}' % (','.join(vecValues))
    def as_vector_array(self, value_tree, ident):
        lst = []
        idx = 0
        for match in vector_pat.findall(value_tree.value):
            vecValues = match.replace("(", "[").replace(")", "]")
            idx = idx + 1
            lst.append('[%d]={%s}' % (idx,(','.join(vecValues))) )
        return '{%s}' % (','.join(lst))
    def as_nil(self, value_tree, ident):
        return 'none'

if __name__ == '__main__':
    sys.exit(entry.main(sys.argv, 'json', JsonFormatter()))
