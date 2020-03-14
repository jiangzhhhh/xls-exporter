# -*- coding: utf-8 -*-
import os
import sys
import importlib
import pkgutil
import getopt
import codecs
from exporter import xls_exporter
from exporter.formatter import LangFormatter
from exporter import exceptions
from exporter import lang as support_langs


def error(msg: str) -> None:
    sys.stderr.write(msg + '\n')


def cmd(argv):
    support_lang_list = ''
    lang_pkg = importlib.import_module('exporter.lang')
    for (_, name, _) in pkgutil.iter_modules(lang_pkg.__path__):
        support_lang_list += '    %s\n' % name
    usage = 'usage main.py <input_file> -l <lang> -o <output_file> [option]\n' \
            '  lang:\n' \
            '%s' \
            '  option:\n' \
            '    --check: only check, no output' % support_lang_list

    try:
        opts, args = getopt.getopt(argv, 'hi:l:o', ['--check'])
    except getopt.GetoptError:
        error(usage)
        return 2

    input_file = None
    lang = None
    output_file = None
    only_check = False

    for opt, arg in opts:
        if opt == '-h':
            print(usage)
            return 0
        elif opt == '-l':
            lang = arg
        elif opt == '-o':
            output_file = arg
        elif opt == '--check':
            only_check = True

    if not args:
        error(usage)
        return 2

    if lang is None:
        error(usage)
        return 2

    input_file = args[0]
    try:
        module = importlib.import_module('exporter.lang.%s' % lang)
        formatter = module.__dict__.get('Formatter')
        if not formatter:
            error('%s is not supported' % lang)
            return 2
    except ModuleNotFoundError:
        error('%s is not supported' % lang)
        return 2

    try:
        value_tree = xls_exporter.parse(input_file, verbose=True)
        if not only_check:
            out = value_tree.tostring(formatter=formatter())
            if output_file:
                # 输出文件
                with codecs.open(output_file, "w+", "utf-8") as f:
                    f.write(out)
                print('write file:%s' % os.path.abspath(output_file))
            else:
                print('-' * 10, 'output', '-' * 10)
                print(out)
    except exceptions.ParseError as e:
        error(e.message)
        return 3
    return 0


if __name__ == '__main__':
    # cmd(sys.argv[1:])
    cmd(['-l', 'lua', 'example/example.xlsx'])
    # cmd(['-h'])
