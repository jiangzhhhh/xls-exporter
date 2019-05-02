# -*- coding: utf-8 -*-
import sys
import xlrd
import codecs
import re
import os

# fuck py2
strings = (str)
try:
    reload(sys)
    sys.setdefaultencoding("utf-8")
    strings = (basestring,str)
except:
    pass

# 异常定义
# 结构异常
class ParseError(RuntimeError):
    def __init__(self, msg):
        super().__init__(msg)

# 数据异常
class EvalError(RuntimeError):
    def __init__(self, msg):
        super().__init__(msg)

# 文件格式异常
class FileFormatError(RuntimeError):
    def __init__(self, msg):
        super().__init__(msg)

# 定义符号
class Types(object):
    int_t = 'int'
    bool_t = 'bool'
    string_t = 'string'
    float_t = 'float'
    struct_t = 'struct'
    array_t = 'array'
    embedded_array_t = 'embedded_array'

# 直接求值类型
value_types = (Types.int_t,Types.float_t,Types.bool_t,Types.string_t)
empty_values = ('', None)

class Literals(object):
    array_fmt = '{%s}'
    struct_fmt = '{%s}'
    separator = ','
    newline = '\n'
    bool_true = 'true'
    bool_false = 'false'
    nil = 'nil'
    index_fmt = '[%s]'
    key_pair_fmt = '%s=%s'

# lua的保留关键字
reserved_keywords = [
  'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 
  'function', 'if', 'in', 'local', 'nil', 'not', 'or', 'repeat', 
  'return', 'then', 'true', 'until', 'while' ]

# 正则
id_pat = re.compile(r'^[_a-zA-Z][_\w]*$')
array_pat = re.compile(r'^(\w+)\[(\d+)\]$')
embedded_array_pat = re.compile(r'^(\w+)\[\]$')
default_option_pat = re.compile(r'default\s*=\s*(.+)$')
setting_pat = re.compile(r'//\$(.+)$')

class TypeTree(object):
    def __init__(self, type):
        self.type = type
        self.members = []
        self.cursor = None
        self.unique = False
        self.required = False
        self.default = None
        # depth>1的容器节点(不包括嵌套数组),如果所有子节点为nil,自己也会输出nil
        self.depth = 0

    def set_cursor(self, sheet_name, col):
        self.cursor = (sheet_name, col)

    def add_member(self, key, member):
        member.depth = self.depth+1
        self.members.append((key,member))

    def get_member(self, member_name):
        for (key,m) in self.members:
            if key == member_name:
                return m

    def set_option(self, option):
        self.unique = 'unique' in option
        self.required = 'required' in option
        m = default_option_pat.match(option)
        if m:
            self.default = m.group(1)

    # 是否唯一项,不允许出现重复值
    def is_unique(self):
        return self.unique

    # 是否必填项
    def is_required(self):
        return self.required

    def __str__(self):
        def to_str_recursion(tree, ident):
            s = ''
            s += tree.type
            if tree.cursor:
                s += '(%s:%s)' % (tree.cursor[0], to_xls_col(tree.cursor[1]))
            if tree.is_unique():
                s += 'u'
            if tree.is_required():
                s += '!'
            s += '\n'
            for (k,m) in tree.members:
                s += ' ' * (2*(ident+1))
                s += '%s:%s' % (k, to_str_recursion(m, ident+1))
            return s
        return to_str_recursion(self, 0)

    def eval(self, row, row_data):
        text = Literals.nil
        if self.type == Types.array_t:
            lst = []
            for (index,member) in self.members:
                value = member.eval(row, row_data)
                if value == Literals.nil:
                    continue
                lst.append('%s' % value)
            if (self.depth > 1) and not lst:
                text = Literals.nil
            else:
                text = Literals.array_fmt % Literals.separator.join(lst)
        elif self.type == Types.struct_t:
            lst = []
            for (key,member) in self.members:
                value = member.eval(row, row_data)
                if value == Literals.nil:
                    continue
                if is_legal_id(key):
                    lst.append(Literals.key_pair_fmt % (key, value))
                else:
                    fmt = Literals.key_pair_fmt % (Literals.index_fmt, '%s')
                    lst.append(fmt % (add_quote(key), value))
            if (self.depth > 1) and not lst:
                text = Literals.nil
            else:
                text = Literals.struct_fmt % Literals.separator.join(lst)
        else:
            (sheet_name, col) = self.cursor
            value = row_data[col].value
            # 如果有填写了空值，且存在默认值，则替换之
            if self.default is not None and (value in empty_values):
                value = self.default
            try:
                if self.type in value_types:
                    text = eval_value(self.type, value)
                else:
                    # 内嵌数组
                    m = embedded_array_pat.match(self.type)
                    if m:
                        embedded_type = m.group(1)
                        arr = value.split(Literals.separator)
                        lst = []
                        size_arr = len(arr)
                        # 从后往前遍历，找到最后一个有效下标，用于过滤尾部空项
                        last_valid_index = size_arr-1
                        for v in arr[::-1]:
                            if v != '' and v is not None:
                                break
                            last_valid_index -= 1
                        # 遍历至最后一个有效下标为止
                        for v in arr[:last_valid_index+1]:
                            lst.append(eval_value(embedded_type, v))
                        text = Literals.array_fmt % Literals.separator.join(lst)
                    else:
                        raise ValueError
            except ValueError:
                eval_error('表:%s,列:%s,行:%s,填写了跟定义类型(%s)不一致的值:%s' % (sheet_name, to_xls_col(col), to_xls_row(row), self.type, value))
        return text

