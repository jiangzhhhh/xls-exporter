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
class ParseError(RuntimeError):
    title = None
    detail = None
    def __init__(self, title, detail):
        self.title = title
        self.detail = detail
        self.message = \
            'error:%s\n'\
            'title:%s\n'\
            'detail:%s'\
            % (type(self).__name__, self.title, self.detail)

# 结构异常
class StructureError(ParseError):
    sheet = None
    row = None
    col = None
    def __init__(self, title, detail, sheet, row, col):
        super().__init__(title, detail)
        self.sheet = sheet
        self.row = row
        self.col = col
        self.message +=\
            '\n'\
            'sheet:%s\n'\
            'row:%s\n'\
            'col:%s'\
            % (self.sheet, to_xls_row(self.row), to_xls_col(self.col))

# 数据异常
class EvalError(ParseError):
    sheet = None
    row = None
    col = None
    def __init__(self, title, detail, sheet, row, col):
        super(EvalError, self).__init__(title, detail)
        self.sheet = sheet
        self.row = row
        self.col = col
        self.message +=\
            '\n'\
            'sheet:%s\n'\
            'row:%s\n'\
            'col:%s'\
            % (self.sheet, to_xls_row(self.row), to_xls_col(self.col))

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
    tuple_t = 'tuple'

# 直接求值类型
value_types = (Types.int_t,Types.float_t,Types.bool_t,Types.string_t)
empty_values = ('', None)

# 正则
array_pat = re.compile(r'^(\w+)\[(\d+)\]$')
default_option_pat = re.compile(r'.*def\s*:\s*(.+)$')
setting_pat = re.compile(r'//\$(.+)$')

class TypeTree(object):
    def __init__(self, type: str):
        assert type,type
        self.type = type
        self.members = []
        self.span = None
        self.unique = False
        self.required = False
        self.default = None
        self.elem_type = None # only for embedded array

    def set_span(self, sheet_name: str, row: int, col: int):
        self.span = (sheet_name, row, col)
        if self.elem_type:
            self.elem_type.span = self.span

    def add_member(self, key: [str, int], member: 'TypeTree'):
        self.members.append((key,member))

    def get_member(self, member_name: [str, int]):
        for (key,m) in self.members:
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
                s += '(%s)' % (','.join([to_str_recursion(m) for (_,m) in tree.members]))
            elif tree.type in value_types:
                s += tree.type
            if tree.span:
                (sheet, _, col) = tree.span
                s += '(%s:%s)' % (sheet, to_xls_col(col))
            if tree.is_unique():
                s += 'u'
            if tree.is_required():
                s += '!'

            if tree.type == Types.struct_t or tree.type == Types.dict_t:
                s += '{%s}' % (','.join([str(k)+':'+to_str_recursion(m) for (k,m) in tree.members]))
            elif tree.type == Types.array_t:
                s += '[%s]' % (','.join([to_str_recursion(m) for (_, m) in tree.members]))

            return s
        return to_str_recursion(self)

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
        for (k,m) in value_tree.members:
            s += '%s:%s,' % (k, self.as_any(m, ident+1))
            if ident == 0: s += '\n'
        s += '}'
        return s
    def as_array(self, value_tree: 'ValueTree', ident: int):
        s = '['
        if ident == 0: s += '\n'
        for (k,m) in value_tree.members:
            s += '%s,' % (self.as_any(m, ident+1))
            if ident == 0: s += '\n'
        s += ']'
        return s
    def as_dict(self, value_tree: 'ValueTree', ident: int):
        s = '{'
        if ident == 0: s += '\n'
        for (k,m) in value_tree.members:
            s += '%s:%s,' % (k, self.as_any(m, ident+1))
            if ident == 0: s += '\n'
        s += '}'
        return s
    def as_tuple(self, value_tree: 'ValueTree', ident: int):
        s = '('
        if ident == 0: s += '\n'
        for (k,m) in value_tree.members:
            s += '%s,' % (self.as_any(m, ident+1))
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

