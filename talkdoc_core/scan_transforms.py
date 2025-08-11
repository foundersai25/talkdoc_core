from typing import Optional, Tuple
import numpy as np
import cv2
from scipy.spatial import distance as dist
from matplotlib.lines import Line2D
from matplotlib.artist import Artist


class ScanTransform:
    """Image transformation utilities for scanning applications."""

    @staticmethod
    def translate(image: np.ndarray, x: int, y: int) -> np.ndarray:
        """Translate image by x and y pixels."""
        M = np.float32([[1, 0, x], [0, 1, y]])
        return cv2.warpAffine(image, M, (image.shape[1], image.shape[0]))

    @staticmethod
    def rotate(
        image: np.ndarray, angle: float, center: Optional[Tuple[float, float]] = None, scale: float = 1.0
    ) -> np.ndarray:
        """Rotate image by angle (degrees) around center with optional scaling."""
        (h, w) = image.shape[:2]
        if center is None:
            center = (w / 2, h / 2)
        M = cv2.getRotationMatrix2D(center, angle, scale)
        return cv2.warpAffine(image, M, (w, h))

    @staticmethod
    def resize(
        image: np.ndarray, width: Optional[int] = None, height: Optional[int] = None, inter=cv2.INTER_AREA
    ) -> np.ndarray:
        """Resize image to given width or height while maintaining aspect ratio."""
        (h, w) = image.shape[:2]
        if width is None and height is None:
            return image
        if width is None:
            r = height / float(h)
            dim = (int(w * r), height)
        else:
            r = width / float(w)
            dim = (width, int(h * r))
        return cv2.resize(image, dim, interpolation=inter)

    @staticmethod
    def order_points(pts: np.ndarray) -> np.ndarray:
        """Order points in the order: top-left, top-right, bottom-right, bottom-left."""
        x_sorted = pts[np.argsort(pts[:, 0]), :]
        left_most, right_most = x_sorted[:2, :], x_sorted[2:, :]
        left_most = left_most[np.argsort(left_most[:, 1]), :]
        (tl, bl) = left_most
        D = dist.cdist(tl[np.newaxis], right_most, "euclidean")[0]
        (br, tr) = right_most[np.argsort(D)[::-1], :]
        return np.array([tl, tr, br, bl], dtype="float32")

    @staticmethod
    def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
        """Perform a perspective transform to obtain a top-down view of the image."""
        rect = ScanTransform.order_points(pts)
        (tl, tr, br, bl) = rect

        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        maxWidth = int(max(widthA, widthB))

        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        maxHeight = int(max(heightA, heightB))

        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(image, M, (maxWidth, maxHeight))


class PolygonInteractor:
    """Interactive polygon editor for matplotlib."""

    showverts = True
    epsilon = 5  # max pixel distance to count as a vertex hit

    def __init__(self, ax, poly):
        if poly.figure is None:
            raise RuntimeError(
                "You must first add the polygon to a figure or canvas before defining the interactor"
            )
        self.ax = ax
        self.poly = poly
        self.canvas = poly.figure.canvas

        x, y = zip(*self.poly.xy)
        self.line = Line2D(x, y, marker="o", markerfacecolor="r", animated=True)
        self.ax.add_line(self.line)

        self.poly.add_callback(self.poly_changed)
        self._ind = None  # the active vertex

        self.canvas.mpl_connect("draw_event", self.draw_callback)
        self.canvas.mpl_connect("button_press_event", self.button_press_callback)
        self.canvas.mpl_connect("button_release_event", self.button_release_callback)
        self.canvas.mpl_connect("motion_notify_event", self.motion_notify_callback)

    def get_poly_points(self) -> np.ndarray:
        """Return polygon points as a numpy array."""
        return np.asarray(self.poly.xy)

    def draw_callback(self, event):
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
        self.ax.draw_artist(self.poly)
        self.ax.draw_artist(self.line)
        self.canvas.blit(self.ax.bbox)

    def poly_changed(self, poly):
        """Called whenever the polygon object is changed."""
        vis = self.line.get_visible()
        Artist.update_from(self.line, poly)
        self.line.set_visible(vis)

    def get_ind_under_point(self, event) -> Optional[int]:
        """Get the index of the vertex under point if within epsilon tolerance."""
        xy = np.asarray(self.poly.xy)
        xyt = self.poly.get_transform().transform(xy)
        xt, yt = xyt[:, 0], xyt[:, 1]
        d = np.hypot(xt - event.x, yt - event.y)
        ind = np.argmin(d)
        if d[ind] >= self.epsilon:
            return None
        return ind

    def button_press_callback(self, event):
        if not self.showverts or event.inaxes is None or event.button != 1:
            return
        self._ind = self.get_ind_under_point(event)

    def button_release_callback(self, event):
        if not self.showverts or event.button != 1:
            return
        self._ind = None

    def motion_notify_callback(self, event):
        if (
            not self.showverts
            or self._ind is None
            or event.inaxes is None
            or event.button != 1
        ):
            return
        x, y = event.xdata, event.ydata
        self.poly.xy[self._ind] = x, y
        if self._ind == 0:
            self.poly.xy[-1] = x, y
        elif self._ind == len(self.poly.xy) - 1:
            self.poly.xy[0] = x, y
        self.line.set_data(zip(*self.poly.xy))
        self.canvas.restore_region(self.background)
        self.ax.draw_artist(self.poly)
        self.ax.draw_artist(self.line)
        self.canvas.blit(self.ax.bbox)
