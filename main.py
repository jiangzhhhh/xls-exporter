# -*- coding: utf-8 -*-
import sys
import argparse
from exporter import xls_exporter
from exporter import exceptions
from exporter.lang import lua
from exporter.lang import json
from exporter.lang import python


def error(msg: str) -> None:
    sys.stderr.write(msg + '\n')


def support_output_langs():
    dict = {}
    for m in [lua, json, python]:
        name = m.__name__.split('.')[-1]
        dict[name] = m
    return dict


def cmd(argv):
    langs = support_output_langs()
    lang_help = 'support langs:' + ' '.join([k for k in langs])
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

    formatter = None
    try:
        module = langs.get(lang, None)
        if module:
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
            output_file.write(out)
    except exceptions.ParseError as e:
        error(e.message)
        return 3
    return 0


if __name__ == '__main__':
    cmd(sys.argv[1:])
    # cmd('example/example.xlsx -l cpp'.split())
