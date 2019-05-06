# -*- coding: utf-8 -*-
import sys
import xlrd
import codecs
import re
import os

# fuck py2
strings = (str,)
try:
    reload(sys)
    sys.setdefaultencoding("utf-8")
    strings = (basestring,str)
except:
    pass

# 异常定义
# 结构异常
class ParseError(RuntimeError):
    pass

# 数据异常
class EvalError(ParseError):
    pass

# 文件格式异常
class FileFormatError(ParseError):
    pass

# 定义符号
class Types(object):
    int_t = 'int'
    bool_t = 'bool'
    string_t = 'string'
    float_t = 'float'
    struct_t = 'struct'
    array_t = 'array'
    embedded_array_t = 'embedded_array'
    dict_t = 'dict'

# 直接求值类型
value_types = (Types.int_t,Types.float_t,Types.bool_t,Types.string_t)
empty_values = ('', None)

# 正则
array_pat = re.compile(r'^(\w+)\[(\d+)\]$')
embedded_array_pat = re.compile(r'^(\w+)\[\]$')
default_option_pat = re.compile(r'default\s*=\s*(.+)$')
setting_pat = re.compile(r'//\$(.+)$')

class TypeTree(object):
    def __init__(self, type):
        assert type,type
        self.type = type
        self.members = []
        self.cursor = None
        self.unique = False
        self.required = False
        self.default = None
        self.value = None
        self.elem_type = None # only for embedded array

    def set_cursor(self, sheet_name, col):
        self.cursor = (sheet_name, col)

    def add_member(self, key, member):
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

    def set_embedded_type(self, elem_type):
        self.elem_type = elem_type

    # 是否唯一项,不允许出现重复值
    def is_unique(self):
        return self.unique

    # 是否必填项
    def is_required(self):
        return self.required

    def __str__(self):
        def to_str_recursion(tree, ident):
            s = ''
            if tree.type == Types.embedded_array_t:
                s += '%s[]' % (tree.elem_type)
            else:
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

class Formatter(object):
    def as_any(self, value_tree, ident):
        type = value_tree.type_tree.type
        if type == Types.struct_t:
            return self.as_struct(value_tree, ident)
        elif type in (Types.array_t, Types.embedded_array_t):
            return self.as_array(value_tree, ident)
        elif type == Types.dict_t:
            return self.as_dict(value_tree, ident)
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
    def as_struct(self, value_tree, ident):
        s = '{'
        if ident == 0: s += '\n'
        for (k,m) in value_tree.members:
            s += '%s:%s,' % (k, self.as_any(m, ident+1))
            if ident == 0: s += '\n'
        s += '}'
        return s
    def as_array(self, value_tree, ident):
        s = '['
        if ident == 0: s += '\n'
        for (k,m) in value_tree.members:
            s += '%s,' % (self.as_any(m, ident+1))
            if ident == 0: s += '\n'
        s += ']'
        return s
    def as_dict(self, value_tree, ident):
        s = '{'
        if ident == 0: s += '\n'
        for (k,m) in value_tree.members:
            s += '%s:%s,' % (k, self.as_any(m, ident+1))
            if ident == 0: s += '\n'
        s += '}'
        return s
    def as_int(self, value_tree, ident):
        return str(value_tree.value)
    def as_float(self, value_tree, ident):
        return str(value_tree.value)
    def as_bool(self, value_tree, ident):
        return str(value_tree.value)
    def as_string(self, value_tree, ident):
        return add_quote(value_tree.value)
    def as_nil(self, value_tree, ident):
        return 'None'

