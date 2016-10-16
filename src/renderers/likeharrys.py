import cv2
import math

from renderers import BaseRenderer
class LikeHarrysRenderer(BaseRenderer):

    def __init__(self, video):
        self.map_y = 150
        self.map_x = -50
        self.map_width = 300
        self.map_height = 300
        self.video = video

        self.g_meter_size = 150
        self.g_meter_ball_size = 10

    def render_frame(self, frame, start_frame, framenum, lap):
        frames_in = framenum - start_frame
        seconds_total_in = frames_in / self.video.fps
        minutes_in = int(seconds_total_in / 60)
        seconds_in = seconds_total_in % 60


        # Render watermark
        txt = "Rendered by zachsLapRenderer"
        cv2.putText(frame, txt, (5, self.from_bottom(10)), cv2.FONT_HERSHEY_PLAIN, 2,
                    (255, 255, 255), 1, cv2.CV_AA)

        # Render lap-clock
        txt = "Lap Time: %.2d:%06.3f" % (minutes_in, seconds_in)
        cv2.putText(frame, txt, (200, 100), cv2.FONT_HERSHEY_PLAIN, 4,
                    (255, 255, 255), 2, cv2.CV_AA)

        # Render MPH
        # Erg, first figure out MPH
        mph = lap.get_mph_at_time(seconds_total_in)
        mph_txt = "%6.0f MPH" % mph
        cv2.putText(frame, mph_txt, (900, 100), cv2.FONT_HERSHEY_PLAIN, 4,
                    (255, 255, 255), 2, cv2.CV_AA)

        # Render G force in a circle
        # Background Circle
        radius = self.g_meter_size / 2
        origin = (radius + 5, self.from_bottom(radius + 35))
        self.alpha_circle(frame, origin, radius, (100, 100, 100), -1, alpha=0.2)

        # Background outline
        self.alpha_circle(frame, origin, radius, (200, 200, 200), 1, alpha=0.2)
        # Outer Stroke
        self.alpha_circle(frame, origin, int(radius * 0.65), (255, 255, 255), 1, alpha=0.1)
        # Inner Stroke
        self.alpha_circle(frame, origin, int(radius * 0.3), (255, 255, 255), 1, alpha=0.1)
        # Crosshairs
        self.alpha_line(frame,
                        (radius + 5, self.from_bottom(2*radius + 35)),
                        (radius + 5, self.from_bottom(35)),
                        (255, 255, 255), 1, alpha=0.1)
        self.alpha_line(frame,
                        (5, origin[1]),
                        (2 * radius + 5, origin[1]),
                        (255, 255, 255), 1, alpha=0.1)

        # G-force ball
        lat_g = lap.get_lat_g_at_time(seconds_total_in)
        lin_g = lap.get_lin_g_at_time(seconds_total_in)

        self.draw_gforce_ball(frame, origin, lat_g, lin_g)

        # See if we have any vmin/vmax annotations
        speedinfo = lap.get_nearest_speed_direction_change(
            seconds_total_in)

        brakeinfo = lap.get_nearest_lin_g_direction_change(seconds_total_in)
        cornerinfo = lap.get_nearest_lat_g_direction_change(seconds_total_in)

        # How long to show a speed notice for
        METRIC_APEX_DURATION = 3

        # How long should the fade out be
        METRIC_APEX_FADE = 1

        # Minimum cornering Gs that will trigger a "max corner g" annotation
        MIN_APEX_CORNER_G = 0.6

        # Minimum braking Gs that will trigger a "max break g" annotation
        MIN_BRAKE_G = -0.3

        start_fade = METRIC_APEX_DURATION - METRIC_APEX_FADE

        def render_metric_direction_change(
                metricinfo, metric_text_func, metric_duration, metric_fade, render_pos):

            if metricinfo:
                seconds_since_metric = seconds_total_in - metricinfo['seconds']
                if seconds_since_metric < METRIC_APEX_DURATION:
                    text = metric_text_func(metricinfo)
                    if seconds_since_metric < start_fade:
                        cv2.putText(frame, text, render_pos, cv2.FONT_HERSHEY_PLAIN, 4,
                                    (255, 255, 255), 2, cv2.CV_AA)
                    else:
                        # Do some fun alpha fading
                        time_since_fade_start = seconds_since_metric - start_fade

                        alpha = 1 - (time_since_fade_start / METRIC_APEX_FADE)
                        beta = 1 - alpha
                        gamma = 0
                        overlay = frame.copy()
                        cv2.putText(overlay, text, render_pos, cv2.FONT_HERSHEY_PLAIN, 4,
                                    (255, 255, 255), 2, cv2.CV_AA)
                        cv2.addWeighted(overlay, alpha, frame, beta, gamma, frame)


        def speed_text(metricinfo):
            if metricinfo['direction'] == 1:
                return "Straight %6.2f mph" % metricinfo['metric']
            else:
                return "Corner %6.2f mph" % metricinfo['metric']

        def corner_text(metricinfo):
            return "Max Corner Gs:  %4.2f" % metricinfo['metric']

        def brake_text(metricinfo):
            return "Max Braking Gs:  %4.2f" % metricinfo['metric']

        render_metric_direction_change(speedinfo, speed_text, METRIC_APEX_DURATION,
                                       METRIC_APEX_FADE, (200, 200))

        if (cornerinfo and
            abs(cornerinfo['metric']) > MIN_APEX_CORNER_G):
            render_metric_direction_change(cornerinfo, corner_text, METRIC_APEX_DURATION,
                                           METRIC_APEX_FADE, (200, 250))


        if (brakeinfo and
            brakeinfo['direction'] == -1 and
            brakeinfo['metric'] < MIN_BRAKE_G):
            render_metric_direction_change(brakeinfo, brake_text, METRIC_APEX_DURATION,
                                           METRIC_APEX_FADE, (200, 300))


        self.draw_map(frame, start_frame, framenum, lap)

        cv2.imshow('frame', frame)
        keypress = cv2.waitKey(1)
        return frame

    def draw_gforce_ball(self, frame, origin, latg, ling):
        total_g = math.sqrt((latg * latg) + (ling * ling))
        total_g_txt = "%6.2fg" % total_g

        # TODO: Make this a bit more dynamic, bump it up if the
        # video has morethan 2gs in it
        max_g = 2.0

        scale_lat = latg / max_g
        scale_lin = ling / max_g

        orig_x = origin[0] + (self.g_meter_size / max_g) * (-1 * scale_lat)
        orig_y = origin[1] + (self.g_meter_size / max_g) * scale_lin

        ball_origin = (int(orig_x), int(orig_y))

        ball_color = (255, 255, 100)

        self.alpha_circle(frame, ball_origin, self.g_meter_ball_size,
                          ball_color, -1, alpha=0.1)

        self.alpha_text(frame, total_g_txt,
                        (ball_origin[0] - (self.g_meter_ball_size / 2) - 40,
                         ball_origin[1] - (self.g_meter_ball_size)),
                        cv2.FONT_HERSHEY_PLAIN, 1.5,
                        (255, 255, 255), 1, cv2.CV_AA, 0.1)



    def draw_map(self, frame, start_frame, framenum, lap):
        # Fuck me.
        # Step 1, compute the GPS bounding box
        bounds = lap.get_gps_bounds()
        lat_range = bounds[1] - bounds[0]
        long_range = bounds[3] - bounds[2]

        gps_origin = (
            # min_lat + half lat range = center of lat
            (bounds[0] + (lat_range / 2)),
            # min_long + half long range = center of long
            (bounds[2] + (long_range / 2))
        )


        lat_scale_factor = self.map_width / lat_range
        long_scale_factor = self.map_height / long_range

        map_x = self.map_x
        map_y = self.map_y

        if map_x < 0:
            map_x = self.video.width + self.map_x

        if map_y < 0:
            map_y = self.video.height + self.map_y


        map_orig = (map_x - self.map_width / 2,
                    map_y + (self.map_height / 2))

        def get_point(fix=None, lat=None, lon=None):
            if not lat and fix:
                lat = fix.lat
            if not lon and fix:
                lon = fix.long

            x = gps_origin[0] + ((lat - gps_origin[0]) * lat_scale_factor)
            y = gps_origin[1] + ((lon - gps_origin[1]) * long_scale_factor)

            x += map_orig[0]
            y += map_orig[1]


            return (int(x), int(y))

        last_fix = lap.fixes[0]
        for fix in lap.fixes[1:]:
            cv2.line(frame, get_point(last_fix), get_point(fix), (255,255,255), 3, cv2.CV_AA)
            last_fix = fix

        frames_in = framenum - start_frame
        seconds_total_in = frames_in / self.video.fps
        # Now let's draw us!
        (lat, lon) = lap.get_gps_at_time(seconds_total_in)
        cv2.circle(frame, get_point(None, lat, lon), 10, (255, 255, 100), -1)
