"""Command-line tool to run YAMLine.
Usage:

    $ python -m yamline.tool yamline_file [yamline_alias_file]
"""
from __future__ import absolute_import, print_function

import warnings
import argparse
import traceback

from const import OKGREEN, WARNING, FAIL, ENDC, BOLD
from yamline import get_pipeline


def _execute_failfast(yamlines, alias=None):
    for file_obj in yamlines:
        if alias:
            line = get_pipeline(file_obj, alias)
        else:
            line = get_pipeline(file_obj)
        line.execute()


def _execute_skip_fail(yamlines, alias=None):
    execution_queue = []

    for file_obj in yamlines:
        if alias:
            line = get_pipeline(file_obj, alias)
        else:
            line = get_pipeline(file_obj)

        try:
            line.execute()
            execution_queue.append([file_obj, 'OK'])

        except Exception as e:
            msg = 'WHILE EXECUTING {} FOLLOWING EXCEPTION HAPPENED:\n'
            print('\n' + WARNING + msg.format(file_obj.name) + ENDC)
            traceback.print_exc()
            msg = 'END OF THE {} EXCEPTION TRACEBACK\n'
            print('\n' + WARNING + msg.format(file_obj.name) + ENDC)
            print(e)
            execution_queue.append([file_obj, 'FAILED'])

    return execution_queue


def _parse_cmd_args():
    parser = argparse.ArgumentParser(description='Process files as yamlines')
    parser.add_argument('-f', '--failfast',
                        action='store_true',
                        default=False,
                        help='If this flag is set and any of yamlines raised'
                             ' exception then whole process will fail.')

    parser.add_argument('-a', '--alias',
                        action='store',
                        default='',
                        help='To clarify yamlines meaning you may provide a '
                             'yaml file with aliases to all yamline literals')

    parser.add_argument('-p', '--parallel',
                        action='store_true',
                        default=False,
                        help='[NOT SUPPORTED JET] If present then run yamlines'
                             ' in as parallel processes')

    parser.add_argument('yamlines', type=argparse.FileType('r'), nargs='+')
    return parser.parse_args()


def main(arguments):
    failfast = arguments.failfast
    alias = arguments.alias
    yamlines = arguments.yamlines
    parallel = arguments.parallel

    if parallel:
        warnings.warn('Parallel mode is not supported jet!', RuntimeWarning)

    if failfast:
        _execute_failfast(yamlines, alias=alias)
    else:
        results = _execute_skip_fail(yamlines, alias=alias)
        print('\n')
        print(BOLD + '=' * 30 + ' EXECUTION RESULTS ' + '=' * 30 + ENDC)
        for execute_result in results:
            text_color = ''
            if execute_result[1] == 'OK':
                text_color = OKGREEN
            elif execute_result[1] == 'FAILED':
                text_color = FAIL
            print('YAMLINE: {} - {}'.format(execute_result[0].name,
                                            text_color + execute_result[
                                                1] + ENDC))


if __name__ == '__main__':
    arguments = _parse_cmd_args()
    main(arguments)