class ValueTree(object):
    def __init__(self, type_tree):
        self.type_tree = type_tree
        self.value = None
        self.members = []
        for (k,m) in self.type_tree.members:
            self.add_member(k, ValueTree(m))

    def add_member(self, key, member):
        self.members.append((key, member))

    def eval_value(self, text):
        (sheet_name, col) = self.type_tree.cursor
        # 如果有填写了空值，且存在默认值，则替换之
        if self.type_tree.default is not None and (text in empty_values):
            text = self.type_tree.default
        try:
            # 将xls单元格文本转换为内部表示值
            if self.type_tree.type in value_types:
                if text in empty_values:
                    self.value = None
                elif self.type_tree.type == Types.int_t:
                    self.value = int(text)
                elif self.type_tree.type == Types.float_t:
                    self.value = float(text)
                elif self.type_tree.type == Types.bool_t:
                    lower_str = str(int(text)).lower()
                    if lower_str in ('0', 'false'):
                        self.value = False
                    elif lower_str in ('1', 'true'):
                        self.value = True
                    else:
                        raise ValueError
                elif self.type_tree.type == Types.string_t:
                    self.value = text
                else:
                    raise ValueError
            elif self.type_tree.type == Types.embedded_array_t: # 内嵌数组
                arr = text.split(',')
                size_arr = len(arr)
                # 从后往前遍历，找到最后一个有效下标，用于过滤尾部空项
                last_valid_index = size_arr-1
                for v in arr[::-1]:
                    if v != '' and v is not None:
                        break
                    last_valid_index -= 1
                # 遍历至最后一个有效下标为止
                i = 0
                for v in arr[:last_valid_index+1]:
                    elem_member_type = TypeTree(self.type_tree.elem_type)
                    elem_member_type.set_cursor(*self.type_tree.cursor)
                    elem_value_tree = ValueTree(elem_member_type)
                    elem_value_tree.eval_value(v)
                    self.add_member(i, elem_value_tree)
                    i += 1
        except ValueError:
            eval_error('表:%s,列:%s,行:%s,填写了跟定义类型(%s)不一致的值:%s' % (sheet_name, to_xls_col(col), to_xls_row(row), self.type_tree.type, text))

    def eval(self, row, row_data):
        if self.type_tree.type in (Types.array_t,Types.struct_t):
            for (_,member) in self.members:
                member.eval(row, row_data)
        else:
            (sheet_name, col) = self.type_tree.cursor
            text = row_data[col].value
            self.eval_value(text)

    def __str__(self):
        return self.tostring(formatter=Formatter())

    def tostring(self, formatter=Formatter()):
        return formatter.as_any(self, 0)

    def is_empty(self):
        if self.type_tree.type in (Types.struct_t, Types.array_t, Types.dict_t, Types.embedded_array_t):
            for (_, m) in self.members:
                if m.is_empty():
                    return False
            return True
        else:
            return self.value is None

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

# 输出解析错误信息并退出程序
def parse_error(msg):
    raise ParseError('[解析错误]%s' % msg)

# 输出求值错误信息并退出程序
def eval_error(msg):
    raise EvalError('[求值错误]%s' % msg)

# 为字符串内容添加双引号
translation = {
    '"':'\\"',
    '\\':'\\\\"',
    '\n':'\\n',
    '\\r':'\\r',
}
def add_quote(text):
    out = ''
    for c in text:
        v = translation.get(c, c)
        out += v
    return '"' + out + '"'

# 读取xls文件内容，并过滤注释行
# 返回{sheet_name:[(row, row_cells),...]}
def read_sheets_from_xls(file_path):
    workbook = None
    try:
        workbook = xlrd.open_workbook(file_path)
    # 将xlrd的异常转化为自定义异常向上传播
    except xlrd.biffh.XLRDError as e:
        raise FileFormatError(str(e))
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
            decl_type = Types.embedded_array_t
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
        if decl_type == Types.embedded_array_t:
            field_member.set_embedded_type(elem_type)
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

def parse(file_path, verbose=True):
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

    root = None
    # 求值
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
            (key_type, value_type) = (type_tree.members[0][1],type_tree.members[1][1])
            root = root or ValueTree(TypeTree(Types.struct_t))
            # 前三行为结构定义行，从第四行开始遍历
            for (row, row_data) in row_cells[3:]:
                key_value = ValueTree(key_type)
                value_value = ValueTree(value_type)

                key_value.eval(row, row_data)
                value_value.eval(row, row_data)

                root.add_member(key_value.value, value_value)
        elif type_tree.members[0][1].is_unique():
            (_, key_type) = type_tree.members[0]

            if key_type.type not in (Types.int_t, Types.string_t):
                (_, col) = key_type.cursor
                parse_error('主键类型错误,表:%s,列:%s,主键类型只能是整型或者字符串' % (sheet_name, to_xls_col(col)))

            root = root or ValueTree(TypeTree(Types.dict_t))
            # 前三行为结构定义行，从第四行开始遍历
            for (row, row_data) in row_cells[3:]:
                key_value = ValueTree(key_type)
                value_value = ValueTree(type_tree)

                key_value.eval(row, row_data)
                value_value.eval(row, row_data)

                root.add_member(key_value.value, value_value)
        else:
            root = root or ValueTree(TypeTree(Types.array_t))
            # 前三行为结构定义行，从第四行开始遍历
            i = 0
            for (row, row_data) in row_cells[3:]:
                value_value = ValueTree(type_tree)
                value_value.eval(row, row_data)
                root.add_member(i, value_value)
                i += 1
    return root or ValueTree(TypeTree(Types.dict_t))

def error(msg):
    sys.stderr.write(msg + '\n')

if __name__ == '__main__':
    def protect_parse(file):
        try:
            parse(file, verbose=False)
        except Exception as e:
            error('%s error:%s' % (file, str(e)))
    protect_parse('example/define.xlsx')
    protect_parse('example/example.xlsx')
    protect_parse('example/empty.xlsx')
    protect_parse('example/list.xlsx')
    protect_parse('example/error.xlsx')
    protect_parse('example/invalid-file-format.xlsx')