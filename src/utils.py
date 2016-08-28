import logging
import os


logger = logging.getLogger(__name__)


def collect_videos(dirname):
    files = os.listdir(dirname)

    for fname in files:
        logger.debug("Inspecting %s..." % fname)
