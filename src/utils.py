import logging
import os
import subprocess
import tzlocal

from datetime import datetime
from dateutil import parser

logger = logging.getLogger(__name__)

def creation_time(filename):
    """
    From http://www.theeminentcodfish.com/gopro-timestamp/
    """
    cmnd = ['ffprobe', '-show_format', '-pretty', '-loglevel', 'quiet', filename]
    p = subprocess.Popen(cmnd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err =  p.communicate()
    if err:
        return None
    t = out.splitlines()

    # TODO ZG: This feels remarkably fragile...
    time = str(t[14][18:37])
    try:
        lz =  tzlocal.get_localzone()
        parsed = lz.localize(parser.parse(time))
        return parsed
    except:
        return None

def collect_videos(dirname, laps=None):
    if not laps:
        laps = []

    try:
        files = os.listdir(dirname)
    except:
        logging.error("Invalid video directory provided")
        return []

    videos = []
    for fname in files:
        logger.info("Inspecting %s..." % fname)

        from models import Video

        video = Video(os.path.join(dirname, fname))
        if video.is_valid():
            video.match_laps(laps)
            videos.append(video)
            logging.info("Found a video: %s" % video)
        else:
            logging.debug("%s is not a video" % video)


    return videos