def eval_value(type, value):
    if value in empty_values:
        return Literals.nil
    elif type == Types.int_t:
        return str(int(value))
    elif type == Types.float_t:
        return str(float(value))
    elif type == Types.bool_t:
        lower_str = str(int(value)).lower()
        if lower_str in ('0', 'false'):
            return Literals.bool_false
        elif lower_str in ('1', 'true'):
            return Literals.bool_true
        else:
            raise ValueError
    elif type == Types.string_t:
        return add_quote(value)
    else:
        raise ValueError

# 将整数转换为excel的列
def to_xls_col(num):
    a = ord('A')
    result = ''
    tmp = num
    while True:
        factor = tmp // 26
        remain = tmp % 26
        tmp = factor
        result = chr(remain + a) + result
        if factor == 0:
            break
    return result

def to_xls_row(num):
    return str(num+1)

# 判断字符串是否合法变量名
def is_legal_id(s):
    if id_pat.match(s) and s not in reserved_keywords:
        return True
    return False

# 输出解析错误信息并退出程序
def parse_error(msg):
    raise ParseError('[解析错误]%s' % msg)

# 输出求值错误信息并退出程序
def eval_error(msg):
    raise EvalError('[求值错误]%s' % msg)

# 为字符串内容添加双引号
def add_quote(text):
    translation = {
        '"':'\\"',
        '\\':'\\\\"',
        '\n':'\\n',
        '\\r':'\\r',
    }
    out = ''
    for c in text:
        v = translation.get(c, c)
        out += v
    return '"' + out + '"'

# 读取xls文件内容，并过滤注释行
# 返回{sheet_name:[(row, row_cells),...]}
def read_sheets_from_xls(file_path):
    workbook = xlrd.open_workbook(file_path)
    sheets = []
    reading_setting = True
    for sheet in workbook.sheets():
        if sheet.ncols <= 0:
            continue
        row_cells = []
        settings = []
        for row in range(0, sheet.nrows):
            # 过滤全空白行
            if not any(sheet.row_values(row)):
                continue
            text = sheet.cell_value(row, 0)
            # 过滤注释行
            if isinstance(text, strings) and text.startswith('//'):
                if reading_setting:
                    m = setting_pat.match(text)
                    if m:
                        settings.append(m.group(1))
                continue
            row_cells.append((row, sheet.row(row)))
            reading_setting = False
        if len(row_cells) > 0:
            sheets.append((sheet.name, row_cells, settings))
    return sheets

