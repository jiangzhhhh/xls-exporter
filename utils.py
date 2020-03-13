import xlrd
from xlrd.sheet import Cell
import math


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
    return str(num + 1)


# 为字符串内容添加双引号
translation = {
    '"': '\\',
    '\\': '\\\\',
    '\n': '\\n',
    '\\r': '\\r',
}


def add_quote(text: str):
    out = ''
    for c in text:
        v = translation.get(c, c)
        out += v
    return '"' + out + '"'


def to_int(v):
    return int(float(v))


def cell_to_text(cell: Cell):
    ctype = cell.ctype
    value = cell.value
    if ctype in (xlrd.XL_CELL_BLANK, xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_ERROR):
        return ''
    elif ctype == xlrd.XL_CELL_BOOLEAN:
        # int; 1 means TRUE, 0 means FALSE
        return str(value)
    elif ctype in (xlrd.XL_CELL_NUMBER, xlrd.XL_CELL_DATE):
        # float
        integer = math.floor(value)
        fact = value - integer
        if fact == 0:
            return str(integer)
        else:
            return str(value)
    elif ctype == xlrd.XL_CELL_TEXT:
        return value
