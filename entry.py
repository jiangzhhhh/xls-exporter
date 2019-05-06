# -*- coding: utf-8 -*-
import os
import xls_exporter
from xls_exporter import error
import codecs

def main(argv, file_extention, formatter):
    argc = len(argv)
    if argc < 2:
        msg = 'usage: xls2%s.py <input_file> [<output_file>]' % file_extention
        error(msg)
        return 2
    else:
        input_file = argv[1]
        if argc > 2:
            output_file = argv[2]
        else:
            pre, ext = os.path.splitext(input_file)
            output_file = pre + '.' + file_extention

        try:
            value_tree = xls_exporter.parse(input_file, verbose=True)
            out = value_tree.tostring(formatter=formatter)
            # 输出文件
            with codecs.open(output_file, "w+", "utf-8") as f:
                f.write(out)
            print('write file:%s' % os.path.abspath(output_file))
        except (xls_exporter.ParseError) as e:
            error(str(e))
            return 3
    return 0