# 输入sheet构建类型树
def build_type_tree(sheet_name, sheet_cells):
    type_tree = TypeTree(Types.struct_t) # todo:根节点不一定是struct???
    for col in range(len(sheet_cells[0][1])):
        # 前三行约定为定义行
        option = sheet_cells[0][1][col].value
        decl_type = sheet_cells[1][1][col].value
        path = sheet_cells[2][1][col].value
        elem_type = decl_type

        m = embedded_array_pat.match(decl_type)
        if m:
            elem_type = m.group(1)
        # 检查数据类型
        if elem_type not in value_types:
            # 声明了未知数据类型
            parse_error('表:%s,列:%s,声明了未知数据类型%s' % (sheet_name, to_xls_col(col), decl_type))

        # 如果定义了路径，则需要向上查找到父节点
        splited = path.split('.')
        parent = type_tree
        for term in splited[:-1]:
            m = array_pat.match(term)
            index = None
            if m:
                term = m.group(1)
                index = int(m.group(2))
            lookup = parent.get_member(term)
            if lookup is None:
                lookup = TypeTree(Types.struct_t if index is None else Types.array_t)
                parent.add_member(term, lookup)
            parent = lookup
            if index is not None:
                elem = parent.get_member(index)
                if elem is None:
                    elem  = TypeTree(Types.struct_t)
                    parent.add_member(index, elem)
                parent = elem
        field_name = splited[-1]
        field_member = TypeTree(decl_type)
        field_member.set_cursor(sheet_name, col)
        field_member.set_option(option)
        # 检查重复定义域
        if parent.get_member(field_name) is not None:
            parse_error('表:%s,列:%s,重复定义了成员%s' % (sheet_name, to_xls_col(col), path))
        parent.add_member(field_name, field_member)
    # todo:还需要检查数组元素是否同构???
    return type_tree

# 检查类型树之间是否存在结构冲突
def check_type_conflicet(lhs_key, lhs, rhs_key, rhs):
    # 宽度优先遍历
    def bfs_walk(lhs_key, lhs, rhs_key, rhs):
        # 检查不同类型树之间的同项类型是否一致
        if lhs.type != rhs.type:
            parse_error('类型冲突,项:%s类型(%s)跟项:%s类型(%s)不同' % (lhs_key, lhs.type, rhs_key, rhs.type))

        # 检查约束冲突
        if lhs.is_unique() and not rhs.is_unique():
            parse_error('约束冲突,项:%s(unique)跟项:%s约束类型不同' % (lhs_key, rhs_key))

        if lhs.is_required() and not rhs.is_required():
            parse_error('约束冲突,项:%s(required)跟项:%s约束类型不同' % (lhs_key, rhs_key))

        for (k,m1) in lhs.members:
            m2 = rhs.get_member(k)
            if m2:
                bfs_walk('%s.%s' % (lhs_key, k), m1, '%s.%s' % (rhs_key, k), m2)
            elif m1.is_unique():
                # 如果某一列定义为unique，则其余sheet表也必须定义该列
                parse_error('约束冲突,%s缺少unique项:%s' % (rhs_key, k))
            elif m1.is_required():
                # 如果某一列定义为required，则其余sheet表也必须定义该列
                parse_error('约束冲突,%s缺少required项:%s' % (rhs_key, k))
    bfs_walk(lhs_key, lhs, rhs_key, rhs)

# 根据约束列定义，对源数据进行检查
def check_constraint_cols(type_trees, sheets):
    if not type_trees:
        return

    # 唯一列
    unique_cols = []
    # 必填列
    requried_cols = []

    # 收集所有unique引用路径
    def collect_check_cols(path, tree):
        if tree.is_unique():
           unique_cols.append(path)
        if tree.is_required():
            requried_cols.append(path)
        for (k,m) in tree.members:
            clone = path[:]
            clone.append(k)
            collect_check_cols(clone, m) 

    (_, type_tree) = type_trees[0]
    for (k,m) in type_tree.members:
        collect_check_cols([k], m)

    def get_member_by_path(type_tree, path):
        cur = type_tree
        for key in path:
            cur = cur.get_member(key)
        return cur

    i = 0
    for (sheet_name, row_cells, _) in sheets:
        (_, type_tree) = type_trees[i]
        i += 1

        # 检查所有唯一列数据有没有重复
        for path in unique_cols:
            # 根据path搜索到type_tree节点
            unique_col = get_member_by_path(type_tree, path)
            (_, col) = unique_col.cursor
            unique_set = set()
            for (row, row_data) in row_cells[3:]:
                value = row_data[col].value
                if value in empty_values:
                    continue
                if value in unique_set:
                    eval_error('unique列(%s)于表:%s,列:%s,行:%s出现了重复值(%s)' \
                        % ('.'.join([str(x) for x in path]), sheet_name, to_xls_col(col), to_xls_row(row), value))
                unique_set.add(value)

        # 检查所有必填列是否为空
        for path in requried_cols:
            # 根据path搜索到type_tree节点
            requried_col = get_member_by_path(type_tree, path)
            (_, col) = requried_col.cursor
            for (row, row_data) in row_cells[3:]:
                value = row_data[col].value
                if value in empty_values:
                    eval_error('requried列(%s)于表:%s,列:%s,行:%s出现了空数据' \
                        % ('.'.join([str(x) for x in path]), sheet_name, to_xls_col(col), to_xls_row(row)))

