# -*- coding: utf-8 -*-
import sys
import xlrd
import re
from six import string_types
from peg_parser.id import get_or_create_parent
from peg_parser.type import parse_type_tree
from type_define import Types, value_types, empty_values
from exceptions import *
from type_tree import TypeTree
from value_tree import ValueTree
from span import Span
from utils import cell_to_text

# 正则
array_pat = re.compile(r'^(\w+)\[(\d+)\]$')
setting_pat = re.compile(r'//\$(.+)$')


# 读取xls文件内容，并过滤注释行
# 返回[(sheet.name, [(row, row_cells), ...], [settings, ...])]
def read_sheets_from_xls(file_path):
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
            if isinstance(text, string_types) and text.startswith('//'):
                if reading_setting:
                    m = setting_pat.match(text)
                    if m:
                        settings.append(m.group(1))
                continue
            cells = [cell_to_text(cell) for cell in sheet.row(row)]
            row_cells.append((row, cells))
            reading_setting = False
        if len(row_cells) > 0:
            sheets.append((sheet.name, row_cells, settings))
    return sheets


def parse_type(text: str, span: Span):
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
        type_tree.set_span(span)
    return type_tree


# 输入sheet构建类型树
def build_type_tree(sheet_name: str, sheet_cells):
    (option_row, option_row_cells) = sheet_cells[0]
    (type_row, type_row_cells) = sheet_cells[1]
    (id_row, id_row_cells) = sheet_cells[2]
    root = TypeTree(Types.struct_t)  # todo:根节点不一定是struct???
    left_side_field = None
    for col in range(len(option_row_cells)):
        # 前三行约定为定义行
        option_text = option_row_cells[col]
        type_text = type_row_cells[col]
        id_text = id_row_cells[col]

        # option与类型同时为空的列约定注释列，不参导出
        if option_text in empty_values and type_text in empty_values:
            continue

        type_span = Span(sheet_name, type_row, col)
        id_span = Span(sheet_name, id_row, col)
        (parent_node, field_name) = get_or_create_parent(id_text, root, type_span)

        # 解析数据定义
        field_node = parse_type_tree(type_text, type_span)
        if field_node is None:
            # 声明了未知数据类型
            raise StructureError('类型错误', '声明了未知数据类型%s' % type_text, type_span)
        field_node.set_span(type_span)
        field_node.set_option(option_text)

        # 约束冲突
        if field_node.default is not None and field_node.unique:
            raise StructureError('约束冲突', '列约束不能同时拥有unique和def,%s' % id_text, id_span)

        # 检查重复定义域
        if parent_node.get_member(field_name) is not None:
            raise StructureError('重复定义', '重复定义了成员%s' % id_text, Span(sheet_name, id_row, col))

        # 检查是否连续定义在一块
        if parent_node != root and len(parent_node.members) > 0:
            (_, left_brother) = parent_node.members[-1]
            if left_brother.span:
                left_brother_col = left_brother.span.col
                if left_brother != left_side_field:
                    left_side_path = id_row_cells[left_brother_col]
                    raise StructureError('格式错误', '结构体或数组成员必须连续定义在一起,成员%s必须紧跟在%s右侧' % (id_text, left_side_path), id_span)
        left_side_field = field_node
        parent_node.add_member(field_name, field_node)
    # todo:还需要检查数组元素是否同构???
    return root


# 检查类型树之间是否存在结构冲突
def check_type_conflicet(lhs_key, lhs: TypeTree, rhs_key, rhs: TypeTree):
    # 宽度优先遍历
    def bfs_walk(lhs_key, lhs, rhs_key, rhs):
        span = rhs.span or Span('none', 0, 0)
        # 检查不同类型树之间的同项类型是否一致
        if lhs.type != rhs.type:
            raise StructureError('类型冲突', '项:%s类型(%s)跟项:%s类型(%s)不同' % (lhs_key, lhs.type, rhs_key, rhs.type),
                                 span)

        # 检查约束冲突
        if lhs.is_unique() and not rhs.is_unique():
            raise StructureError('约束冲突', '项:%s(unique)跟项:%s约束类型不同' % (lhs_key, rhs_key),
                                 span)

        if lhs.is_required() and not rhs.is_required():
            raise StructureError('约束冲突', '项:%s(required)跟项:%s约束类型不同' % (lhs_key, rhs_key),
                                 span)

        for (k, m1) in lhs.members:
            m2 = rhs.get_member(k)
            if m2:
                bfs_walk('%s.%s' % (lhs_key, k), m1, '%s.%s' % (rhs_key, k), m2)
            elif m1.is_unique():
                # 如果某一列定义为unique，则其余sheet表也必须定义该列
                raise StructureError('约束冲突', '%s缺少unique项:%s' % (rhs_key, k),
                                     span)
            elif m1.is_required():
                # 如果某一列定义为required，则其余sheet表也必须定义该列
                raise StructureError('约束冲突', '%s缺少required项:%s' % (rhs_key, k),
                                     span)

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
        for (k, m) in tree.members:
            clone = path[:]
            clone.append(k)
            collect_check_cols(clone, m)

    (_, type_tree) = type_trees[0]
    for (k, m) in type_tree.members:
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
            col = unique_col.span.col
            for (row, row_data) in row_cells[3:]:
                value = row_data[col]
                if value in empty_values:
                    continue
                if value in unique_set:
                    col_path = '.'.join([str(x) for x in path])
                    raise EvalError('数据冲突', '关于unique列(%s)的重复的值(%s)' % (col_path, value), Span(sheet_name, row, col))
                unique_set.add(value)

    # 检查所有必填列是否为空
    for path in requried_cols:
        i = 0
        for (sheet_name, row_cells, _) in sheets:
            (_, type_tree) = type_trees[i]
            i += 1
            # 根据path搜索到type_tree节点
            requried_col = get_member_by_path(type_tree, path)
            col = requried_col.span.col
            for (row, row_data) in row_cells[3:]:
                value = row_data[col]
                if value in empty_values:
                    col_path = '.'.join([str(x) for x in path])
                    raise EvalError('数据缺失', '关于required列(%s)的数据缺失' % col_path, Span(sheet_name, row, col))


def parse(file_path, verbose=True):
    sheets = read_sheets_from_xls(file_path)  # 过滤注释行

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
        if len(type_tree.members) == 2 and (type_tree.members[0][0], type_tree.members[1][0]) == ('key', 'value'):
            (key_type, value_type) = (type_tree.members[0][1], type_tree.members[1][1])
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
                raise StructureError('主键类型错误', '主键类型只能是整型或者字符串', Span(sheet_name, type_row, 0))

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
