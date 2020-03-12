from utils import to_xls_row, to_xls_col


class Span(object):
    sheet: str
    row: int
    col: int

    def __init__(self, sheet: str, row: int, col: int):
        self.sheet = sheet
        self.row = row
        self.col = col

    def __str__(self):
        return '(%s,%s,%s)' % (self.sheet, self.xls_row, self.xls_col)

    @property
    def xls_row(self): return to_xls_row(self.row)

    @property
    def xls_col(self): return to_xls_col(self.col)


if __name__ == '__main__':
    print(Span('sheet1', 0, 1))