def xls2lua(file_path, out_file_path, verbose=True):
    sheets = read_sheets_from_xls(file_path)    # 过滤注释行

    # 生成表结构
    type_trees = []
    for (sheet_name, row_cells, settings) in sheets:
        type_tree = build_type_tree(sheet_name, row_cells)
        type_trees.append((sheet_name, type_tree))
        if verbose:
            print(settings)
            print(sheet_name, type_tree)

    # 检查不同sheet的typetree有没有结构冲突
    for (lhs_name, lhs) in type_trees:
        for (rhs_name, rhs) in type_trees:
            if lhs == rhs:
                continue
            check_type_conflicet(lhs_name, lhs, rhs_name, rhs)

    # 检查有约束的值
    check_constraint_cols(type_trees, sheets)

    # 求值
    lst = []
    i = 0
    for (sheet_name, row_cells, settings) in sheets:
        (_, type_tree) = type_trees[i]
        i += 1

        # 处理空类型树异常
        if not type_tree.members:
            continue

        # 输出格式有三种:
        # 只有两列，名字分别叫做key,value的输出成定义格式
        # 第一列是unique的输出成字典
        # 否则输出成列表  
        if len(type_tree.members) == 2 and (type_tree.members[0][0],type_tree.members[1][0]) == ('key', 'value'):
            (key_node, value_node) = (type_tree.members[0][1],type_tree.members[1][1])
            # 前三行为结构定义行，从第四行开始遍历
            for (row, row_data) in row_cells[3:]:
                key = key_node.eval(row, row_data)
                value = value_node.eval(row, row_data)
                if is_legal_id(key):
                    lst.append(Literals.key_pair_fmt % (key, value))
                else:
                    fmt = Literals.key_pair_fmt % (Literals.index_fmt, '%s')
                    lst.append(fmt % (key, value))
        elif type_tree.members[0][1].is_unique():
            (_, key_node) = type_tree.members[0]
            fmt = Literals.key_pair_fmt % (Literals.index_fmt, '%s')
            # 前三行为结构定义行，从第四行开始遍历
            for (row, row_data) in row_cells[3:]:
                lst.append(fmt % (key_node.eval(row, row_data), type_tree.eval(row, row_data)))
        else:
            # 前三行为结构定义行，从第四行开始遍历
            for (row, row_data) in row_cells[3:]:
                lst.append('%s' % (type_tree.eval(row, row_data)))

    # 每行结尾都加个,有利于版本管理工具diff
    lst = map(lambda x:x+Literals.separator, lst)

    out = ('return ' + Literals.struct_fmt) % \
        (Literals.newline 
        + Literals.newline.join(lst)
        + Literals.newline)

    # 输出文件
    with codecs.open(out_file_path, "w+", "utf-8") as f:
        f.write(out)
    print('%s -> %s' % (os.path.abspath(file_path), os.path.abspath(out_file_path)))

def error(*args, **kwargs):
    return print(*args, file=sys.stderr, **kwargs)

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
        try:
            try:
                xls2lua(input_file, output_file, verbose=True)
            # 将xlrd的异常转化为自定义异常向上传播
            except xlrd.biffh.XLRDError as e:
                raise FileFormatError(str(e))
        except (ParseError,EvalError,IOError,FileFormatError) as e:
            error(e)
            return 1
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
    # main(['', './example/example.xlsx'])
    # main(['', './example/list.xlsx'])
    # main(['', './example/error.xlsx'])
    # main(['', './example/empty.xlsx'])
    # main(['', './example/invalid-file-format.xlsx'])
    # main(['', './example/define.xlsx'])
