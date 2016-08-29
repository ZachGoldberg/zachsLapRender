import cv2
import logging
import os
import pytz
import settings
import subprocess
import tzlocal
import wave

from dateutil import parser
from datetime import datetime, timedelta
from utils import creation_time

logger = logging.getLogger(__name__)

class Video(object):
    def __init__(self, filename):
        self.filename = filename
        self.filebase = os.path.basename(filename)
        self.file_start_date = None
        self.last_modified_at = None
        self.last_access_at = None
        self.created_at = None
        self.is_valid_video = False
        self.fps = None
        self.frame_count = None
        self.width = None
        self.height = None
        self.duration = None
        self.matched_laps = []
        self.frame_offset = 0

        self._calc_times()


    def _calc_times(self):
        # Open the file, find timestmps etc.
        res = os.stat(self.filename)
        self.last_modified_at = datetime.fromtimestamp(res.st_mtime)
        self.last_access_at = datetime.fromtimestamp(res.st_atime)
        self.created_at =  datetime.fromtimestamp(res.st_ctime)

        # Don't bother with obviously not video files
        _, ext = os.path.splitext(self.filename)
        if ext.lower() not in settings.VALID_VIDEO_EXTENSIONS:
            return

        cap = None
        # Verify that it's a valid video that cv2 can inspect,
        # record some video metadata whilst its open
        try:
            cap = cv2.VideoCapture(self.filename)
            self.fps = cap.get(cv2.cv.CV_CAP_PROP_FPS)
            self.frame_count = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))
            self.duration = timedelta(seconds=self.frame_count / self.fps)
            self.width  = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH))
            self.height = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))
            cap.release()
        except:
            return

        self.file_start_date = creation_time(self.filename)
        self.is_valid_video = True

    def render_laps(self, outputdir):
        for lapinfo in self.matched_laps:
            # Load up the old video
            oldcap = cv2.VideoCapture(self.filename)

            newfname = os.path.join(outputdir, "lap_%s_%s.noaudio.avi" % (
                lapinfo["lap"].lapnum,
                lapinfo["lap"].lap_time))

            final_newfname = os.path.join(outputdir, "lap_%s_%s.avi" % (
                lapinfo["lap"].lapnum,
                lapinfo["lap"].lap_time))

            logger.info("Rendering %s from %s..." % (newfname, self.filebase))

            # Include the frame offset from calibration
            start_frame = lapinfo['start_frame'] + self.frame_offset
            start_time = start_frame / self.fps
            end_frame = lapinfo['end_frame'] + self.frame_offset

            total_frames = end_frame - start_frame
            duration = total_frames / self.fps

            framenum = start_frame
            frames_writen = 0
            skipped = 0


            # Create a new videowriter file
            fourcc = cv2.cv.CV_FOURCC(*'MJPG')
            out = cv2.VideoWriter(newfname, fourcc, self.fps, (self.width, self.height))

            logger.debug("Seeking to lap start at %s..." % framenum)
            oldcap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, framenum)
            while(oldcap.isOpened()):
                framenum += 1
                ret, frame = oldcap.read()

                if framenum >= start_frame and framenum <= end_frame:
                    out.write(frame)
                    frames_writen += 1
                    if frames_writen % 20 == 0:
                        logger.debug("Written %s/%s frames..." % (frames_writen, total_frames))
                else:
                    skipped += 1
                    if skipped % 100 == 0:
                        logger.debug("Still seeking...")

                if framenum > end_frame:
                    break

            logger.debug("Buttoning up video...")
            oldcap.release()
            out.release()
            cv2.destroyAllWindows()

            logger.debug("Extracting audio...")
            audiofile = "/tmp/zachsaudio.wav"
            newaudiofile = "/tmp/zachaudioout.wav"
            subprocess.call(
                "ffmpeg -y -i %s -ab 160k -ac 2 -ar 44100 -vn %s" % (self.filename, audiofile),
                shell=True)

            old_audio = wave.open(audiofile, 'rb')
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

            logger.debug("Merging video and audio data...")
            cmd = "ffmpeg -y -i %s -i %s -c:v copy -c:a aac -strict experimental %s" % (
                    newfname, newaudiofile, final_newfname)

            subprocess.call(cmd, shell=True)

            logger.debug("Finished with %s" % final_newfname)



    def calibrate_offset(self):
        if not self.matched_laps:
            return

        cap = cv2.VideoCapture(self.filename)
        lapinfo = self.matched_laps[0]
        print "#" * 100
        print "# MANUAL OFFSET CALIBRATION "
        print "#" * 100
        print """In a moment a window will appear which shows the first frame of the lap.  This frame may be offset from the actual start of the lap due to the difference in the block on your laptimer and your camera.  Use the arrow keys to move forward and backwards by 1 frame, or page up and page down to move forward and backwards by ten seconds (300 frames).  Once you have the video at the first frame of the lap press enter."""
        print "\nVideo File: %s" % self.filename
        print "Video Start Time (Camera clock): %s" % self.start_time
        print "First Lap Start Time (Laptimer Clock): %s" % lapinfo['lap'].start_time
        print "First Frame of First Lap (calculated, assuming clocks are in sync): %s" % lapinfo['start_frame']
        print "First Lap Start in Video-time (calculated, assuming clocks are in sync): %s" % lapinfo['start_seconds']
        print "\nPress Enter to show the first frame and begin calibration for %s" % self.filebase

        go = raw_input()

        # Set initial frame to calculated start time
        start_framenum = lapinfo['start_frame']
        cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, start_framenum)

        end_calibration = False
        KEY_DELTA = {
            65361: -1,
            65363: 1,
            65365: 300,
            65366: -300
        }

        ENTER = 13

        framenum = start_framenum

        while(not end_calibration):
            print "Offset: %s" % (framenum - start_framenum)
            ret, frame = cap.read()

            if ret:
                cv2.imshow('frame', frame)
                keypress = cv2.waitKey(-1)
                if keypress == ENTER:
                    self.frame_offset = framenum - start_framenum
                    cap.release()
                    cv2.destroyAllWindows()
                    return
                else:
                    movement = KEY_DELTA.get(keypress, 0)
                    if movement == 1:
                        framenum += 1
                        continue

                    elif movement != 0:
                        framenum += movement
                        cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, framenum)


    def match_laps(self, laps):
        for lap in laps:
            self.match_lap(lap)

    def match_lap(self, lap):
        if self.start_time <= lap.start_time <= self.end_time:
            start_seconds = (lap.start_time - self.start_time).total_seconds()
            start_frame = int((start_seconds) * self.fps)

            """
            print "Lap Start: %s" %  lap.start_time
            print "Video Start: %s" % self.start_time
            print "Seconds into video: %s" % start_seconds
            print "Start Frame: %s" % start_frame
            """

            end_frame = start_frame + (lap.lap_time * self.fps)
            lap_info = {
                "lap": lap,
                "start_seconds": start_seconds,
                "start_frame": start_frame,
                "end_frame": end_frame
            }
            self.matched_laps.append(lap_info)

    def is_valid(self):
        return self.is_valid_video

    @property
    def start_time(self):
        if self.file_start_date:
            return self.file_start_date
        else:
            return self.created_at

    @property
    def end_time(self):
        if self.duration:
            return self.start_time + self.duration
        else:
            return None

    def __str__(self):
        return "%s (%sx%s) starting at %s / %s long with %s laps" % (
            os.path.basename(self.filename),
            self.width,
            self.height,
            self.start_time,
            self.duration,
            len(self.matched_laps)
        )

