import cv2
import os

import settings

from datetime import datetime
from utils import creation_time

class Video(object):
    def __init__(self, filename):
        self.filename = filename
        self.file_start_date = None
        self.last_modified_at = None
        self.last_access_at = None
        self.created_at = None
        self.is_valid_video = False
        self._calc()

    def _calc(self):
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
        # Verify that it's a valid video that cv2 can inspect
        try:
            cap = cv2.VideoCapture(self.filename)
            cap.release()
        except:
            return

        self.file_start_date = creation_time(self.filename)
        self.is_valid_video = True

    def is_valid(self):
        return self.is_valid_video

    def start_time(self):
        if self.file_start_date:
            return self.file_start_date
        else:
            return self.created_at

    def __str__(self):
        return "%s starting at %s" % (self.filename,
                                      self.start_time())

class Day(object):
    pass

class Session(object):
    pass

class Lap(object):
    def __init__(self, lapnum, fixes):
        self.lapnum = lapnum
        self.fixes = fixes
        self._calc()

    def _calc(self):
        # find lap length
        max_time = 0
        end_time = 0
        start_time = 0
        min_time = 999999
        for fix in self.fixes:
            if fix.lap_time <= min_time:
                min_time = fix.lap_time
                start_time = fix.wall_time

            if fix.lap_time > max_time:
                max_time = fix.lap_time
                end_time = fix.wall_time

        self.lap_time = max_time
        self.end_time = end_time
        self.start_time = start_time

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
