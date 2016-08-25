class Day(object):
    pass

class Session(object):
    pass

class Lap(object):
    pass

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

        setattr(self, attr, val)


    def __str__(self):
        return "Fix %s Lap %s @%s %s:%s" % (self.fix_id,
                                             self.lap_index,
                                             self.lap_time,
                                             self.lat,
                                             self.long)
