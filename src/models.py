import cv2
import logging
import math
import os
import pytz
import settings
import subprocess
import tzlocal
import wave

from dateutil import parser
from datetime import datetime, timedelta
from utils import creation_time, within_x_sec, gopro_video_names_in_order, extract_audio

from renderers.basic import BasicRenderer
from renderers.likeharrys import LikeHarrysRenderer

logger = logging.getLogger(__name__)

speed_func = lambda x: x.speed_mph

class Video(object):
    def __init__(self, filename):
        self.filenames = [filename]
        self.filebase = os.path.basename(filename[0])
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
        self.frame_offset = -28
        self.renderer = LikeHarrysRenderer(self)
        self._calc_times()

    def file_basenames(self):
        return ",".join([os.path.basename(fn) for fn in self.filenames])

    def find_video_predecessor(self, videos):
        for video in videos:
            if (within_x_sec(3, self.end_time, video.start_time) or
                within_x_sec(3, self.start_time, video.end_time) or
                gopro_video_names_in_order(self.filenames, video.filenames)
            ):
                # Figure out which has earliest start, append all videos from newer one,
                # resort filenames by start time / filename, redo all internal calculations
                old = self
                new = video
                if self.start_time > video.start_time:
                    old = video
                    new = self

                logger.debug("Merging %s and %s" % (old.file_basenames(), new.file_basenames()))
                # TODO: Use basenames when sorting?
                old.filenames.extend(new.filenames)
                old.filenames.sort()
                old._calc_times()
                return old, new

        return None, None


    def sort_filenames(self):
        pass

    def _calc_times(self):
        # Open the file, find timestmps etc.
        res = os.stat(self.filenames[0])
        self.last_modified_at = datetime.fromtimestamp(res.st_mtime)
        self.last_access_at = datetime.fromtimestamp(res.st_atime)
        self.created_at =  datetime.fromtimestamp(res.st_ctime)

        # Don't bother with obviously not video files
        _, ext = os.path.splitext(self.filenames[0])
        if ext.lower() not in settings.VALID_VIDEO_EXTENSIONS:
            return

        cap = None
        # Verify that it's a valid video that cv2 can inspect,
        # record some video metadata whilst its open
        try:
            cap = cv2.VideoCapture(self.filenames[0])
            self.fps = cap.get(cv2.cv.CV_CAP_PROP_FPS)
            self.frame_count = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))
            self.duration = timedelta(seconds=self.frame_count / self.fps)
            self.width  = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH))
            self.height = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))
            cap.release()

            if len(self.filenames) > 1:
                for filename in self.filenames[1:]:
                    cap = cv2.VideoCapture(filename)
                    fps = cap.get(cv2.cv.CV_CAP_PROP_FPS)
                    frame_count = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))
                    self.duration += timedelta(seconds=frame_count / fps)
                    cap.release()

        except:
            return

        self.file_start_date = creation_time(self.filenames[0])
        self.is_valid_video = True


    def render_frame(self, frame, start_frame, framenum, lap):
        return self.renderer.render_frame(frame, start_frame, framenum, lap)

    def next_sync_event(self, frames_in):
        seconds_in = frames_in / self.fps

        print "-" * 50
        for lapinfo in self.matched_laps:
            lap = lapinfo['lap']
            lap_seconds_in = seconds_in - lapinfo['start_seconds']
            print "Lap Start: %s, seconds in: %s" % (lapinfo['start_seconds'], seconds_in)
            print "Lap Seconds In: %s" % lap_seconds_in
            if lap_seconds_in < -1 or frames_in > lapinfo['end_frame']:
                continue

            speedinfo = lap.get_nearest_speed_direction_change(
                lap_seconds_in, True) or {}

            brakeinfo = lap.get_nearest_lin_g_direction_change(lap_seconds_in, True) or {}
            cornerinfo = lap.get_nearest_lat_g_direction_change(lap_seconds_in, True) or {}

            lowest_time = min([speedinfo.get('seconds'), brakeinfo.get('seconds'), cornerinfo.get('seconds')])
            print lapinfo
            print speedinfo, brakeinfo, cornerinfo
            print lowest_time
            new_frame = lapinfo['start_frame'] + math.ceil(lowest_time * self.fps)

            print "Returning %s" % new_frame
            if abs(new_frame - frames_in) == 0:
                return new_frame + 1

            return new_frame

        return frames_in

    def prev_sync_event(self, frames_in):
        seconds_in = frames_in / self.fps
        print "-" * 50


        for lapinfo in self.matched_laps:
            lap = lapinfo['lap']
            lap_seconds_in = seconds_in - lapinfo['start_seconds']
            print "Lap Start: %s, seconds in: %s" % (lapinfo['start_seconds'], seconds_in)
            print lap_seconds_in
            if lap_seconds_in < -1 or frames_in > lapinfo['end_frame']:
                continue

            speedinfo = lap.get_nearest_speed_direction_change(
                lap_seconds_in) or {}

            brakeinfo = lap.get_nearest_lin_g_direction_change(lap_seconds_in) or {}
            cornerinfo = lap.get_nearest_lat_g_direction_change(lap_seconds_in) or {}

            highest_time = max([speedinfo.get('seconds'), brakeinfo.get('seconds'), cornerinfo.get('seconds')])
            print lapinfo
            print seconds_in
            print lap_seconds_in
            print speedinfo, brakeinfo, cornerinfo
            print highest_time
            return lapinfo['start_frame'] + int(highest_time * self.fps)

        return frames_in

    def renderable_laps(self):
        return [m for m in self.matched_laps if m['render']]

    def render_laps(self, outputdir):
        lapvideos = []

        for lapinfo in self.matched_laps:
            if not lapinfo.get("render", True):
                logger.debug("Skipping lap %s due to render=false" % lapinfo['lap'])
                continue

            # Load up the old video
            oldcap = cv2.VideoCapture(self.filenames[0])

            newfname = os.path.join(outputdir, "lap_%s_%s.noaudio.avi" % (
                lapinfo["lap"].lapnum,
                lapinfo["lap"].lap_time))

            final_newfname = os.path.join(outputdir, "lap_%s_%s.avi" % (
                lapinfo["lap"].lapnum,
                lapinfo["lap"].lap_time))

            lapvideos.append(final_newfname)

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
            fourcc = cv2.cv.CV_FOURCC(*'XVID')
            out = cv2.VideoWriter(newfname, fourcc, self.fps, (self.width, self.height))

            logger.debug("Seeking to lap start at %s ..." % framenum)
            oldcap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, framenum)
            while(oldcap.isOpened()):
                framenum += 1
                ret, frame = oldcap.read()

                if framenum >= start_frame and framenum <= end_frame:
                    rendered_frame = self.render_frame(frame, start_frame, framenum, lapinfo["lap"])
                    out.write(rendered_frame)
                    cv2.imshow('frame', rendered_frame)
                    keypress = cv2.waitKey(1)

                    frames_writen += 1
                    if frames_writen % 30 == 0:
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
            newaudiofile = "/tmp/zachaudioout.wav"
            extract_audio(self.filenames[0], newaudiofile, start_time, duration)

            logger.debug("Merging video and audio data...")
            cmd = "ffmpeg -y -i %s -i %s -c:v copy -c:a aac -strict experimental %s" % (
                    newfname, newaudiofile, final_newfname)

            subprocess.call(cmd, shell=True)

            logger.debug("Finished with %s" % final_newfname)


        return lapvideos


    def find_lap_by_framenum(self, framenum):
        if not self.matched_laps:
            return None

        for lap in self.matched_laps:
            if lap['start_frame'] <= framenum <= lap['end_frame']:
                return lap

        return None


    def calibrate_offset(self):
        if not self.matched_laps:
            return

        cap = cv2.VideoCapture(self.filenames[0])
        lapinfo = self.matched_laps[0]
        print "#" * 100
        print "# MANUAL OFFSET CALIBRATION "
        print "#" * 100
        print """In a moment a window will appear which shows the first frame of the lap.  This frame may be offset from the actual start of the lap due to the difference in the block on your laptimer and your camera."""
        print "\nUse the arrow keys to move the video forward and backwards by 1 frame, or page up and page down to move forward and backwards by ten seconds (300 frames)."
        print "\nHold shift and the arrow keys or page up and page down to move the video sync by the appropriate amount."
        print "\nPress space to start and stop playback and test the video sync"
        print "\nPress Enter when finished syncing\n"
        print "\nVideo File: %s" % self.filenames[0]
        print "Video Start Time (Camera clock): %s" % self.start_time
        print "First Lap Start Time (Laptimer Clock): %s" % lapinfo['lap'].start_time
        print "First Frame of First Lap (calculated, assuming clocks are in sync): %s" % lapinfo['start_frame']
        print "First Lap Start in Video-time (calculated, assuming clocks are in sync): %s" % lapinfo['start_seconds']

        # Set initial frame to calculated start time
        start_framenum = lapinfo['start_frame']
        cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, start_framenum)

        end_calibration = False
        UP_KEY = 65362
        RIGHT_KEY = 65363
        DOWN_KEY = 65364
        LEFT_KEY = 65361
        KEY_DELTA = {
            LEFT_KEY: -1,
            RIGHT_KEY: 1,
            65365: 300,
            65366: -300
        }

        ENTER = 13
        SPACE = 32
        W_KEY = 119
        Q_KEY = 113
        offset = -28
        framenum = start_framenum + offset
        playing = False
        while(not end_calibration):
            print "Current Frame: %s, sync offset: %s" % (framenum, offset)

            ret, frame = cap.read()

            if ret:
                # Find which lap we're in based on framenum
                lapinfo = self.find_lap_by_framenum(framenum + offset) or self.matched_laps[0]

                lap_start_framenum = lapinfo['start_frame'] + offset
                frame = self.render_frame(frame, lap_start_framenum, framenum, lapinfo['lap'])
                cv2.imshow('frame', frame)
                if playing:
                    wait = 1
                else:
                    wait = -1

                keypress = cv2.waitKey(wait)
                movement = 0
                print "Keypress: %s" % keypress
                if keypress == -1:
                    framenum += 1
                elif keypress == ENTER:
                    self.frame_offset = offset
                    cap.release()
                    cv2.destroyAllWindows()
                    return
                # Experimental features that aren't quite finished and might crash:
                #elif keypress == W_KEY:
                #    movement = self.next_sync_event(framenum) - framenum
                #elif keypress == Q_KEY:
                #    movement = self.prev_sync_event(framenum) - framenum
                elif keypress == SPACE:
                    playing = not playing
                elif keypress == UP_KEY:
                    offset += 1
                    framenum += 1
                    cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, framenum)
                elif keypress == DOWN_KEY:
                    offset -= 1
                    framenum -= 1
                    cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, framenum)
                else:
                    movement = KEY_DELTA.get(keypress, 0)

                print "Moving offset: %s, movemnet: %s" % (offset, movement)

                if movement == 1:
                    # Don't actually seek to get the next frame since seeking is expensive
                    framenum += 1
                    continue

                elif movement != 0:
                    print "Jumping by %s frames..." % movement
                    framenum += movement
                    cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, framenum)


    def match_laps(self, laps):
        self.matched_laps = []

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
                "render": True,
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
            self.file_basenames(),
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
        self.speed_markers = []
        self.lat_g_markers = []
        self.lin_g_markers = []
        self._calc()


    def get_gps_bounds(self):
        min_lat = 999
        min_long = 999

        max_lat = -999
        max_long = -999
        for fix in self.fixes:
            if fix.lat < min_lat:
                min_lat = fix.lat

            if fix.lat > max_lat:
                max_lat = fix.lat

            if fix.long < min_long:
                min_long = fix.long

            if fix.long > max_long:
                max_long = fix.long

        return (min_lat, max_lat, min_long, max_long)


    def get_mph_at_time(self, seconds):
        return self.get_metric_at_time(lambda x: x.speed_mph, seconds)

    def get_lat_g_at_time(self, seconds):
        return self.get_metric_at_time(lambda x: x.lat_g, seconds)

    def get_lin_g_at_time(self, seconds):
        return self.get_metric_at_time(lambda x: x.lin_g, seconds)

    def get_gps_at_time(self, seconds):
        return (self.get_metric_at_time(lambda x: x.lat, seconds),
                self.get_metric_at_time(lambda x: x.long, seconds))

    def get_metric_at_time(self, metric, seconds):
        # This timestamp should be inbetween two fixes
        # Find which two, then "interpolate" MPH between them

        if seconds < self.fixes[0].lap_time:
            return metric(self.fixes[0])

        for i in xrange(len(self.fixes)):
            if i + 1 >= len(self.fixes):
                break
            this_fix = self.fixes[i]
            next_fix = self.fixes[i+1]

            if this_fix.lap_time <= seconds and next_fix.lap_time >= seconds:
                total_delta = next_fix.lap_time - this_fix.lap_time
                this_delta = seconds - this_fix.lap_time
                percentage = this_delta / total_delta
                metric_delta = metric(this_fix) - metric(next_fix)
                metric_delta_mod = -1 * metric_delta * percentage
                metric_out = metric(this_fix) + metric_delta_mod
                """
                print "-" * 100
                print this_fix.lap_time, metric(this_fix)
                print next_fix.lap_time, metric(next_fix)
                print total_delta
                print seconds
                print this_delta, percentage
                print metric_delta, metric_delta_mod, metric_out
                print "-" * 100
                """
                return metric_out

        # Erg, just use the last one?
        return metric(self.fixes[-1])


    def get_nearest_speed_direction_change(self, seconds, look_forward=False):
        return self.get_nearest_metric_direction_change(self.speed_markers, seconds, look_forward)

    def get_nearest_lin_g_direction_change(self, seconds, look_forward=False):
        return self.get_nearest_metric_direction_change(self.lin_g_markers, seconds, look_forward)

    def get_nearest_lat_g_direction_change(self, seconds, look_forward=False):
        return self.get_nearest_metric_direction_change(self.lat_g_markers, seconds, look_forward)

    def get_nearest_metric_direction_change(self, markers, seconds, look_forward=False):
        # Find the closest speed change that is _behind_ this fix
        # Unless look_forward=True, then we look _ahead_ of this fix

        # Assumes speed_markers are sorted in time
        reverse_markers = [m for m in markers]
        if not look_forward:
            reverse_markers.reverse()
        for marker in reverse_markers:
            this_seconds = marker['seconds']
            if not look_forward:
                if this_seconds > seconds:
                    continue
                else:
                    return marker
            else:
                if this_seconds < seconds:
                    continue
                else:
                    return marker

        return None

    def _calc(self):
        # find lap length
        max_time = 0
        end_time = 0
        start_time = 0
        min_time = 999999
        utc = ""
        if self.fixes and self.fixes[0].is_utc:
            utc = " UTC"


        # Peek speed / gforce variables
        peek_state = {}

        for fix in self.fixes:
            def peek_metric_calc(state, metric_name, storage_name):
                last_metric_name = "last_%s" % metric_name
                last_direction_name = "last_%s_direction" % metric_name
                last_metric = state.get(last_metric_name, None)
                last_direction = state.get(last_direction_name, None)
                last_fix = state.get('last_fix', None)

                cur_metric = getattr(fix, metric_name)
                cur_direction = None

                if last_metric is not None:
                    if cur_metric > last_metric:
                        cur_direction = 1
                    elif cur_metric < last_metric:
                        cur_direction = -1
                    else:
                        cur_direction = last_direction

                    if (last_direction is not None
                        and cur_direction is not None
                        and cur_direction != last_direction):

                        # We've found either a straight vmax or a corner vmin
                        getattr(self, storage_name).append(
                            {"metric": last_metric,
                             "direction": last_direction,
                             "fix": last_fix,
                             "seconds": last_fix.lap_time
                            })

                state[last_direction_name] = cur_direction
                state[last_metric_name] = cur_metric

            if 'last_fix' in peek_state:
                peek_metric_calc(peek_state, 'speed_mph', 'speed_markers')
                peek_metric_calc(peek_state, 'lat_g', 'lat_g_markers')
                peek_metric_calc(peek_state, 'lin_g', 'lin_g_markers')


            if fix.lap_time <= min_time:
                min_time = fix.lap_time
                start_time = fix.wall_time
                self.date = parser.parse(fix.date)
            if fix.lap_time > max_time:
                max_time = fix.lap_time
                end_time = fix.wall_time

            peek_state['last_fix'] = fix

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

    def get_time(self):
        mins = self.lap_time / 60
        sec = self.lap_time % 60
        return "%.2d:%06.3f" % (mins, sec)

    def __str__(self):
        return "Lap %s, %s, %s fixes" % (self.lapnum, self.get_time(), len(self.fixes))


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
