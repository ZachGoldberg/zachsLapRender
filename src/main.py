import argparse
import logging
import parsers
import sys
from picker import Picker


from models import Fix, Lap, Session, Day
from renderers import LikeHarrysRenderer
from utils import collect_videos
import youtube

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

    parser.add_argument("-t", "--trackname",
                        dest="trackname", type=str,
                        help="Trackname (for overlay)")

    parser.add_argument("-m", "--manual-offset",
                        dest="manual_offset", action='store_true',
                        help="Allow the user to manually select the time offset for each video file")

    parser.add_argument("-y", "--enable-youtube",
                        dest="youtube", action='store_true',
                        help="Upload all laps to youtube")

    parser.add_argument("-a", "--all-laps",
                        dest="all_laps", action='store_true',
                        help="Render all found laps (default is to allow user choice)")

    parser.add_argument("-c", "--lap-comparison",
                        dest="lap_comparison", action='store_true',
                        help="Render 2 laps one ontop of the other")

    parser.add_argument("-r", "--show-video-during-rendering",
                        dest="show_video", action='store_true',
                        help="Show the video during the rendering process.  Slows down rendering a little bit.")

    parser.add_argument("-b", "--bookend-time",
                        dest="bookend_time", type=int,
                        default=8,
                        help="Number of seconds to render before and after a lap (default: 8)")


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
        print "*" * 30
        print video
        for lap in video.matched_laps:
            print lap['lap']

def select_laps_to_render(videos, lap_comparison_mode=False):
    laps = {}
    for video in videos:
        for lap in video.matched_laps:
            print lap['lap']
            key = str(lap['lap'])
            laps[key] = lap
            lap["render"] = False

    keys = laps.keys()
    keys.sort()

    title = 'Select laps to render'
    if lap_comparison_mode:
        title = "Select at most 2 laps to render in side-by-side mode"

    opts = Picker(
        title = title,
        options = keys
    ).getSelected()

    if lap_comparison_mode:
        opts = opts[:2]

    for lap in opts:
        laps[lap]['render'] = True

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

    if args.trackname:
        for video in videos:
            video.trackname = args.trackname

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

    # Collect user's YouTube OAuth credentials before starting rendering process,
    # that way we can be finished with all user input and just run
    if args.youtube:
        youtube.get_authenticated_service()


    if not args.all_laps or args.lap_comparison:
        select_laps_to_render(matched_videos, args.lap_comparison)

    if args.manual_offset:
        for video in matched_videos:
            has_renderable_laps = False
            for lap in video.matched_laps:
                if lap.get('render'):
                    has_renderable_laps = True
                    break
            if has_renderable_laps:
                video.calibrate_offset()


    if args.lap_comparison:
        dual_vids = [v for v in matched_videos if v.renderable_laps()]
        if len(dual_vids) == 1:
            dual_vids.append(None)

        from renderers.dual import DualRenderer
        from renderers.likeharrys import LikeHarrysRenderer
        dr = DualRenderer(dual_vids[0], dual_vids[1], LikeHarrysRenderer)
        split_video = dr.render_laps(args.outputdir or "/tmp/",
                                     args.show_video,
                                     args.bookend_time)
        if args.youtube:
            video_id = youtube.upload_video(split_video)
            print "Upload Complete!  Visit at https://www.youtube.com/watch?v=%s" % video_id
    else:
        for video in matched_videos:
            renderer = LikeHarrysRenderer(video)
            lapvideos = renderer.render_laps(args.outputdir or "/tmp/",
                                             args.show_video,
                                             args.bookend_time)
            if args.youtube:
                for lapvideo in lapvideos:
                    video_id = youtube.upload_video(lapvideo)
                    print "Upload Complete!  Visit at https://www.youtube.com/watch?v=%s" % video_id
