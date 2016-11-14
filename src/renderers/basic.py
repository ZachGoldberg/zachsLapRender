import cv2

from renderers import BaseRenderer

class BasicRenderer(BaseRenderer):

    def __init__(self, video):
        super(BasicRenderer, self).__init__(video)

    def render_frame(self, frame, lapparams, framenum, lap):
        if not lapparams.is_mid_lap(framenum):
            return frame

        start_frame = lapparams.start_frame
        frames_in = framenum - start_frame
        seconds_total_in = frames_in / self.video.fps
        minutes_in = int(seconds_total_in / 60)
        seconds_in = seconds_total_in % 60


        # Render watermark
        txt = "Rendered by zachsLapRenderer"
        cv2.putText(frame, txt, (5, self.video.height - 10), cv2.FONT_HERSHEY_PLAIN, 2,
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

        # Render G force in numbers for now
        lat_g = lap.get_lat_g_at_time(seconds_total_in)
        lin_g = lap.get_lin_g_at_time(seconds_total_in)
        lat_g_txt = "Lateral Gs: %6.2f" % lat_g
        lin_g_txt = "Accel Gs: %6.2f" % lin_g
        cv2.putText(frame, lat_g_txt, (200, 150), cv2.FONT_HERSHEY_PLAIN, 4,
                    (255, 255, 255), 2, cv2.CV_AA)

        cv2.putText(frame, lin_g_txt, (900, 150), cv2.FONT_HERSHEY_PLAIN, 4,
                    (255, 255, 255), 2, cv2.CV_AA)



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


        return frame
