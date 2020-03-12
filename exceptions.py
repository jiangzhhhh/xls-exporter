from utils import to_int,to_xls_col,to_xls_row

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

