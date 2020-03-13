from exporter.type_tree import TypeTree
from exporter.type_define import Types, value_types, empty_values
from exporter.exceptions import EvalError
from exporter.formatter import Formatter
from exporter.peg_parser import value as value_parser


class ValueTree(object):
    def __init__(self, type_tree: TypeTree):
        self.type_tree = type_tree
        self.value = None
        self.members = []
        for (k, m) in self.type_tree.members:
            self.add_member(k, ValueTree(m))

    def add_member(self, key: [str, int], member: 'ValueTree'):
        self.members.append((key, member))

    def _eval_array(self, row: int, text: str):
        elem_type = self.type_tree.elem_type

        def loop_body(in_out_text, index):
            item_value = ValueTree(elem_type)
            pos = item_value._eval_value(row, in_out_text)
            self.add_member(index, item_value)
            return (in_out_text[pos:].lstrip(), index + 1)

        index = 0
        (remain_text, index) = loop_body(text, index)
        while len(remain_text) > 0:
            if not remain_text or remain_text[0] != ',':
                break
            remain_text = remain_text.lstrip(',')
            (remain_text, index) = loop_body(remain_text, index)
        return len(text) - len(remain_text)

    def _eval_tuple(self, row: int, text: str):
        remain_text = text
        remain_text = remain_text.lstrip()
        if len(remain_text) < 2 or remain_text[0] != '(':
            return 0
        remain_text = remain_text.lstrip('(')
        for (i, m) in self.members:
            if i > 0:
                if not remain_text or remain_text[0] != ',':
                    return 0
                remain_text = remain_text.lstrip(',')
            pos = m._eval_value(row, remain_text)
            remain_text = remain_text[pos:]
        remain_text = remain_text.lstrip()
        if not remain_text or remain_text[0] != ')':
            return 0
        remain_text = remain_text.lstrip(')')
        remain_text = remain_text.lstrip()
        return len(text) - len(remain_text)

    def _eval_value(self, row: int, text: str):
        span = self.type_tree.span
        def_text = False
        pos = 0
        # 如果有填写了空值，且存在默认值，则替换之
        if self.type_tree.default is not None and (text in empty_values):
            text = self.type_tree.default
            def_text = True
        try:
            if text in empty_values:
                return 0

            # 将xls单元格文本转换为内部表示值
            if self.type_tree.type in value_types:
                matcher = value_parser.__dict__['match_' + self.type_tree.type]
                (self.value, pos) = matcher(text)
            elif self.type_tree.type == Types.embedded_array_t:  # 内嵌数组
                pos = self._eval_array(row, text)
            elif self.type_tree.type == Types.tuple_t:  # 元组
                pos = self._eval_tuple(row, text)
        except ValueError:
            raise EvalError('数据类型错误', '填写了跟定义类型%s不一致的值:%s' % (self.type_tree.type, text), span)
        if def_text:
            pos = 0
        return pos

    def eval(self, row: int, row_data):
        node_type = self.type_tree.type
        if node_type in (Types.array_t, Types.struct_t):
            for (_, member) in self.members:
                member.eval(row, row_data)
        else:
            span = self.type_tree.span
            text = row_data[span.col]
            pos = self._eval_value(row, text)
            if pos < len(text):
                raise EvalError('数据类型错误', '填写了跟定义类型%s不一致的值:%s' % (str(self.type_tree), text), span)

    def __str__(self):
        return self.tostring(formatter=Formatter())

    def tostring(self, formatter: Formatter = Formatter()):
        return formatter.as_any(self, 0)

    def is_empty(self):
        if self.type_tree.type in (Types.struct_t, Types.array_t, Types.dict_t, Types.embedded_array_t, Types.tuple_t):
            for (_, m) in self.members:
                if not m.is_empty():
                    return False
            return True
        else:
            return self.value is None