class ValueTree(object):
    def __init__(self, type_tree: TypeTree):
        self.type_tree = type_tree
        self.value = None
        self.members = []
        for (k,m) in self.type_tree.members:
            self.add_member(k, ValueTree(m))

    def add_member(self, key: [str, int], member: 'ValueTree'):
        self.members.append((key, member))

    def eval_value(self, row: int, text: str):
        (sheet_name, _, col) = self.type_tree.span
        # 如果有填写了空值，且存在默认值，则替换之
        if self.type_tree.default is not None and (text in empty_values):
            text = self.type_tree.default
        try:
            # 将xls单元格文本转换为内部表示值
            if self.type_tree.type in value_types:
                text = str(text)
                pos = text.find(',')
                if pos == -1:
                    term = text
                else:
                    term = text[:pos]
                if term in empty_values:
                    self.value = None
                elif self.type_tree.type == Types.int_t:
                    self.value = to_int(term)
                elif self.type_tree.type == Types.float_t:
                    self.value = float(term)
                elif self.type_tree.type == Types.bool_t:
                    lower_str = str(to_int(term)).lower()
                    if lower_str in ('0', 'false'):
                        self.value = False
                    elif lower_str in ('1', 'true'):
                        self.value = True
                    else:
                        raise ValueError
                elif self.type_tree.type == Types.string_t:
                    self.value = term
                else:
                    raise ValueError
                return len(term)
            elif self.type_tree.type == Types.embedded_array_t: # 内嵌数组
                text = str(text)
                if not text:
                    return 0
                elem_member_type = self.type_tree.elem_type
                pos = 0
                i = 0
                while pos <= len(text):
                    beg = pos
                    term = text[beg:]
                    elem_value_tree = ValueTree(elem_member_type)
                    pos += elem_value_tree.eval_value(row, term) + 1
                    if elem_value_tree.is_empty():
                        raise EvalError('数据类型错误', '填写了跟定义类型(%s)不一致的值:%s' % (elem_member_type.type, term), sheet_name, row, col)
                    self.add_member(i, elem_value_tree)
                    i += 1
            elif self.type_tree.type == Types.tuple_t:  # 元组
                text = str(text)
                if not text:
                    return 0
                pos = 0
                bracket_style = text[0] == '('
                if bracket_style:
                    pos = 1
                num_members = len(self.members)
                for (i,member) in self.members:
                    term = ''
                    for ch in text[pos:]:
                        if ch == ',' or ch == ')':
                            break
                        term += ch
                    member.eval_value(row, term)
                    pos += len(term)
                    if i < num_members - 1:
                        pos += 1
                    if member.is_empty():
                        raise EvalError('数据类型错误', '填写了跟定义类型(%s)不一致的值:%s' % (member.type_tree, term), sheet_name, row, col)
                if bracket_style:
                    pos += 1
                return pos
        except ValueError as e:
            raise EvalError('数据类型错误', '填写了跟定义类型(%s)不一致的值:%s' % (self.type_tree.type, text), sheet_name, row, col)

    def eval(self, row: int, row_data):
        if self.type_tree.type in (Types.array_t,Types.struct_t):
            for (_,member) in self.members:
                member.eval(row, row_data)
        else:
            (sheet_name, _, col) = self.type_tree.span
            text = row_data[col].value
            self.eval_value(row, text)

    def __str__(self):
        return self.tostring(formatter=Formatter())

    def tostring(self, formatter:Formatter=Formatter()):
        return formatter.as_any(self, 0)

    def is_empty(self):
        if self.type_tree.type in (Types.struct_t, Types.array_t, Types.dict_t, Types.embedded_array_t, Types.tuple_t):
            for (_, m) in self.members:
                if not m.is_empty():
                    return False
            return True
        else:
            return self.value is None

