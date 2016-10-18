import cv2
import math
from datetime import timedelta


from renderers import BaseRenderer
class LikeHarrysRenderer(BaseRenderer):

    def __init__(self, video):
        super(LikeHarrysRenderer, self).__init__(video)

    def render_frame(self, frame, start_frame, framenum, lap):
        frames_in = framenum - start_frame
        seconds_total_in = frames_in / self.video.fps
        minutes_in = int(seconds_total_in / 60)
        seconds_in = seconds_total_in % 60


        # See if we have any vmin/vmax annotations
        speedinfo = lap.get_nearest_speed_direction_change(
            seconds_total_in)

        brakeinfo = lap.get_nearest_lin_g_direction_change(seconds_total_in)
        cornerinfo = lap.get_nearest_lat_g_direction_change(seconds_total_in)

        # How long to show a speed notice for
        METRIC_APEX_DURATION = 3

        # How long should the fade out be
        METRIC_APEX_FADE = 1

        # How long to fade in
        METRIC_FADE_IN = 0.5

        # Minimum cornering Gs that will trigger a "max corner g" annotation
        MIN_APEX_CORNER_G = 0.6

        # Minimum braking Gs that will trigger a "max break g" annotation
        MIN_BRAKE_G = -0.3

        start_fade = METRIC_APEX_DURATION - METRIC_APEX_FADE

        # Margin between widgets on the bottom
        margin = 5

        # Width of the MPH / Laptime meter
        meter_width = 200

        # Radius of g-meter
        radius = self.g_meter_size / 2

        # g-meter origin
        origin = (radius + margin, self.from_bottom(radius + 35))

        # Render watermark
        txt = "Rendered by zachsLapRenderer"
        self.text(frame, txt, (5, self.from_bottom(10)), cv2.FONT_HERSHEY_PLAIN, 2,
                  (255, 255, 255), 1, cv2.CV_AA)

        # Render lap info
        lapdate = (lap.start_time + timedelta(seconds=seconds_total_in)).strftime(
            "%b %d, %Y %I:%M %p")
        trackname = self.video.trackname
        self.text(frame, lapdate, (margin * 2, self.from_bottom(75 + self.g_meter_size + margin)),
                  cv2.FONT_HERSHEY_PLAIN, 1.5,
                  (255, 255, 255), 1, cv2.CV_AA)

        self.text(frame, trackname, (margin * 2, self.from_bottom(45 + self.g_meter_size + margin)),
                  cv2.FONT_HERSHEY_PLAIN, 1.5,
                  (255, 255, 255), 1, cv2.CV_AA)

        with self.alpha(0.1, frame):
            lat_g = lap.get_lat_g_at_time(seconds_total_in)
            lin_g = lap.get_lin_g_at_time(seconds_total_in)

            self.render_g_meter(frame,
                                origin, radius,
                                (100, 100, 100),
                                (200, 200, 200),
                                (255, 255, 255),
                                lat_g,
                                lin_g)

            # Render MPH
            # Erg, first figure out MPH
            mph = lap.get_mph_at_time(seconds_total_in)
            mph_txt = "%3.0f mph" % mph
            g_meter_right_edge = (margin + radius * 2)
            topLeft = [(margin + g_meter_right_edge),
                       self.from_bottom(40 + 60)]
            bottomRight = [(margin + g_meter_right_edge + meter_width),
                           self.from_bottom(40)]
            self.rounded_rectangle(frame,
                                   topLeft, bottomRight,
                                   (255, 255, 255),
                                   1,
                                   cv2.CV_AA,
                                   10,
                                   fill=True,
                                   fillColor=(50, 50, 50))

            self.text(frame, mph_txt,
                      (topLeft[0] + margin * 3,
                       self.from_bottom(55)),
                      cv2.FONT_HERSHEY_PLAIN, 2.5,
                      (255, 255, 255), 2, cv2.CV_AA)

            topLeft = [(margin + g_meter_right_edge),
                       self.from_bottom(110 + margin + 60)]
            bottomRight = [(margin + g_meter_right_edge + meter_width),
                           self.from_bottom(110)]

            self.rounded_rectangle(frame,
                                   topLeft, bottomRight,
                                   (255, 255, 255),
                                   1,
                                   cv2.CV_AA,
                                   10,
                                   fill=True,
                                   fillColor=(50, 50, 50))

            txt = "%.2d:%05.2f" % (minutes_in, seconds_in)
            self.text(frame, txt,
                            (topLeft[0] + margin * 3,
                             self.from_bottom(130)),
                            cv2.FONT_HERSHEY_PLAIN, 2.5,
                            (255, 255, 255), 2, cv2.CV_AA)



        def render_metric_direction_change(metricinfo, metric_text_func,
                                           metric_duration, metric_fade, render_pos):
            if not metricinfo:
                return

            seconds_since_metric = seconds_total_in - metricinfo['seconds']
            if seconds_since_metric < METRIC_APEX_DURATION:
                text = metric_text_func(metricinfo)
                alpha = 0
                if seconds_since_metric > start_fade:
                    time_since_fade_start = seconds_since_metric - start_fade
                    alpha = (time_since_fade_start / METRIC_APEX_FADE)

                if seconds_since_metric < METRIC_FADE_IN:
                    alpha = 1- (seconds_since_metric / METRIC_FADE_IN)

                with self.alpha(alpha, frame):
                    topLeft = (render_pos[0] - 10, render_pos[1] - 40)
                    bottomRight = (render_pos[0] + 10 + 24 * len(text), render_pos[1] + 10)

                    self.rounded_rectangle(frame,
                                           topLeft, bottomRight,
                                           (255, 255, 255),
                                           1,
                                           cv2.CV_AA,
                                           10,
                                           fill=True,
                                           fillColor=(50, 50, 50))

                    self.text(frame, text, (render_pos[0] + 10, render_pos[1]),
                              cv2.FONT_HERSHEY_PLAIN, 2.5,
                              (255, 255, 255), 2, cv2.CV_AA)


        def speed_text(metricinfo):
            if metricinfo['direction'] == 1:
                return "Straight %5.2f mph" % metricinfo['metric']
            else:
                return "Corner %5.2f mph" % metricinfo['metric']

        def corner_text(metricinfo):
            return "Corner Gs:  %4.2f" % metricinfo['metric']

        def brake_text(metricinfo):
            return "Braking Gs:  %4.2f" % metricinfo['metric']


        render_metric_direction_change(speedinfo, speed_text, METRIC_APEX_DURATION,
                                       METRIC_APEX_FADE, (0, 100))

        # TODO: Show this on G-Map, not in Text
        #if (cornerinfo and
        #    abs(cornerinfo['metric']) > MIN_APEX_CORNER_G):
        #    render_metric_direction_change(cornerinfo, corner_text, METRIC_APEX_DURATION,
        #                                   METRIC_APEX_FADE, (0, 150))


        #if (brakeinfo and
        #    brakeinfo['direction'] == -1 and
        #    brakeinfo['metric'] < MIN_BRAKE_G):
        #    render_metric_direction_change(brakeinfo, brake_text, METRIC_APEX_DURATION,
        #                                   METRIC_APEX_FADE, (0, 200))


        self.draw_map(frame, start_frame, framenum, lap)

        return frame
