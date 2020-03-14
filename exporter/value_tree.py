from exporter.type_tree import TypeTree
from exporter.type_define import Types, value_types, empty_values
from exporter import exceptions
from exporter.formatter import LangFormatter
from exporter.lang.python import Formatter as PythonFormatter
from exporter.peg_parser import value as value_parser
import parsimonious
from typing import List


class ValueTree(object):
    def __init__(self, type_tree: TypeTree):
        self.type_tree = type_tree
        self.value = None
        self.members = []
        for (k, m) in self.type_tree.members:
            self.add_member(k, ValueTree(m))

    def add_member(self, key: [str, int], member: 'ValueTree'):
        self.members.append((key, member))

    def _eval_embedded_array(self, row: int, text: str, explicit: bool):
        elem_type = self.type_tree.elem_type

        def loop_body(in_out_text, index):
            item_value = ValueTree(elem_type)
            pos = item_value._eval_generic(row, in_out_text, False)
            self.add_member(index, item_value)
            return in_out_text[pos:].lstrip(), index + 1

        index = 0
        (remain_text, index) = loop_body(text, index)
        while len(remain_text) > 0:
            if not remain_text or remain_text[0] != ',':
                break
            remain_text = remain_text.lstrip(',')
            (remain_text, index) = loop_body(remain_text, index)
        return len(text) - len(remain_text)

    def _eval_tuple(self, row: int, text: str, explicit: bool):
        remain_text = text.lstrip()
        if explicit and (len(remain_text) < 2 or remain_text[0] != '('):
            return 0
        remain_text = remain_text.lstrip('(')
        for (i, m) in self.members:
            if i > 0:
                if not remain_text or remain_text[0] != ',':
                    return 0
                remain_text = remain_text.lstrip(',')
            pos = m._eval_generic(row, remain_text, False)
            remain_text = remain_text[pos:]
        if explicit and (not remain_text or remain_text[0] != ')'):
            return 0
        remain_text = remain_text.lstrip(')')
        remain_text = remain_text.lstrip()
        return len(text) - len(remain_text)

    def _eval_string(self, row: int, text: str, explicit: bool) -> int:
        pos = 0
        if explicit:
            (self.value, pos) = value_parser.match_string(text)
        else:
            stripped = text.strip()
            if (stripped[0] == stripped[-1] == '"') or (stripped[0] == stripped[-1] == "'"):
                (self.value, pos) = value_parser.match_string(text)
            else:
                self.value, pos = text, len(text)
        return pos

    def _eval_value(self, row: int, text: str, explicit: bool) -> int:
        matcher = value_parser.__dict__['match_' + self.type_tree.type]
        (self.value, pos) = matcher(text)
        return pos

    def _eval_generic(self, row: int, text: str, top_define: bool):
        span = self.type_tree.span
        pos = 0
        try:
            if text in empty_values:
                return 0
            # 将xls单元格文本转换为内部表示值
            methods = self.__class__.__dict__
            eval_func = methods.get('_eval_' + self.type_tree.type, methods['_eval_value'])
            pos = eval_func(self, row, text, not top_define)
        except parsimonious.exceptions.ParseError:
            raise exceptions.EvalError('数据类型错误', '填写了定义类型%s无法解析的值的值:%s' % (self.type_tree.type, text), span)
        return pos

    def eval(self, row: int, row_data: List[str]) -> None:
        node_type = self.type_tree.type
        if node_type in (Types.array_t, Types.struct_t):
            for (_, member) in self.members:
                member.eval(row, row_data)
        else:
            span = self.type_tree.span
            text = row_data[span.col]
            # 如果有填写了空值，且存在默认值，则替换之
            if self.type_tree.default is not None and (text in empty_values):
                text = self.type_tree.default
            pos = self._eval_generic(row, text, top_define=True)
            if pos < len(text):
                raise exceptions.EvalError('数据类型错误', '填写了定义类型%s无法解析的值的值:%s' % (str(self.type_tree), text), span)

    def __str__(self):
        return self.tostring()

    def tostring(self, formatter: LangFormatter = PythonFormatter()):
        return formatter.as_any(self, 0)

    def is_empty(self) -> bool:
        if self.type_tree.type in (Types.struct_t, Types.array_t, Types.dict_t, Types.embedded_array_t, Types.tuple_t):
            for (_, m) in self.members:
                if not m.is_empty():
                    return False
            return True
        else:
            return self.value is None
