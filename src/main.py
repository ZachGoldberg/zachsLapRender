import argparse
import sys
import parsers
from models import Fix, Lap, Session, Day

import argparse

def build_parser():

    parser = argparse.ArgumentParser(description='Process some integers.')

    parser.add_argument('--analyze',
                        dest='analyze', action='store_true',
                        help='Analyze and print info about input data, does not render video')

    parser.add_argument('--input-data-file', dest='datafile',
                        type=argparse.FileType('r'),
                        help='Input structured data file')

    return parser



if __name__ == '__main__':
    # Do things with argparse
    args = build_parser().parse_args()

    filedata = None
    if args.datafile:
        filedata = args.datafile.read()

    filename = args.datafile.name

    parserClass = parsers.find_parser(filename, filedata)
    data = parserClass.parse_data(filedata)
    print data
