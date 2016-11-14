import cv2
import logging
import math
import numpy as np
import os
import subprocess
import time

from threading import Thread

from renderers import BaseRenderer
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

        self.video1.renderer = self.renderer(self.video1)
        self.video1.renderer.enable_map = False

        self.video2.renderer = self.renderer(self.video2)
        self.video2.renderer.enable_map = False

        self.map_width = self.video1.width * 0.9
        self.map_height = self.video.height * 0.9

        self.map_y = 200
        self.map_x = self.map_width

    def render_laps(self, outputdir, show_video=False):
        lapinfo1 = self.video1.renderable_laps()[0]
        lapinfo2 = self.video2.renderable_laps()[0]


        if self.video1 == self.video2:
            lapinfo2 = self.video2.renderable_laps()[1]

        # Load up the old videos
        # TODO: Need to account for split gopro videos!
        cap1 = cv2.VideoCapture(self.video1.filenames[0])
        cap2 = cv2.VideoCapture(self.video2.filenames[0])

        newfname = os.path.join(outputdir, "lap_%s_%s_join.noaudio.avi" % (
            lapinfo1["lap"].lapnum,
            lapinfo2["lap"].lapnum))

        final_newfname = os.path.join(outputdir, "lap_%s_%s_join.avi" % (
            lapinfo1["lap"].lapnum,
            lapinfo2["lap"].lapnum))


        logger.info("Rendering %s from %s, %s..." % (newfname,
                                                     self.video1.filebase,
                                                     self.video2.filebase))

        # Include the frame offset from calibration
        start_frame1 = lapinfo1['start_frame'] + self.video1.frame_offset
        start_time1 = start_frame1 / self.video1.fps
        end_frame1 = lapinfo1['end_frame'] + self.video1.frame_offset

        total_frames1 = end_frame1 - start_frame1
        duration1 = total_frames1 / self.video1.fps

        framenum1 = start_frame1

        start_frame2 = lapinfo2['start_frame'] + self.video2.frame_offset
        start_time2 = start_frame2 / self.video2.fps
        end_frame2 = lapinfo2['end_frame'] + self.video2.frame_offset

        total_frames2 = end_frame2 - start_frame2
        duration2 = total_frames2 / self.video2.fps

        framenum2 = start_frame2

        frames_writen = 0
        skipped = 0


        end_frame = max([end_frame1, end_frame2])
        total_frames = int(max([total_frames1, total_frames2]))

        # Create a new videowriter file
        fourcc = cv2.cv.CV_FOURCC(*'XVID')
        out = cv2.VideoWriter(newfname, fourcc, self.video1.fps, (self.video1.width,
                                                                  self.video1.height))

        logger.debug("Seeking to lap start at %s,%s ..." % (framenum1, framenum2))

        cap1.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, framenum1)
        cap2.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, framenum2)


        frame1 = None
        frame2 = None

        last_time = time.time()

        while(cap1.isOpened() or cap2.isOpened()):
            framenum1 += 1
            framenum2 += 1
            frames_writen += 1
            if frames_writen % 30 == 0:
                delta = time.time() - last_time
                last_time = time.time()
                logger.debug("Written %s/%s frames, %s fps..." % (frames_writen, total_frames,
                                                                  (30 / delta)))

            thread1 = None
            thread2 = None
            t1val = {}
            t2val = {}
            if framenum1 <= end_frame1:

                def render_vid(val):
                    ret1, frame1 = cap1.read()
                    self.video1.render_frame(frame1, start_frame1, framenum1, lapinfo1["lap"])
                    val['frame'] = frame1

                thread1 = Thread(target=render_vid, args=(t1val, ))
                thread1.start()
            else:
                # Frame1 will be from the last iteration
                pass

            if framenum2 <= end_frame2:
                def render_vid2(val):
                    ret2, frame2 = cap2.read()
                    self.video2.render_frame(frame2, start_frame2, framenum2, lapinfo2["lap"])
                    val['frame'] = frame2

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

            merged_frame = self.merge_frames(frame1, frame2)
            self.render_frame(merged_frame,
                              (start_frame1, start_frame2),
                              (framenum1, framenum2),
                              (lapinfo1['lap'], lapinfo2['lap']))

            out.write(merged_frame)

            if show_video:
                cv2.imshow('frame', merged_frame)
                keypress = cv2.waitKey(1)

            if framenum1 > end_frame1 and framenum2 > end_frame2:
                break

        logger.debug("Buttoning up video...")
        cap1.release()
        cap2.release()
        out.release()
        cv2.destroyAllWindows()

        logger.debug("Extracting audio...")
        newaudiofile1 = "/tmp/zachaudioout1.wav"
        extract_audio(self.video1.filenames[0], newaudiofile1, start_time1, duration1)

        newaudiofile2 = "/tmp/zachaudioout2.wav"
        extract_audio(self.video2.filenames[0], newaudiofile2, start_time2, duration2)

        newaudiofile = "/tmp/zachaudioout.wav"
        if duration1 > duration2:
            mix_audiofiles(newaudiofile1, newaudiofile2, newaudiofile)
        else:
            mix_audiofiles(newaudiofile2, newaudiofile1, newaudiofile)

        logger.debug("Merging video and audio data...")
        cmd = "ffmpeg -y -i %s -i %s -c:v copy -c:a aac -strict experimental %s" % (
            newfname, newaudiofile, final_newfname)

        subprocess.call(cmd, shell=True)

        logger.debug("Finished with %s" % final_newfname)
        return final_newfname


    def render_frame(self, frame,
                     starts,
                     framenums,
                     laps):

        color1 = (255, 255, 100)
        color2 = (255, 150, 100)

        seconds_in1 = (framenums[0] - starts[0]) / self.video1.fps
        seconds_in2 = (framenums[1] - starts[1]) / self.video2.fps

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
            if dustance_perc1 > distance_perc2:
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
