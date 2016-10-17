import logging
import os
import subprocess
import tzlocal
import wave
from pydub import AudioSegment


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


def gopro_video_names_in_order(names1, names2):
    if (("GOPR" in names1[0] or "GP01" in names2[0]) and
        ("GOPR" in names2[0] or "GP01" in names2[0])):
        return names1[0][-6:-4] == names2[0][-6:-4]

    return False

def within_x_sec(sec, dt1, dt2):
    return abs((dt1 - dt2).total_seconds()) < sec


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

def extract_audio(source, newaudiofile, start_time, duration):
    tmpaudiofile = "/tmp/zachsaudio.wav"
    subprocess.call(
        "ffmpeg -y -i %s -ab 160k -ac 2 -ar 44100 -vn %s" % (source, tmpaudiofile),
        shell=True)

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