# 将整数转换为excel的列
def to_xls_col(num: int):
    if num < 0:
        return 'NAN'
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

def to_xls_row(num: int):
    if num < 0:
        return 'NAN'
    return str(num+1)

def to_int(v):
    return int(float(v))

# 为字符串内容添加双引号
translation = {
    '"':'\\"',
    '\\':'\\\\"',
    '\n':'\\n',
    '\\r':'\\r',
}
def add_quote(text: str):
    out = ''
    for c in text:
        v = translation.get(c, c)
        out += v
    return '"' + out + '"'

# 读取xls文件内容，并过滤注释行
# 返回[(sheet.name, [(row, row_cells), ...], [settings, ...])]
def read_sheets_from_xls(file_path):
    workbook = None
    try:
        workbook = xlrd.open_workbook(file_path)
    # 将xlrd的异常转化为自定义异常向上传播
    except xlrd.biffh.XLRDError as e:
        raise FileFormatError('文件格式错误', str(e))
    sheets = []
    reading_setting = True
    for sheet in workbook.sheets():
        if sheet.ncols <= 0:
            continue
        # sheet名字以=开头会被过滤，不进行导出
        if sheet.name.startswith('='):
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

def parse_type(text, span):
    type_tree = None
    if text in value_types:
        # 基本类型
        type_tree = TypeTree(text)
    if text.endswith('[]'):
        # 内嵌数组
        type_tree = TypeTree(Types.embedded_array_t)
        elem_type = parse_type(text[:-2], span)
        if elem_type is None:
            return None
        type_tree.set_embedded_type(elem_type)
    if text[0] == '(' and text[-1] == ')':
        # 元组
        type_tree = TypeTree(Types.tuple_t)
        terms = text[1:-1].split(',')
        for i in range(len(terms)):
            term = terms[i].strip()
            term_type = parse_type(term, span)
            if term_type is None:
                return None
            type_tree.add_member(i, term_type)
    if type_tree:
        type_tree.set_span(*span)
    return type_tree

# 输入sheet构建类型树
def build_type_tree(sheet_name: str, sheet_cells):
    (option_row, option_row_cells) = sheet_cells[0]
    (type_row, type_row_cells) = sheet_cells[1]
    (id_row, id_row_cells) = sheet_cells[2]
    type_tree = TypeTree(Types.struct_t) # todo:根节点不一定是struct???
    left_side_field = None
    for col in range(len(option_row_cells)):
        # 前三行约定为定义行
        option = option_row_cells[col].value
        decl_type = type_row_cells[col].value
        path = id_row_cells[col].value

        # option与类型同时为空的列约定注释列，不参导出
        if option in empty_values and decl_type in empty_values:
            continue

        # 如果定义了路径，则需要向上查找到父节点
        splited = path.split('.')
        parent = type_tree
        for term in splited[:-1]:
            m = array_pat.match(term)
            index = None
            if m:
                term = m.group(1)
                index = to_int(m.group(2))
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

        # 解析数据定义
        field_member = parse_type(decl_type, (sheet_name, type_row, col))
        if field_member is None:
            # 声明了未知数据类型
            raise StructureError('类型错误', '声明了未知数据类型%s' % (decl_type), sheet_name, type_row, col)
        field_member.set_option(option)

        # 约束冲突
        if field_member.default is not None and field_member.unique:
            raise StructureError('约束冲突', '%s列约束不能同时拥有unique和def,%s' % path, sheet_name, id_row, col)

        # 检查重复定义域
        if parent.get_member(field_name) is not None:
            raise StructureError('重复定义', '重复定义了成员%s' % path, sheet_name, id_row, col)

        # 检查是否连续定义在一块
        if len(parent.members) > 0:
            (_, left_brother) = parent.members[-1]
            if left_brother.span:
                (_, _, left_brother_col) = left_brother.span
                if left_brother != left_side_field:
                    left_side_path = id_row_cells[left_brother_col].value
                    raise StructureError('格式错误', '结构体或数组成员必须连续定义在一起,成员%s必须紧跟在%s右侧' % (path, left_side_path), sheet_name, id_row, col)
        parent.add_member(field_name, field_member)
        left_side_field = field_member
    # todo:还需要检查数组元素是否同构???
    return type_tree

