import csv
import os
from datetime import datetime, timedelta
from StringIO import StringIO
from . import LaptimeParser
from models import Fix, Lap

class TrackAddictCSVParser(LaptimeParser):

    COL_MAPPING = {
        "Time": "lap_time",
        "Lap": "lap_index",
        "Latitude": "lat",
        "Longitude": "long",
        "Altitude (m)": "alt_m",
        "Altitude (ft)": "alt_ft",
        "Speed (MPH)": "speed_mph",
        "Heading": "heading_deg",
        "Accuracy (m)": "accuracy",
        "Accel X": "lat_g",
        "Accel Y": "lin_g",
        #"Accel Z": "accel_z"
    }



    @classmethod
    def is_valid(cls, filename):
        df = open(filename)
        start = df.readline()
        return "TrackAddict" in start

    @classmethod
    def parse_data(cls, datafile, filename=None):
        """head -n 5 sample.csv
# RaceRender Data: TrackAddict 3.4.2 on iOS 10.1.1 [iPhone8,4] (Mode: 0)
# End Point: 34.871512, -118.263719  @ -1.00 deg
"Time","Lap","Predicted Lap Time","Predicted vs Best Lap","GPS_Update","GPS_Delay","Latitude","Longitude","Altitude (m)","Altitude (ft)","Speed (MPH)","Heading","Accuracy (m)","Accel X","Accel Y","Accel Z"
0.000,0,0,0,1,0.000,34.8708676,-118.2630034,735.5,2413,13.2,303.4,5.0,0.00,0.00,0.00
0.010,0,0,0,0,0.000,34.8708676,-118.2630034,735.5,2413,13.2,303.4,5.0,0.04,0.01,-0.06
0.065,0,0,0,0,0.000,34.8708676,-118.2630034,735.5,2413,13.2,303.4,5.0,0.05,0.00,-0.04
        """

        # Start date is embedded in the filename only
        base = os.path.basename(filename)
        file_date = datetime.strptime(base[4:19], "%Y%m%d-%H%M%S")

        # Fast forward past the TrackAddict notice
        data = StringIO("\n".join(datafile.read().split("\n")[2:]))
        reader = csv.DictReader(data)
        raw_laps = {}
        fixes = []
        fix_id = 0
        last_lap_end = 0
        lap_ended = False
        last_fix = None
        for row in reader:
            if "End" in row['Time']:
                continue

            if "#" in row['Time']:
                # We need to insert a new fix with the exact lap end time,
                # then modify all fixes after that time to actually be for the next lap

                laptime = row['Time'][9:].split(':')
                laptime_s = int(laptime[0]) * 3600 + int(laptime[1]) * 60 + float(laptime[2])
                last_lap_end += laptime_s
                ending_lap = last_fix.lap_index
                # Bump all fixes from last lap after laptime_s to next lap
                fixes = list(raw_laps[last_fix.lap_index])
                for fix in fixes:
                    if float(fix.lap_time) > laptime_s:
                        raw_laps[fix.lap_index].remove(fix)

                        fix.lap_index += 1
                        if not fix.lap_index in raw_laps:
                            raw_laps[fix.lap_index] = []

                        fix.lap_time -= last_lap_end
                        raw_laps[fix.lap_index].insert(0, fix)

                # Now insert the "lap ending" fix into the end of the last lap
                lapEndFix = raw_laps[last_fix.lap_index][-1].copy()
                lapEndFix.lap_time = laptime_s
                raw_laps[ending_lap].append(lapEndFix)
                continue

            fix = Fix(is_utc=False)
            for k, v in row.iteritems():
                if k in cls.COL_MAPPING:
                    fix.setattr(cls.COL_MAPPING[k], v)

            fix.fix_id = fix_id
            fix_id += 1
            fix.date = str(file_date.date())
            fix.wall_time = str((file_date + timedelta(seconds=fix.lap_time)).time())
            fix.lap_time -= last_lap_end
            fixes.append(fix)
            lap_fixes = raw_laps.get(fix.lap_index, [])
            lap_fixes.append(fix)
            raw_laps[fix.lap_index] = lap_fixes
            last_fix = fix

        laps = []
        for lapnum, fixes in raw_laps.iteritems():
            laps.append(Lap(lapnum, fixes))

        return laps
