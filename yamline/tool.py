"""Command-line tool to run YAMLine.
Usage:

    $ python -m yamline.tool yamline_file [yamline_alias_file]
"""
import argparse
import traceback
from yamline import get_pipeline
from time import sleep
from multiprocessing import Pool

HEADER = '\033[35m'
OKBLUE = '\033[34m'
OKGREEN = '\033[32m'
WARNING = '\033[33m'
FAIL = '\033[31m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
BUNDERLINE = BOLD + UNDERLINE


# def _par(file_obj, alias=None):
#     if alias:
#         line = get_pipeline(file_obj, alias)
#     else:
#         line = get_pipeline(file_obj)
#     line.execute()


def _execute_failfast(yamlines, alias=None):
    for file_obj in yamlines:
        if alias:
            line = get_pipeline(file_obj, alias)
        else:
            line = get_pipeline(file_obj)
        line.execute()
        #
        # pool = Pool() if parallel else None
        # results = []
        #
        # for file_obj in yamlines:
        #     if pool:
        #         results.append(pool.apply_async(_par, (file_obj, alias)))
        #     else:
        #         if alias:
        #             line = get_pipeline(file_obj, alias)
        #         else:
        #             line = get_pipeline(file_obj)
        #         line.execute()
        #
        # pool.close()
        # pool.join()
        # return [result.get() for result in results]


def _execute_normal(yamlines, alias=None):
    execution_queue = []

    for file_obj in yamlines:
        if alias:
            line = get_pipeline(file_obj, alias)
        else:
            line = get_pipeline(file_obj)

        try:
            line.execute()
            execution_queue.append([file_obj, 'OK'])

        except Exception:
            print '\n' + WARNING + 'WHILE EXECUTING {} FOLLOWING EXCEPTION HAPPENED:\n'.format(
                file_obj.name) + ENDC
            traceback.print_exc()
            print '\n' + WARNING + 'END OF THE {} EXCEPTION TRACEBACK\n'.format(
                file_obj.name) + ENDC
            execution_queue.append([file_obj, 'FAILED'])

    return execution_queue


def parse_arguments():
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
                        help='If present then run yamlines in as '
                             'parallel processes')

    parser.add_argument('yamlines', type=argparse.FileType('r'), nargs='+')
    return parser.parse_args()


def main(arguments):
    failfast = arguments.failfast
    alias = arguments.alias
    yamlines = arguments.yamlines
    parallel = arguments.parallel

    if failfast:
        _execute_failfast(yamlines, alias=alias)
    else:
        results = _execute_normal(yamlines, alias=alias)
        print '\n'
        print BOLD + '=' * 30 + ' EXECUTION RESULTS ' + '=' * 30 + ENDC
        for execute_result in results:
            text_color = ''
            if execute_result[1] == 'OK':
                text_color = OKGREEN
            elif execute_result[1] == 'FAILED':
                text_color = FAIL
            print 'YAMLINE: {} - {}'.format(execute_result[0].name,
                                            text_color + execute_result[
                                                1] + ENDC)


if __name__ == '__main__':
    arguments = parse_arguments()
    main(arguments)
