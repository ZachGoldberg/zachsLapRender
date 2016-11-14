import cv2
import logging
import math
import os
import time
from threading import Thread

from contextlib import contextmanager
from utils import extract_audio, mix_audiofiles

logger = logging.getLogger(__name__)

class BaseRenderer(object):
    def __init__(self, video):
        self.g_meter_size = 200
        self.g_meter_ball_size = 10
        self.map_y = 150
        self.map_x = -50
        self.map_width = 300
        self.map_height = 300
        self.video = video

        self.enable_map = True

    def from_bottom(self, pixels):
        return self.video.height - pixels

    def from_right(self, pixels):
        return self.video.width - pixels

    @contextmanager
    def alpha(self, alpha, frame):
        if alpha != 0:
            beta = 1 - alpha
            gamma = 0
            overlay = frame.copy()
        yield
        if alpha != 0:
            cv2.addWeighted(overlay, alpha, frame, beta, gamma, frame)

    def alpha_circle(self, frame, origin, radius, color, thickness=1, lineType=8, shift=0, alpha=0):
        beta = 1 - alpha
        gamma = 0
        overlay = frame.copy()
        cv2.circle(frame, origin, radius, color, thickness, lineType, shift)

    def circle(self, frame, origin, radius, color, thickness=1, lineType=8, shift=0):
        cv2.circle(frame, origin, radius, color, thickness, lineType, shift)

    def line(self, frame, start, fin, color, thickness, lineType=8, shift=0):
        cv2.line(frame, start, fin, color, thickness, lineType, shift)

    def text(self, frame, txt, origin, font, size, color, stroke, linetype):
        cv2.putText(frame, txt, origin, font, size, color, stroke, linetype)

    def alpha_line(self, frame, start, fin, color, thickness, lineType=8, shift=0, alpha=0):
        beta = 1 - alpha
        gamma = 0
        overlay = frame.copy()
        cv2.line(frame, start, fin, color, thickness, lineType, shift)
        cv2.addWeighted(overlay, alpha, frame, beta, gamma, frame)

    def alpha_text(self, frame, txt, origin, font, size, color, stroke, linetype, alpha):
        beta = 1 - alpha
        gamma = 0
        overlay = frame.copy()
        cv2.putText(frame, txt, origin, font, size, color, stroke, linetype)
        cv2.addWeighted(overlay, alpha, frame, beta, gamma, frame)


    def rounded_rectangle(self, frame, topLeft, bottomRight, lineColor, thickness, lineType, cornerRadius, fill=False, fillColor=None):
        if fill:
            self._rounded_rectangle(frame, topLeft, bottomRight, fillColor, thickness, lineType, cornerRadius, fill, fillColor)
            self._rounded_rectangle(frame, topLeft, bottomRight, lineColor, thickness, lineType, cornerRadius, False)
        else:
            self._rounded_rectangle(frame, topLeft, bottomRight, lineColor, thickness, lineType, cornerRadius, fill, fillColor)


    def alpha_rounded_rectangle(self, frame, topLeft, bottomRight, lineColor, thickness, lineType, cornerRadius, alpha, fill=False, fillColor=None):
        beta = 1 - alpha
        gamma = 0
        overlay = frame.copy()
        if fill:
            self._rounded_rectangle(frame, topLeft, bottomRight, fillColor, thickness, lineType, cornerRadius, fill, fillColor)
            self._rounded_rectangle(frame, topLeft, bottomRight, lineColor, thickness, lineType, cornerRadius, False)
        else:
            self._rounded_rectangle(frame, topLeft, bottomRight, lineColor, thickness, lineType, cornerRadius, fill, fillColor)

        cv2.addWeighted(overlay, alpha, frame, beta, gamma, frame)


    """
    Draws a rectangle with rounded corners, the parameters are the same as in the OpenCV function @see rectangle();
    @param cornerRadius A positive int value defining the radius of the round corners.
    @author K

    From http://stackoverflow.com/questions/18973103/how-to-draw-a-rounded-rectangle-rectangle-with-rounded-corners-with-opencv
    """
    def _rounded_rectangle(self, src, topLeft, bottomRight, lineColor, thickness, lineType, cornerRadius, fill, fillColor=None):
        # corners:
        # p1 - p2
        # |     |
        # p4 - p3
        p1 = topLeft
        p2 = (bottomRight[0], topLeft[1])
        p3 = bottomRight
        p4 = (topLeft[0], bottomRight[1])

        # draw straight lines
        cv2.line(src,
                 (p1[0] + cornerRadius, p1[1]),
                 (p2[0] - cornerRadius, p2[1]),
                 lineColor, thickness, lineType);
        cv2.line(src,
                 (p2[0], p2[1] + cornerRadius),
                 (p3[0], p3[1] - cornerRadius),
                 lineColor, thickness, lineType);
        cv2.line(src,
                 (p4[0] + cornerRadius, p4[1]),
                 (p3[0] - cornerRadius, p3[1]),
                 lineColor, thickness, lineType);
        cv2.line(src,
                 (p1[0], p1[1] + cornerRadius),
                 (p4[0], p4[1] - cornerRadius),
                 lineColor, thickness, lineType);

        elipse_thickness = thickness

        if fill:
            elipse_thickness = -1
            cv2.rectangle(src,
                          (p1[0] + cornerRadius, p1[1]),
                          (p3[0] - cornerRadius, p3[1]),
                          fillColor, -1)
            cv2.rectangle(src,
                          (p1[0], p1[1] + cornerRadius),
                          (p3[0], p3[1] - cornerRadius),
                          fillColor, -1)
        # draw arcs
        cv2.ellipse(src,
                    (p1[0] + cornerRadius, p1[1] + cornerRadius), #center
                    (cornerRadius, cornerRadius ), #axes
                    180.0, #angle
                    0, #start_angle
                    90, #end_angle
                    lineColor, elipse_thickness, lineType );

        cv2.ellipse(src, (p2[0] - cornerRadius, p2[1] + cornerRadius),
                    (cornerRadius, cornerRadius), 270.0, 0, 90, lineColor, elipse_thickness, lineType )

        cv2.ellipse(src, (p3[0] -cornerRadius, p3[1] -cornerRadius),
                    (cornerRadius, cornerRadius), 0.0, 0, 90, lineColor, elipse_thickness, lineType );

        cv2.ellipse(src, (p4[0] + cornerRadius, p4[1] - cornerRadius),
                    (cornerRadius, cornerRadius), 90.0, 0, 90, lineColor, elipse_thickness, lineType );


    def render_g_meter(self, frame, origin, radius,
                        inner_color,
                        frame_color,
                        inner_line_color, lat_g, lin_g):
        # Render G force in a circle
        # Background Circle
        self.circle(frame, origin, radius, inner_color, -1)

        # Background outline
        self.circle(frame, origin, radius, frame_color, 1)

        # Outer Stroke
        self.circle(frame, origin, int(radius * 0.65), inner_line_color, 1)

        # Inner Stroke
        self.circle(frame, origin, int(radius * 0.3), inner_line_color, 1)

        # Crosshairs
        self.line(frame,
                  (origin[0], self.from_bottom(2*radius + 35)),
                  (origin[0], self.from_bottom(35)),
                  inner_line_color, 1)

        self.line(frame,
                  (origin[0] - radius, origin[1]),
                  (origin[0] + radius, origin[1]),
                  inner_line_color, 1)


        self.draw_gforce_ball(frame, origin, lat_g, lin_g)

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

        self.circle(frame, ball_origin, self.g_meter_ball_size,
                          ball_color, -1)

        self.text(frame, total_g_txt,
                        (ball_origin[0] - (self.g_meter_ball_size / 2) - 40,
                         ball_origin[1] - (self.g_meter_ball_size)),
                        cv2.FONT_HERSHEY_PLAIN, 1.5,
                        (255, 255, 255), 1, cv2.CV_AA)


    def _map_data(self, lap):
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

        map_origin = (map_x - self.map_width / 2,
                    map_y + (self.map_height / 2))

        return gps_origin, map_origin, (lat_scale_factor, long_scale_factor)

    def draw_map(self, frame, start_frame, framenum, lap):
        if not self.enable_map:
            return frame

        gps_origin, map_origin, scales = self._map_data(lap)

        last_fix = lap.fixes[0]
        for fix in lap.fixes[1:]:
            cv2.line(frame,
                     self._get_map_point(gps_origin, map_origin, scales, last_fix),
                     self._get_map_point(gps_origin, map_origin, scales, fix),
                     (255,255,255), 3, cv2.CV_AA)

            last_fix = fix

        self.draw_map_ball(frame, start_frame, framenum, lap)

    def _get_map_point(self, gps_origin, map_origin, scales, fix=None, lat=None, lon=None):
        if not lat and fix:
            lat = fix.lat
        if not lon and fix:
            lon = fix.long

        x = gps_origin[0] + ((lat - gps_origin[0]) * scales[0])
        y = gps_origin[1] + ((lon - gps_origin[1]) * scales[1])

        x += map_origin[0]
        y += map_origin[1]


        return (int(x), int(y))

    def draw_map_ball(self, frame, start_frame, framenum, lap, ballcolor=(255, 255, 100)):
        # Now let's draw us!
        gps_origin, map_origin, scales = self._map_data(lap)

        frames_in = framenum - start_frame
        seconds_total_in = frames_in / self.video.fps

        (lat, lon) = lap.get_gps_at_time(seconds_total_in)
        cv2.circle(frame, self._get_map_point(gps_origin, map_origin, scales, None, lat, lon), 10, ballcolor, -1)


    def _render_video_file(self, out, params, show_video=False):
        for lapparams in params.laps:

            framenum = lapparams.start_frame
            frames_writen = 0
            last_time = time.time()

            thread_results = []
            def render_thread(start):
                t_framenum = start
                while t_framenum <= lapparams.end_frame:
                    while len(thread_results) > 100:
                        time.sleep(.1)

                    ret, frame = params.get_framenum(lapparams, t_framenum)

                    rendered_frame = self.render_frame(frame,
                                                       lapparams.start_frame,
                                                       t_framenum,
                                                       lapparams.lapinfo["lap"])
                    thread_results.insert(0, rendered_frame)
                    t_framenum += 1

            worker_thread = Thread(target=render_thread, args=(framenum,))
            worker_thread.start()

            while framenum <= lapparams.end_frame:
                framenum += 1

                while len(thread_results) == 0:
                    time.sleep(0.1)

                rendered_frame = thread_results.pop()
                out.write(rendered_frame)

                if show_video:
                    cv2.imshow('frame', rendered_frame)
                    keypress = cv2.waitKey(1)

                # Assist Garbage collection, throw away the rendered frame
                rendered_frame = None

                frames_writen += 1
                if frames_writen % 30 == 0:
                    delta = time.time() - last_time
                    last_time = time.time()
                    logger.debug("Written %s/%s frames, %s fps..." % (frames_writen,
                                                                      lapparams.total_frames,
                                                                      (30 / delta)))

        logger.debug("Buttoning up video...")
        params.release()
        cv2.destroyAllWindows()
        return True

    def _render_audio_file(self, params, newaudiofile):
        logger.debug("Extracting audio...")
        extract_audio(self.video.filenames[0], newaudiofile, start_time, duration)

    def _merge_audio_and_video(self, videofname, audiofname, outputfile):
        logger.debug("Merging video and audio data...")
        cmd = "ffmpeg -y -i %s -i %s -c:v copy -c:a aac -strict experimental %s" % (
            videofname, audiofname, outputfile)
        subprocess.call(cmd, shell=True)

    def _get_render_params(self, outputdir):
        laptuples = []

        for lapinfo in self.video.matched_laps:
            if not lapinfo.get("render", True):
                logger.debug("Skipping lap %s due to render=false" % lapinfo['lap'])
                continue
            else:
                logger.debug("Generating params for %s" % lapinfo['lap'])

            laptuples.append((self.video, lapinfo))

        if laptuples:
            return RenderParams(laptuples, outputdir)

    def render_laps(self, outputdir, show_video=False, bookend_time=0):
        params = self._get_render_params(outputdir)
        if not params:
            return []

        params.set_bookend_time(bookend_time)

        logger.info("Rendering %s..." % (params.newfname))

        # Create a new videowriter file
        fourcc = cv2.cv.CV_FOURCC(*'XVID')
        out = cv2.VideoWriter(params.newfname, fourcc, params.fps, (params.width,
                                                             params.height))

        self._render_video_file(out, params, show_video=show_video)
        out.release()

        newaudiofile = "/tmp/zachaudioout.wav"
        self._render_audio_file(params, newaudiofile)

        self._merge_audio_and_video(params.newfname, newaudiofile, params.final_newfname)

        logger.debug("Finished with %s" % params.final_newfname)

        return [params.final_newfname]


