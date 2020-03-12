from utils import to_int, to_xls_col, to_xls_row
from span import Span


# 异常定义
class ParseError(RuntimeError):
    title: str = None
    detail: str = None

    def __init__(self, title: str, detail: str):
        self.title = title
        self.detail = detail
        self.message = \
            'error:%s\n' \
            'title:%s\n' \
            'detail:%s' \
            % (type(self).__name__, self.title, self.detail)


# 结构异常
class StructureError(ParseError):
    span: Span = None

    def __init__(self, title: str, detail: str, span: Span):
        super().__init__(title, detail)
        self.span = span
        self.message += \
            '\n' \
            'sheet:%s\n' \
            'row:%s\n' \
            'col:%s' \
            % (span.sheet, span.xls_row, span.xls_col)


# 数据异常
class EvalError(ParseError):
    span: Span = None

    def __init__(self, title: str, detail: str, span: Span):
        super(EvalError, self).__init__(title, detail)
        self.span = span
        self.message += \
            '\n' \
            'sheet:%s\n' \
            'row:%s\n' \
            'col:%s' \
            % (span.sheet, span.xls_row, span.xls_col)


# 文件格式异常
class FileFormatError(ParseError):
    pass
