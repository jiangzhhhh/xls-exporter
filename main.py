# -*- coding: utf-8 -*-
import os
import sys
import importlib
import pkgutil
import argparse
import codecs
from exporter import xls_exporter
from exporter.formatter import LangFormatter
from exporter import exceptions
from exporter import lang as support_langs


def error(msg: str) -> None:
    sys.stderr.write(msg + '\n')


def support_output_langs():
    lang_pkg = importlib.import_module('exporter.lang')
    langs = []
    for (_, name, _) in pkgutil.iter_modules(lang_pkg.__path__):
        langs.append(name)
    return langs


def cmd(argv):
    lang_help = 'support langs:' + ' '.join(support_output_langs())
    parser = argparse.ArgumentParser(description='welcome to use xls-exporter')
    parser.add_argument('input-file', type=str, help='input file', metavar='<input file>')
    parser.add_argument('-l', type=str, required=True, help=lang_help, metavar='<output lang>', dest='output-lang')
    parser.add_argument('-o', type=argparse.FileType('w', encoding='utf8'), required=False, help='output file',
                        metavar='<output file>', default=sys.stdout, dest='output-file')
    parser.add_argument('--check', action='store_true', required=False, help='only check', dest='only-check')
    args = parser.parse_args(argv)
    opts = vars(args)

    input_file = opts['input-file']
    lang = opts['output-lang']
    output_file = opts['output-file']
    only_check = opts['only-check']

    try:
        module = importlib.import_module('exporter.lang.%s' % lang)
        formatter = module.__dict__.get('Formatter')
        if not formatter:
            error('%s is not supported' % lang)
            return 2
    except ModuleNotFoundError:
        parser.print_help(sys.stderr)
        return 2

    try:
        value_tree = xls_exporter.parse(input_file, verbose=True)
        if not only_check:
            out = value_tree.tostring(formatter=formatter())
            output_file.write(out)
    except exceptions.ParseError as e:
        error(e.message)
        return 3
    return 0


if __name__ == '__main__':
    # cmd(sys.argv[1:])
    cmd('example/example.xlsx -l cpp'.split())
