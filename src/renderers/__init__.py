import cv2
from contextlib import contextmanager

class BaseRenderer(object):
    def from_bottom(self, pixels):
        return self.video.height - pixels

    def from_right(self, pixels):
        return self.video.width - pixels

    @contextmanager
    def alpha(self, alpha, frame):
        beta = 1 - alpha
        gamma = 0
        overlay = frame.copy()
        yield
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
