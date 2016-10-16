import cv2

class BaseRenderer(object):
    def from_bottom(self, pixels):
        return self.video.height - pixels

    def from_right(self, pixels):
        return self.video.width - pixels


    def alpha_circle(self, frame, origin, radius, color, thickness=1, lineType=8, shift=0, alpha=0):
        beta = 1 - alpha
        gamma = 0
        overlay = frame.copy()
        cv2.circle(frame, origin, radius, color, thickness, lineType, shift)
        cv2.addWeighted(overlay, alpha, frame, beta, gamma, frame)

    def alpha_line(self, frame, start, fin, color, thickness, lineType=8, shift=0, alpha=0):
        print start
        print fin

        beta = 1 - alpha
        gamma = 0
        overlay = frame.copy()
        cv2.line(frame, start, fin, color, thickness, lineType, shift)
        cv2.addWeighted(overlay, alpha, frame, beta, gamma, frame)
