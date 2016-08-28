import argparse
import logging
import parsers
import sys

from models import Fix, Lap, Session, Day
from utils import collect_videos

import argparse

logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s %(levelname)s %(message)s')

logger = logging.getLogger(__name__)


def build_parser():

    parser = argparse.ArgumentParser(description='Process some integers.')

    parser.add_argument('--analyze-data',
                        dest='analyze_data', action='store_true',
                        help='Analyze and print info about input data, does not render video')

    parser.add_argument(
        '--analyze-videos',
        dest='analyze_videos', action='store_true',
        help='Analyze and print info about videos found in video-directory, does not render video')

    parser.add_argument('--input-data-file', dest='datafile',
                        type=argparse.FileType('r'),
                        help='Input structured data telemetry file')

    parser.add_argument('--video-directory', dest='videodir',
                        type=str,
                        help='Folder containing videos with timestamps synced to telemetry')

    parser.add_argument("-v", '--verbose', dest='info_verbose',
                        action='store_true',
                        help='Input structured data telemetry file')

    parser.add_argument("-vv", dest='debug_verbose',
                        action='store_true',
                        help='Input structured data telemetry file')

    return parser


def print_lap_stats(laps):
    print "Number of Laps in Input File: %s" % len(laps)
    print "Total GPS Fix Points: %s" % (sum([len(lap.fixes) for lap in laps]))
    for lap in laps:
        print lap
        print lap.details()
        print "-" * 30


def print_video_stats(videos):
    for video in videos:
        print video


if __name__ == '__main__':
    # Do things with argparse
    args = build_parser().parse_args()

    if args.info_verbose:
        logging.getLogger().setLevel(logging.INFO)

    if args.debug_verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    laps = None
    if args.datafile:
        filename = args.datafile.name
        parserClass = parsers.find_parser(filename)
        laps = parserClass.parse_data(args.datafile)

    if args.analyze_data:
        print_lap_stats(laps)
        sys.exit(0)

    videos = collect_videos(args.videodir)

    if args.analyze_videos:
        print_video_stats(videos)