class Day(object):
    pass

class Session(object):
    pass

class Lap(object):
    def __init__(self, lapnum, fixes):
        self.lapnum = lapnum
        self.fixes = fixes
        self.date = None
        self._calc()

    def _calc(self):
        # find lap length
        max_time = 0
        end_time = 0
        start_time = 0
        min_time = 999999
        utc = ""
        if self.fixes and self.fixes[0].is_utc:
            utc = " UTC"

        for fix in self.fixes:

            if fix.lap_time <= min_time:
                min_time = fix.lap_time
                start_time = fix.wall_time
                self.date = parser.parse(fix.date)
            if fix.lap_time > max_time:
                max_time = fix.lap_time
                end_time = fix.wall_time


        self.lap_time = max_time
        self.start_time = parser.parse("%s %s %s" % (fix.date, start_time, utc))
        self.end_time = parser.parse("%s %s %s" % (fix.date, end_time, utc))

        if utc:
            self.start_time = self.start_time.astimezone(tzlocal.get_localzone())
            self.end_time = self.end_time.astimezone(tzlocal.get_localzone())


    def details(self):
        return "Lap Length: %s\nLap Start: %s\nLap End: %s" % (self.lap_time,
                                                               self.start_time,
                                                               self.end_time)

    def __str__(self):
        return "Lap %s, %s fixes" % (self.lapnum, len(self.fixes))


class Fix(object):
    FIX_ID = "fix_id"
    FUEL = "fuel"
    ALT_FT = "alt_ft"
    ACCEL_SOURCE = "accel_source"
    HDOP = "hdop"
    ODB_KPH = "odb_kph"
    LAP_TIME = "lap_time"
    MAF = "maf"
    LONG = "long"
    ACCURACY = "accuracy"
    SATELITES = "satelites"
    ALT_M = "alt_m"
    LIN_G = "lin_g"
    DATE = "date"
    LEAN = "lean"
    IAT_C = "iat_c"
    DISTANCE_MI = "distance_mi"
    GEAR = "gear"
    MAP = "map"
    OIL_C = "oil_c"
    THROTTLE = "throttle"
    SPEED_MPH = "speed_mph"
    LAP_INDEX = "lap_index"
    HEADING_DEG = "heading_deg"
    COOLANT_C = "coolant_c"
    GPS_FIX_TYPE = "gps_fix_type"
    LAT_G = "lat_g"
    GPS_DIFF = "gps_diff"
    DISTANCE_KM = "distance_km"
    ODB_MPH = "odb_mph"
    WALL_TIME = "wall_time"
    LAT = "lat"
    RPM = "rpm"
    SPEED_KPH = "speed_kph"
    ATTRS = [FIX_ID, FUEL, ALT_FT, ACCEL_SOURCE, HDOP, ODB_KPH, LAP_TIME, MAF, LONG,
             ACCURACY, SATELITES, ALT_M, LIN_G, DATE, LEAN, IAT_C, DISTANCE_MI, GEAR, MAP,
             OIL_C, THROTTLE, SPEED_MPH, LAP_INDEX, HEADING_DEG, COOLANT_C, GPS_FIX_TYPE, LAT_G,
             GPS_DIFF, DISTANCE_KM, ODB_MPH, WALL_TIME, LAT, RPM, SPEED_KPH]

    DATETIME_ATTRS = [WALL_TIME]

    def __init__(self, is_utc=False):
        self.is_utc = is_utc


    def setattr(self, attr, val):
        if attr not in self.ATTRS:
            raise Exception("Invalid Attr")

        try:
            val = float(val)
        except:
            pass

        setattr(self, attr, val)

    def __str__(self):
        return "Fix %s Lap %s @%s %s:%s" % (self.fix_id,
                                             self.lap_index,
                                             self.lap_time,
                                             self.lat,
                                             self.long)
