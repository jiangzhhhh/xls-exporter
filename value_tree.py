from type_tree import TypeTree
from type_define import Types,value_types,empty_values
from utils import to_int,to_xls_col,to_xls_row
from exceptions import EvalError
from formatter import Formatter

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

