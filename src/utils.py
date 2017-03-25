import config
import logging
import os
import subprocess
import tempfile
import tzlocal
import wave
try:
    import moviepy.editor as mp
except:
    import traceback
    traceback.print_exc()
    import imageio
    imageio.plugins.ffmpeg.download()
from moviepy.video.io import ffmpeg_tools
from datetime import datetime
from dateutil import parser

from math import radians, cos, sin, asin, sqrt
from pydub import AudioSegment

logger = logging.getLogger(__name__)

CONFIG = None

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
    try:
        time = str(t[14][18:37])
        lz =  tzlocal.get_localzone()
        parsed = lz.localize(parser.parse(time))
        return parsed
    except:
        return None


def gopro_video_names_in_order(names1, names2):
    if (("GOPR" in names1[0] or "GP01" in names2[0]) and
        ("GOPR" in names2[0] or "GP01" in names2[0])):
        return names1[0][-6:-4] == names2[0][-6:-4]

    return False

def within_x_sec(sec, dt1, dt2):
    return abs((dt1 - dt2).total_seconds()) < sec



def merge_audio_and_video(videofname, audiofname, outputfile):
    logger.debug("Merging video and audio data...")
    ffmpeg_tools.ffmpeg_merge_video_audio(videofname, audiofname, outputfile)

    #cmd = "ffmpeg -y -i %s -i %s -c:v copy -c:a aac -strict experimental %s" % (
    #    videofname, audiofname, outputfile)
    #subprocess.call(cmd, shell=True)


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
            # Gopro splits up videos every 12 mins, so join them together as far as data
            # processing is concerned
            prev_video, new_video = video.find_video_predecessor(videos)

            if not prev_video:
                videos.append(video)
            else:
                if prev_video == video:
                    videos.remove(new_video)
                    videos.append(prev_video)
                    video = prev_video

            video.match_laps(laps)
            logging.info("Found a video: %s" % video)
        else:
            logging.debug("%s is not a video" % video)


    return videos

def mix_audiofiles(f1, f2, output):
    sound1 = AudioSegment.from_file(f1)
    sound2 = AudioSegment.from_file(f2)

    combined = sound1.overlay(sound2)

    combined.export(output, format='wav')

def combine_audio(sources, outfile):
    new_audio = wave.open(outfile, 'wb')
    old_audio = wave.open(sources[0], 'rb')

    new_audio.setnchannels(old_audio.getnchannels())
    new_audio.setsampwidth(old_audio.getsampwidth())
    new_audio.setframerate(old_audio.getframerate())

    old_audio.close()

    for source in sources:
        old_audio = wave.open(source, 'rb')
        new_audio.writeframes(old_audio.readframes(old_audio.getnframes()))
        old_audio.close()

    new_audio.close()


def extract_audio(source, newaudiofile, start_time, duration):
    tmpaudiofile = "%s.wav" % tempfile.NamedTemporaryFile().name

    clip = mp.VideoFileClip(source)
    clip.audio.write_audiofile(tmpaudiofile)

    #subprocess.call(
    #    "ffmpeg -y -i %s -ab 160k -ac 2 -ar 44100 -vn %s" % (source, tmpaudiofile),
    #    shell=True)

    old_audio = wave.open(tmpaudiofile, 'rb')
    new_audio = wave.open(newaudiofile, 'wb')


    framerate = old_audio.getframerate()
    start_frame = float(start_time * framerate)
    end_frame = start_frame + (duration * framerate)

    pos = start_time * framerate

    # A ghetto "seek"
    old_audio.readframes(int(pos))

    relaventframes = old_audio.readframes(int(end_frame - start_frame))

    new_audio.setnchannels(old_audio.getnchannels())
    new_audio.setsampwidth(old_audio.getsampwidth())
    new_audio.setframerate(framerate)
    new_audio.writeframes(relaventframes)

    new_audio.close()
    old_audio.close()
    os.unlink(tmpaudiofile)


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    http://stackoverflow.com/questions/15736995/how-can-i-quickly-estimate-the-distance-between-two-latitude-longitude-points
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = 6367 * c
    return km


def load_config():
    global CONFIG

    if CONFIG:
        return CONFIG

    path = os.path.join(os.path.expanduser("~"), ".zachslaprenderer.cfg")
    if not os.path.exists(path):
        open(path, 'w').close()
    CONFIG = config.Config(file(path))
    return CONFIG

def save_config(cfg):
    path = os.path.join(os.path.expanduser("~"), ".zachslaprenderer.cfg")
    cfg.save(open(path, 'w'))
