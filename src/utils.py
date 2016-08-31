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


"""
 Draws a rectangle with rounded corners, the parameters are the same as in the OpenCV function @see rectangle();
  @param cornerRadius A positive int value defining the radius of the round corners.
  @author K

 From http://stackoverflow.com/questions/18973103/how-to-draw-a-rounded-rectangle-rectangle-with-rounded-corners-with-opencv
"""
def rounded_rectangle(src, topLeft, bottomRight, lineColor, thickness, lineType, cornerRadius):
    # corners:
    # p1 - p2
    # |     |
    # p4 - p3

    p1 = topLeft
    p2 = (bottomRight[0], topLeft[1])
    p3 = bottomRight
    p4 = (topLeft[0], bottomRight[1])

    # draw straight lines
    cv2.line(src,
             (p1[0] + cornerRadius,p1[1]),
             (p2[0] - cornerRadius,p2[1]),
             lineColor, thickness, lineType);
    cv2.line(src,
             (p2[0], p2[1] + cornerRadius),
             (p3[0], p3[1] - cornerRadius),
             lineColor, thickness, lineType);
    cv2.line(src,
             (p4[0] + cornerRadius,p4[1]),
             (p3[0] - cornerRadius,p3[1]),
             lineColor, thickness, lineType);
    cv2.line(src,
             (p1[0], p1[1] + cornerRadius),
             (p4[0], p4[1] - cornerRadius),
             lineColor, thickness, lineType);

    # draw arcs
    cv2.ellipse(src,
                (p1[0] + cornerRadis, p1[1] + cornerRadius),
                Size( cornerRadius, cornerRadius ), 180.0, 0, 90, lineColor, thickness, lineType );

    #cv2.ellipse(src, p2 + Point(-cornerRadius, cornerRadius), Size( cornerRadius, cornerRadius ), 270.0, 0, 90, lineColor, thickness, lineType );
    #cv2.ellipse(src, p3+Point(-cornerRadius, -cornerRadius), Size( cornerRadius, cornerRadius ), 0.0, 0, 90, lineColor, thickness, lineType );
    #cv2.ellipse(src, p4+Point(cornerRadius, -cornerRadius), Size( cornerRadius, cornerRadius ), 90.0, 0, 90, lineColor, thickness, lineType );
