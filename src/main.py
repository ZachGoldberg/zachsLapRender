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

    parser.add_argument('-vd', '--video-directory', dest='videodir',
                        type=str,
                        help='Folder containing videos with timestamps synced to telemetry')

    parser.add_argument("-v", '--verbose', dest='info_verbose',
                        action='store_true',
                        help='Enable verbose logging')

    parser.add_argument("-vv", dest='debug_verbose',
                        action='store_true',
                        help='Enable even more verbose logging')

    parser.add_argument("-o", "--output-directory",
                        dest="outputdir", type=str,
                        help="Output directory for generated videos")

    parser.add_argument("-m", "--manual-offset",
                        dest="manual_offset", action='store_true',
                        help="Allow the user to manually select the time offset for each video file")
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
        logger.info("Parsing telemetry with %s" % parserClass)
        laps = parserClass.parse_data(args.datafile)
        logger.info("Found %s laps" % len(laps))

    if args.analyze_data:
        print_lap_stats(laps)
        sys.exit(0)

    videos = collect_videos(args.videodir, laps)

    if args.analyze_videos:
        print_video_stats(videos)
        sys.exit(0)

    if not videos:
        print "No Videos Found"
        sys.exit(1)

    if not laps:
        print "No usable laps found"
        sys.exit(1)


    matched_videos = []
    for video in videos:
        if video.matched_laps:
            matched_videos.append(video)

    if not matched_videos:
        print "No matching video/laps"
        sys.exit(1)


    if args.manual_offset:
        for video in matched_videos:
            video.calibrate_offset()


    # For now, just create a new .mp4 with each lap
    # we've discovered.
    # Then we'll write small bits to each of those, and build from there
    for video in matched_videos:
        video.render_laps(args.outputdir or "/tmp/")