# 检查类型树之间是否存在结构冲突
def check_type_conflicet(lhs_key, lhs: TypeTree, rhs_key, rhs: TypeTree):
    # 宽度优先遍历
    def bfs_walk(lhs_key, lhs, rhs_key, rhs):
        (rhs_sheet, rhs_row, rhs_col) = ('none', -1, -1)
        if rhs.span:
            (rhs_sheet, rhs_row, rhs_col) = rhs.span
        # 检查不同类型树之间的同项类型是否一致
        if lhs.type != rhs.type:
            raise StructureError('类型冲突', '项:%s类型(%s)跟项:%s类型(%s)不同' % (lhs_key, lhs.type, rhs_key, rhs.type),
                rhs_sheet, rhs_row, rhs_col)

        # 检查约束冲突
        if lhs.is_unique() and not rhs.is_unique():
            raise StructureError('约束冲突', '项:%s(unique)跟项:%s约束类型不同' % (lhs_key, rhs_key),
                rhs_sheet, rhs_row, rhs_col)

        if lhs.is_required() and not rhs.is_required():
            raise StructureError('约束冲突', '项:%s(required)跟项:%s约束类型不同' % (lhs_key, rhs_key),
                rhs_sheet, rhs_row, rhs_col)

        for (k,m1) in lhs.members:
            m2 = rhs.get_member(k)
            if m2:
                bfs_walk('%s.%s' % (lhs_key, k), m1, '%s.%s' % (rhs_key, k), m2)
            elif m1.is_unique():
                # 如果某一列定义为unique，则其余sheet表也必须定义该列
                raise StructureError('约束冲突', '%s缺少unique项:%s' % (rhs_key, k),
                    rhs_sheet, rhs_row, rhs_col)
            elif m1.is_required():
                # 如果某一列定义为required，则其余sheet表也必须定义该列
                raise StructureError('约束冲突', '%s缺少required项:%s' % (rhs_key, k),
                        rhs_sheet, rhs_row, rhs_col)
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

    # 检查所有唯一列数据有没有重复
    for path in unique_cols:
        unique_set = set()
        i = 0
        for (sheet_name, row_cells, _) in sheets:
            (_, type_tree) = type_trees[i]
            i += 1
            # 根据path搜索到type_tree节点
            unique_col = get_member_by_path(type_tree, path)
            (_, _, col) = unique_col.span
            for (row, row_data) in row_cells[3:]:
                value = row_data[col].value
                if value in empty_values:
                    continue
                if value in unique_set:
                    col_path = '.'.join([str(x) for x in path])
                    raise EvalError('数据冲突', '关于unique列(%s)的重复的值(%s)' % (col_path, value), sheet_name, row, col)
                unique_set.add(value)

    # 检查所有必填列是否为空
    for path in requried_cols:
        i = 0
        for (sheet_name, row_cells, _) in sheets:
            (_, type_tree) = type_trees[i]
            i += 1
            # 根据path搜索到type_tree节点
            requried_col = get_member_by_path(type_tree, path)
            (_, _, col) = requried_col.span
            for (row, row_data) in row_cells[3:]:
                value = row_data[col].value
                if value in empty_values:
                    col_path = '.'.join([str(x) for x in path])
                    raise EvalError('数据缺失', '关于requried列(%s)的数据缺失' % (col_path), sheet_name, row, col)

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
                (_, _, col) = key_type.span
                (type_row, _) = row_cells[1]
                raise StructureError('主键类型错误', '主键类型只能是整型或者字符串', sheet_name, type_row, 0)

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
    print(parse('example/example.xlsx', verbose=True))
