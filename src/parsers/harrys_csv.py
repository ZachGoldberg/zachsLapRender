import csv
from StringIO import StringIO
from . import LaptimeParser
from models import Fix

class HarrysCSVParser(LaptimeParser):

    COL_MAPPING = {
        "INDEX": "fix_id",
        "LAPINDEX": "lap_index",
        "DATE": "date",
        "TIME": "wall_time",
        "TIME_LAP": "lap_time",
        "LATITUDE": "lat",
        "LONGITUDE": "long",
        "SPEED_KPH": "speed_kph",
        "SPEED_MPH": "speed_mph",
        "HEIGHT_M": "alt_m",
        "HEIGHT_FT": "alt_ft",
        "HEADING_DEG": "heading_deg",
        "GPSDIFFERENTIAL[UNKNOWN/2D3D/DGPS/INVALID]": "gps_diff",
        "GPSFIX[NOFIX/2D/3D/UNKNOWN]": "gps_fix_type",
        "SATELLITES": "satelites",
        "HDOP": "hdop",
        "ACCURACY_M": "accuracy",
        "DISTANCE_KM": "distance_km",
        "DISTANCE_MILE": "distance_mi",
        "ACCELERATIONSOURCE[CALCULATED/MEASURED/UNDEFINED]": "accel_source",
        "LATERALG": "lat_g",
        "LINEALG": "lin_g",
        "LEAN": "lean",
        "RPM": "rpm",
        "MAF": "maf",
        "WHEEL_SPEED_KPH": "odb_kph",
        "WHEEL_SPEED_MPH": "odb_mph",
        "THROTTLE": "throttle",
        "GEAR": "gear",
        "FUEL": "fuel",
        "COOLANT_CELSIUS": "coolant_c",
        "OIL_CELSIUS": "oil_c",
        "IAT_CELSIUS": "iat_c",
        "MAP": "map",
    }


    @classmethod
    def is_valid(cls, filename):
        if ".csv" in filename:
            return True

    @classmethod
    def parse_data(cls, datafile):
        """head -n 3 sample.csv
        Harry's GPS LapTimer
INDEX,LAPINDEX,DATE,TIME,TIME_LAP,LATITUDE,LONGITUDE,SPEED_KPH,SPEED_MPH,HEIGHT_M,HEIGHT_FT,HEADING_DEG,GPSDIFFERENTIAL[UNKNOWN/2D3D/DGPS/INVALID],GPSFIX[NOFIX/2D/3D/UNKNOWN],SATELLITES,HDOP,ACCURACY_M,DISTANCE_KM,DISTANCE_MILE,ACCELERATIONSOURCE[CALCULATED/MEASURED/UNDEFINED],LATERALG,LINEALG,LEAN,RPM,MAF,WHEEL_SPEED_KPH,WHEEL_SPEED_MPH,THROTTLE,GEAR,FUEL,COOLANT_CELSIUS,OIL_CELSIUS,IAT_CELSIUS,MAP
57358,381,14-AUG-16,16:57:02.65,0.000000,34.874742,-118.258734,102.600000,63.752684,740.000000,2427.821526,288.1,2,3,11,0.700000,4.9,0.000000,0.000000,1,0.15,0.34,8.500000,0,0.000000,0.000000,0.000000,0.000000,0,0.000000,0.000000,0.000000,0.000000,0.000000
        """
        # Fast forward past the Harry's notice
        data = StringIO("\n".join(datafile.read().split("\n")[1:]))
        reader = csv.DictReader(data)
        for row in reader:
            fix = Fix()
            for k, v in row.iteritems():
                fix.setattr(cls.COL_MAPPING[k], v)

            print fix
