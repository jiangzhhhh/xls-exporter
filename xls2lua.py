import os
import re
import xls_exporter
from xls_exporter import add_quote
import codecs

id_pat = re.compile(r'^[_a-zA-Z][_\w]*$')
# lua的保留关键字
reserved_keywords = [
  'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 
  'function', 'if', 'in', 'local', 'nil', 'not', 'or', 'repeat', 
  'return', 'then', 'true', 'until', 'while' ]

# 判断字符串是否合法变量名
def is_legal_id(s):
    if id_pat.match(s) and s not in reserved_keywords:
        return True
    return False

class LuaFormatter(xls_exporter.Formatter):
    def as_key(self, key):
        if isinstance(key, int):
            return '[%d]' % key
        elif is_legal_id(key):
            return key
        else:
            return '[%s]' % add_quote(key)

    def as_table(self, value_tree, ident):
        # root node
        if ident == 0:
            lst = []
            for (k,m) in value_tree.members:
                lst.append('%s=%s,\n' % (self.as_key(k), self.as_any(m, ident+1)))
            return 'return {\n%s}' % (''.join(lst))
        else:
            lst = []
            for (k,m) in value_tree.members:
                if ident > 0 and m.is_empty():
                    continue
                lst.append('%s=%s' % (self.as_key(k), self.as_any(m, ident+1)))
            return '{%s}' % (','.join(lst))
    def as_struct(self, value_tree, ident):
        return self.as_table(value_tree, ident)
    def as_array(self, value_tree, ident):
        # root node
        if ident == 0:
            lst = []
            for (_,m) in value_tree.members:
                lst.append(self.as_any(m, ident+1) + ',\n')
            return 'return {\n%s}' % (''.join(lst))
        else:
            lst = []
            for (_,m) in value_tree.members:
                if ident > 0 and m.is_empty():
                    continue
                lst.append(self.as_any(m, ident+1))
            return '{%s}' % (','.join(lst))
    def as_dict(self, value_tree, ident):
        return self.as_table(value_tree, ident)
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
        return 'nil'

def main(argv):
    argc = len(argv)
    if argc < 2:
        error('usage: xls2lua.py <input_file> [<output_file>]')
        return 2
    else:
        input_file = argv[1]
        if argc > 2:
            output_file = argv[2]
        else:
            pre, ext = os.path.splitext(input_file)
            output_file = pre + '.lua'
        value_tree = xls_exporter.parse(input_file, verbose=True)
        out = value_tree.print(formatter=LuaFormatter())
        # 输出文件
        with codecs.open(output_file, "w+", "utf-8") as f:
            f.write(out)
    return 0

if __name__ == '__main__':
    main(['', './example/example.xlsx'])
    main(['', './example/list.xlsx'])
    main(['', './example/empty.xlsx'])
