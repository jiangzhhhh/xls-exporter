# -*- coding: utf-8 -*-
import os
import xls_exporter
from xls_exporter import error
import codecs

def main(sys_argv, file_extention, formatter):
    argv = []
    options = []
    for arg in sys_argv:
        if arg.startswith('--'):
            options.append(arg)
        else:
            argv.append(arg)
    only_check = '--check' in options
    argc = len(argv)
    if argc < 1:
        msg = 'usage: xls2%s.py <input_file> [<output_file>] [option]\n'\
        'option:\n'\
        '    --check: only check'\
        % file_extention
        error(msg)
        return 2
    elif only_check:
        input_file = argv[1]
        try:
            value_tree = xls_exporter.parse(input_file, verbose=True)
        except (xls_exporter.ParseError) as e:
            error(e.message)
            return 3
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
            error(e.message)
            return 3
    return 0
