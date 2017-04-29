import cv2

import logging
import math
import numpy as np
import os
import time

from threading import Thread

from renderers import BaseRenderer, RenderParams
from utils import extract_audio, mix_audiofiles

logger = logging.getLogger(__name__)

class DualRenderer(BaseRenderer):
    def __init__(self, video1, video2, subrenderer):
        super(DualRenderer, self).__init__(video1)

        # TODO: Check that we have a total of only
        # 2 laps marked as renderable
        self.video1 = video1
        if not video2:
            video2 = video1

        self.video2 = video2

        self.renderer = subrenderer

        self.renderer1 = self.renderer(self.video1)
        self.renderer1.enable_map = False

        self.renderer2 = self.renderer(self.video2)
        self.renderer2.enable_map = False

        self.map_width = self.video1.width * 0.9
        self.map_height = self.video.height * 0.9

        self.map_y = 200
        self.map_x = self.map_width

    def generate_title(self, args, params):
        return "ZLR: Lap# %s (%s) vs. Lap# %s (%s) at %s" % (
            int(params[0].lapinfo['lap'].lapnum),
            params[0].lapinfo['lap'].get_time(),
            int(params[1].lapinfo['lap'].lapnum),
            params[1].lapinfo['lap'].get_time(),
            args.trackname)


    def _get_render_params(self, outputdir):
        lapinfo1 = self.video1.renderable_laps()[0]
        lapinfo2 = self.video2.renderable_laps()[0]


        if self.video1 == self.video2:
            lapinfo2 = self.video2.renderable_laps()[1]


        return RenderParams([(self.video1, lapinfo1),
                             (self.video2, lapinfo2)], outputdir)

    def _render_audio_file(self, params, newaudiofile):
        lp1 = params.laps[0]
        lp2 = params.laps[1]

        logger.debug("Extracting audio...")
        newaudiofile1 = "/tmp/zachaudioout1.wav"
        extract_audio(self.video1.filenames[0], newaudiofile1, lp1.start_time, lp1.duration)

        newaudiofile2 = "/tmp/zachaudioout2.wav"
        extract_audio(self.video2.filenames[0], newaudiofile2, lp2.start_time, lp2.duration)

        if lp1.duration > lp2.duration:
            mix_audiofiles(newaudiofile1, newaudiofile2, newaudiofile)
        else:
            mix_audiofiles(newaudiofile2, newaudiofile1, newaudiofile)


    def _render_video_file(self, out, params, show_video=False):
        lp1 = params.laps[0]
        lp2 = params.laps[1]
        lp1.set_bookend_time(params.bookend_time)
        lp2.set_bookend_time(params.bookend_time)

        params.enable_info_panel = False

        framenum1 = lp1.start_frame
        framenum2 = lp2.start_frame
        frames_writen = 0
        total_frames = int(max([lp1.total_frames, lp2.total_frames]))
        end_frame = max([lp1.end_frame, lp2.end_frame])

        last_time = time.time()

        while framenum1 < lp1.end_frame or framenum2 < lp2.end_frame:
            framenum1 += 1
            framenum2 += 1
            frames_writen += 1
            if frames_writen % 30 == 0:
                delta = time.time() - last_time
                last_time = time.time()
                logger.debug("Written %s/%s frames, %s fps..." % (
                    frames_writen, total_frames,
                    (30 / delta)))

            thread1 = None
            thread2 = None
            t1val = {}
            t2val = {}
            if framenum1 <= lp1.end_frame:
                ret1, frame1 = params.get_framenum(lp1, framenum1)
                def render_vid(val):
                    self.renderer1.render_frame(frame1, params, lp1, framenum1, lp1.lapinfo["lap"])
                    val['frame'] = frame1

                if frame1 != None:
                    thread1 = Thread(target=render_vid, args=(t1val, ))
                    thread1.start()
            else:
                # Frame1 will be from the last iteration
                pass

            if framenum2 <= lp2.end_frame:
                ret2, frame2 = params.get_framenum(lp2, framenum2, 1)
                def render_vid2(val):
                    self.renderer2.render_frame(frame2, params, lp2, framenum2, lp2.lapinfo["lap"])
                    val['frame'] = frame2

		if frame2 != None:
                    thread2 = Thread(target=render_vid2, args=(t2val, ))
                    thread2.start()
            else:
                # Frame2 will be from the last iteration
                pass

            if thread1:
                thread1.join()
                frame1 = t1val['frame']
            if thread2:
                thread2.join()
                frame2 = t2val['frame']

            if frame1 != None and frame2 != None:
                merged_frame = self.merge_frames(frame1, frame2)
                self.render_frame(merged_frame,
                              params,
                              (lp1, lp2),
                              (framenum1, framenum2),
                              (lp1.lapinfo['lap'], lp2.lapinfo['lap']))

                out.write(merged_frame)

                if show_video:
                    cv2.imshow('frame', merged_frame)
                    keypress = cv2.waitKey(1)

        logger.debug("Buttoning up video...")
        params.release()
        cv2.destroyAllWindows()
        return True


    def render_frame(self, frame,
                     params,
                     lapparams,
                     framenums,
                     laps):
        if not lapparams[0].is_mid_lap(framenums[0]):
            return frame

        starts = [lapparams[0].lap_start_frame, lapparams[1].lap_start_frame]

        color1 = (255, 255, 100)
        color2 = (255, 150, 100)

        start_frame1 = lapparams[0].lap_start_frame
        start_frame2 = lapparams[1].lap_start_frame
        frames_in1 = framenums[0] - lapparams[0].lap_start_frame
        frames_in2 = framenums[1] - lapparams[1].lap_start_frame
        seconds_in1 = frames_in1 / self.video1.fps
        seconds_in2 = frames_in2 / self.video2.fps

        distance1 = laps[0].get_distance_at_time(seconds_in1)
        t_distance1 = laps[0].total_distance
        dist_perc1 = 100 * (distance1 / t_distance1)

        distance2 = laps[1].get_distance_at_time(seconds_in2)
        t_distance2 = laps[1].total_distance
        dist_perc2 = 100 * (distance2 / t_distance2)


        with self.alpha(0.5, frame):
            self.draw_map(frame, starts[0], framenums[0], laps[0])
            self.draw_map(frame, starts[1], framenums[1], laps[1])

            # Draw the leading ball first
            if dist_perc1 > dist_perc2:
                self.draw_map_ball(frame, starts[1], framenums[1], laps[1], color2)
                self.draw_map_ball(frame, starts[0], framenums[0], laps[0], color1)
            else:
                self.draw_map_ball(frame, starts[0], framenums[0], laps[0], color1)
                self.draw_map_ball(frame, starts[1], framenums[1], laps[1], color2)


            txt = "%4.2f%%" % (dist_perc1 - dist_perc2)
            txtheight = (self.video1.height / 2) + 50
            txtw_start = (self.video1.width / 2) - 300
            self.text(frame, "Top vs.",
                      (txtw_start, txtheight),
                      cv2.FONT_HERSHEY_PLAIN, 2,
                      color1, 2, cv2.CV_AA)

            self.text(frame, "Bottom:",
                      (txtw_start + 135, txtheight),
                      cv2.FONT_HERSHEY_PLAIN, 2,
                      color2, 2, cv2.CV_AA)

            self.text(frame, txt,
                      (txtw_start + 280, txtheight),
                      cv2.FONT_HERSHEY_PLAIN, 2,
                      (255, 255, 255), 2, cv2.CV_AA)


    def merge_frames(self, frame1, frame2):
        height = self.video1.height / 2
        width = self.video1.width

        blank_image = np.zeros((height * 2,width,3), np.uint8)

        top = cv2.resize(frame1, (width, height),
                         interpolation = cv2.INTER_CUBIC)
        bottom = cv2.resize(frame2, (width, height),
                         interpolation = cv2.INTER_CUBIC)

        blank_image[0:height,:] = top
        blank_image[height:height*2,:] = bottom

        return blank_image