class LapRenderParams(object):
    def __init__(self, video, lapinfo):
        self.video = video
        self.lapinfo = lapinfo
        self.start_frame = lapinfo['start_frame'] + video.frame_offset
        self.start_time = self.start_frame / video.fps
        self.end_frame = lapinfo['end_frame'] + video.frame_offset
        self.total_frames = self.end_frame - self.start_frame
        self.duration = self.total_frames / video.fps

    def set_bookend_time(self, btime):
        video = self.video
        lapinfo = self.lapinfo

        bookend_frames = btime * video.fps

        self.start_frame = lapinfo['start_frame'] + video.frame_offset - bookend_frames
        self.start_time = (self.start_frame / video.fps) - bookend_frames

        if self.start_frame < 0:
            self.start_frame = 0

        if self.start_time < 0:
            self.start_time = 0

        self.end_frame = lapinfo['end_frame'] + video.frame_offset + bookend_frames

        if self.end_frame > video.frame_count:
            self.end_frame = video.frame_count

        self.total_frames = self.end_frame - self.start_frame
        self.duration = self.total_frames / video.fps


class RenderParams(object):
    def __init__(self, videolaps, outputdir):
        self.oldcaps_f = {}
        self.oldcaps = {}
        self.capstate = {}
        for video, _ in videolaps:
            if not video in self.oldcaps:
                self.oldcaps_f[video] = []
                self.oldcaps[video] = []
                for fn in video.filenames:
                    self.oldcaps_f[video].append(fn)
                    self.oldcaps[video].append([])

        self.laps = []
        for video, lapinfo in videolaps:
            self.laps.append(LapRenderParams(video, lapinfo))

        self.newfname = os.path.join(outputdir, "lap_%s_%s.noaudio.avi" % (
            videolaps[0][1]["lap"].lapnum,
            videolaps[0][1]["lap"].lap_time))

        self.final_newfname = os.path.join(outputdir, "lap_%s_%s.avi" % (
            videolaps[0][1]["lap"].lapnum,
            videolaps[0][1]["lap"].lap_time))

        self.fps = videolaps[0][0].fps
        self.width = videolaps[0][0].width
        self.height = videolaps[0][0].height

    def set_bookend_time(self, btime):
        for lap in self.laps:
            lap.set_bookend_time(btime)


    def get_framenum(self, lapparams, framenum, open_index=0):
        # Figure out what capture this is
        # Then figure out where we are currently seeked in that capture
        # If it's the next frame, call read.  Otherwise, seek and read

        # Figure out which file in that video this is
        fileindex = lapparams.video.filename_number(framenum)

        video_fname = self.oldcaps_f[lapparams.video][fileindex]
        video_caps = self.oldcaps[lapparams.video]
        cap_sequence = video_caps[fileindex]

        while len(cap_sequence) <= open_index:
            cap = cv2.VideoCapture(video_fname)
            cap_sequence.append(cap)
            self.capstate[cap] = 0

        cap = cap_sequence[open_index]

        cap_last_postion = self.capstate[cap]

        if framenum == (cap_last_postion + 1):
            self.capstate[cap] = framenum
            return cap.read()
        else:
            print "SEEKING..."
            print framenum, cap_last_postion
            cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, framenum)
            self.capstate[cap] = framenum
            return cap.read()

    def release(self):
        for videocaps in self.oldcaps.values():
            for cap in videocaps:
                cap.release()


from basic import BasicRenderer
from dual import DualRenderer
from likeharrys import LikeHarrysRenderer

CalibrationRenderer = LikeHarrysRenderer
