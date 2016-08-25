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


def print_stats(laps):
    print "Number of Laps in Input File: %s" % len(laps)
    print "Total GPS Fix Points: %s" % (sum([len(lap.fixes) for lap in laps]))
    for lap in laps:
        print lap
        print lap.details()
        print "-" * 30

if __name__ == '__main__':
    # Do things with argparse
    args = build_parser().parse_args()

    filename = args.datafile.name

    parserClass = parsers.find_parser(filename)
    laps = parserClass.parse_data(args.datafile)

    if args.analyze:
        print_stats(laps)
        sys.exit(0)
