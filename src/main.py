import argparse
import logging
import parsers
import os
import sys
from gooey import Gooey, GooeyParser
from picker import Picker
from threading import Thread

from models import Fix, Lap, Session, Day
from renderers import LikeHarrysRenderer
from utils import collect_videos, load_config, save_config
import youtube

import argparse

logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s %(levelname)s %(message)s')

logger = logging.getLogger(__name__)

# Setup unbuffered stdout for packaging purposes
nonbuffered_stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
sys.stdout = nonbuffered_stdout

# Args we want to cache between invocations
SAVEABLE_ARGS = ["datafile_dir", "videodir",
                "recursive", "outputdir", "trackname",
                "bookend_time"]

@Gooey
def build_parser_gui():
    return build_parser()

def build_parser():
    parser = GooeyParser(description='Render really cool racing videos with telemetry overlays')

    parser.add_argument('--analyze-data',
                        dest='analyze_data', action='store_true',
                        help='Analyze and print info about input data, does not render video')

    parser.add_argument(
        '--analyze-videos',
        dest='analyze_videos', action='store_true',
        help='Analyze and print info about videos found in video-directory, does not render video')

    parser.add_argument('--input-data-file', dest='datafile',
                        type=str,
                        widget="FileChooser",
                        help='Input structured data telemetry file')

    parser.add_argument('--input-data-file-directory', dest='datafile_dir',
                        type=str,
                        widget="DirChooser",
                        help='Folder containing Input structured data telemetry file')

    parser.add_argument('-vd', '--video-directory', dest='videodir',
                        type=str,
                        widget="DirChooser",
                        help='Folder containing videos with timestamps synced to telemetry')

    parser.add_argument('--recursive', dest='recursive',
                        action='store_true',
                        help='Search for videos recursively')

    parser.add_argument("-v", '--verbose', dest='info_verbose',
                        action='store_true',
                        help='Enable verbose logging')

    parser.add_argument("-vv", dest='debug_verbose',
                        action='store_true',
                        help='Enable even more verbose logging')

    parser.add_argument("-o", "--output-directory",
                        dest="outputdir", type=str,
                        widget="DirChooser",
                        help="Output directory for generated videos")

    parser.add_argument("-t", "--trackname",
                        dest="trackname", type=str,
                        help="Trackname (for overlay)")

    parser.add_argument("-m", "--no-manual-offset",
                        dest="manual_offset", action='store_false',
                        help="Disable the manual offset calibration feature.  Manual calibration will only happen once per video.")

    parser.add_argument("-fm", "--force-manual-offset",
                        dest="force_manual_offset", action='store_true',
                        help="Force display of the manual offset calibration feature. To be used if stored offset is innaccurate.")

    parser.add_argument("-y", "--enable-youtube",
                        dest="youtube", action='store_true',
                        help="Upload all laps to youtube")

    parser.add_argument("-a", "--all-laps",
                        dest="all_laps", action='store_true',
                        help="Render all found laps (or sessions with -s) (default is to allow user choice)")

    parser.add_argument("-s", "--render-sessions",
                        dest="render_sessions", action='store_true',
                        help="Render one video per session (i.e. per input video)")

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


def select_sessions_to_render(videos):
    s_videos = {}
    for video in videos:
        key = str(video)
        s_videos[key] = video
        for lap in video.matched_laps:
            lap["render"] = False

    keys = s_videos.keys()
    keys.sort()

    title = 'Select sessions to render'

    picker = Picker(
        title = title,
        options = keys
    )
    picker.window_width = 150
    picker.window_height = 30
    picker.start()
    opts = picker.getSelected()

    for videoname in opts:
        video = s_videos[videoname]
        for lap in video.matched_laps:
            lap['render'] = True



def select_laps_to_render(videos, lap_comparison_mode=False,
                          select_sessions=False):
    if select_sessions:
        return select_sessions_to_render(videos)

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

    picker = Picker(
        title = title,
        options = keys
    )
    picker.start()
    opts = picker.getSelected()

    if lap_comparison_mode:
        opts = opts[:2]

    for lap in opts:
        laps[lap]['render'] = True


