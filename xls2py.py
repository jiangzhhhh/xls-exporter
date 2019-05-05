import os
import re
import xls_exporter
from xls_exporter import add_quote
import codecs

class PyFormatter(xls_exporter.Formatter):
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
            return 'False'
        elif value_tree.value == True:
            return 'True'
    def as_string(self, value_tree, ident):
        return add_quote(value_tree.value)
    def as_nil(self, value_tree, ident):
        return 'None'

def main(argv):
    argc = len(argv)
    if argc < 2:
        error('usage: xls2py.py <input_file> [<output_file>]')
        return 2
    else:
        input_file = argv[1]
        if argc > 2:
            output_file = argv[2]
        else:
            pre, ext = os.path.splitext(input_file)
            output_file = pre + '.py'
        value_tree = xls_exporter.parse(input_file, verbose=True)
        out = value_tree.print(formatter=PyFormatter())
        # 输出文件
        with codecs.open(output_file, "w+", "utf-8") as f:
            f.write(out)
    return 0

if __name__ == '__main__':
    main(['', './example/example.xlsx'])
    main(['', './example/list.xlsx'])
    main(['', './example/empty.xlsx'])
