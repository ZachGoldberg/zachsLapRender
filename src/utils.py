import logging
import os

from models import Video

logger = logging.getLogger(__name__)


def collect_videos(dirname):
    try:
        files = os.listdir(dirname)
    except:
        logging.error("Invalid video directory provided")
        return []

    videos = []
    for fname in files:
        logger.info("Inspecting %s..." % fname)
        video = Video(os.path.join(dirname, fname))
        if video.is_valid():
            videos.append(video)
            logging.info("Found a video: %s" % video)
        else:
            logging.debug("%s is not a video" % video)


    return videos