def generate_metadata(videofile, params, renderer, args):
    return renderer.generate_metadata(args, params)


def get_laps(filename):
    parserClass = parsers.find_parser(filename)

    logger.info("Parsing telemetry from %s with %s" % (filename, parserClass))
    laps = parserClass.parse_data(open(filename), filename=filename)
    logger.info("Found %s laps" % len(laps))
    return laps

def update_cfg(cfg, args):
    arg_cfg = {}
    try:
        arg_cfg = cfg.args
    except:
        pass

    for arg in SAVEABLE_ARGS:
        new_val = getattr(args, arg)
        old_val = arg_cfg.get(arg)
        if new_val:
            arg_cfg[arg] = new_val
        elif old_val:
            setattr(args, arg, old_val)

    cfg.args = arg_cfg
    save_config(cfg)
    return cfg, args

if __name__ == '__main__':
    # Do things with argparse
    if len(sys.argv) > 1:
        args = build_parser().parse_args()
    else:
        args = build_parser_gui().parse_args()

    cfg = load_config()
    cfg, args = update_cfg(cfg, args)

    if args.info_verbose:
        logging.getLogger().setLevel(logging.INFO)

    if args.debug_verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    laps = []
    if args.datafile:
        filename = args.datafile
        filename = "Log-20161120-101406 Big Willow - 1.48.516.csv"
        laps = get_laps(filename)

    #if args.datafile_dir:
    #    files = os.listdir(args.datafile_dir)
    #    for datafile in files:
    #        laps.extend(get_laps(os.path.join(args.datafile_dir, datafile)))

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

    try:
        offsets = cfg.offsets
    except:
        offsets = {}
        cfg.offsets = {}

    for video in matched_videos:
        video.frame_offset = offsets.get(video.filenames[0], 0) or 0

    if not matched_videos:
        print "No matching video/laps"
        sys.exit(1)

    # Collect user's YouTube OAuth credentials before starting rendering process,
    # that way we can be finished with all user input and just run
    if args.youtube:
        youtube.get_authenticated_service()

    if not args.all_laps or args.lap_comparison:
        select_laps_to_render(matched_videos, args.lap_comparison, args.render_sessions)

    if args.manual_offset or args.force_manual_offset:
        for video in matched_videos:
            has_renderable_laps = False
            for lap in video.matched_laps:
                if lap.get('render'):
                    has_renderable_laps = True
                    break
            if has_renderable_laps and (
                    offsets.get(video.filenames[0]) is None or args.force_manual_offset):
                offset = video.calibrate_offset()
                offsets[video.filenames[0]] = offset
                cfg.offsets = offsets
                save_config(cfg)

    def upload(lapvideo, params, renderer, args):
        print "Uploading %s to youtube..." % lapvideo
        md = generate_metadata(lapvideo, params, renderer, args)

        video_id = youtube.upload_video(lapvideo, md)
        print "Upload Complete!  Visit at https://www.youtube.com/watch?v=%s" % video_id

    if args.lap_comparison:
        dual_vids = [v for v in matched_videos if v.renderable_laps()]
        if len(dual_vids) == 1:
            dual_vids.append(None)

        from renderers.dual import DualRenderer
        from renderers.likeharrys import LikeHarrysRenderer
        dr = DualRenderer(dual_vids[0], dual_vids[1], LikeHarrysRenderer)
        for (lapvideo, params) in dr.render_laps(args.outputdir or "/tmp/",
                                    args.show_video,
                                    args.bookend_time,
                                    render_laps_uniquely=False):
            if args.youtube:
                Thread(target=upload, args=(lapvideo, params, dr, args)).start()
    else:
        for video in matched_videos:
            renderer = LikeHarrysRenderer(video)
            for (lapvideo, params) in renderer.render_laps(args.outputdir or "/tmp/",
                                                 args.show_video,
                                                 args.bookend_time,
                                                 render_laps_uniquely=(not args.render_sessions)):
                if args.youtube:
                    Thread(target=upload, args=(lapvideo, params, renderer, args)).start()
