# USAGE:
# python scan.py (--images <IMG_DIR> | --image <IMG_PATH>) [-i]
# For example, to scan a single image with interactive mode:
# python scan.py --image sample_images/desk.JPG -i
# To scan all images in a directory automatically:
# python scan.py --images sample_images

# Scanned images will be output to directory named 'output'

from posixpath import basename
from talkdoc_core.scan_transforms import PolygonInteractor, ScanTransform
from scipy.spatial import distance as dist
from matplotlib.patches import Polygon
import numpy as np
import matplotlib.pyplot as plt
import itertools
import cv2
from pylsd.lsd import lsd
import argparse
import os
from PIL import Image

class DocScanner:
    """Document scanner for images."""

    def __init__(self, interactive: bool = False, min_quad_area_ratio: float = 0.25, max_quad_angle_range: int = 40):
        """
        Args:
            interactive: If True, user can adjust screen contour before transformation.
            min_quad_area_ratio: Minimum area ratio for a valid quadrilateral.
            max_quad_angle_range: Maximum allowed angle range for a valid quadrilateral.
        """
        self.interactive = interactive
        self.min_quad_area_ratio = min_quad_area_ratio
        self.max_quad_angle_range = max_quad_angle_range

    @staticmethod
    def filter_corners(corners, min_dist=20):
        """Filter out corners that are too close to each other."""
        filtered = []
        for c in corners:
            if all(dist.euclidean(rep, c) >= min_dist for rep in filtered):
                filtered.append(c)
        return filtered

    @staticmethod
    def angle_between_vectors_degrees(u, v):
        """Angle between two vectors in degrees."""
        cos_theta = np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v))
        cos_theta = np.clip(cos_theta, -1.0, 1.0)
        return np.degrees(np.arccos(cos_theta))

    def get_angle(self, p1, p2, p3):
        """Angle at p2 between p1 and p3."""
        a, b, c = map(np.array, (p1, p2, p3))
        return self.angle_between_vectors_degrees(a - b, c - b)

    def angle_range(self, quad):
        """Range between max and min interior angles of a quadrilateral."""
        quad = np.squeeze(quad)
        angles = [
            self.get_angle(quad[0], quad[1], quad[2]),
            self.get_angle(quad[1], quad[2], quad[3]),
            self.get_angle(quad[2], quad[3], quad[0]),
            self.get_angle(quad[3], quad[0], quad[1]),
        ]
        return np.ptp(angles)

    def get_corners(self, img):
        """Detect potential corners in the image."""
        lines = lsd(img)
        corners = []
        if lines is not None:
            lines = lines.squeeze().astype(np.int32).tolist()
            h_canvas = np.zeros(img.shape, dtype=np.uint8)
            v_canvas = np.zeros(img.shape, dtype=np.uint8)
            for x1, y1, x2, y2, *_ in lines:
                if abs(x2 - x1) > abs(y2 - y1):
                    (x1, y1), (x2, y2) = sorted([(x1, y1), (x2, y2)], key=lambda pt: pt[0])
                    cv2.line(h_canvas, (max(x1 - 5, 0), y1), (min(x2 + 5, img.shape[1] - 1), y2), 255, 2)
                else:
                    (x1, y1), (x2, y2) = sorted([(x1, y1), (x2, y2)], key=lambda pt: pt[1])
                    cv2.line(v_canvas, (x1, max(y1 - 5, 0)), (x2, min(y2 + 5, img.shape[0] - 1)), 255, 2)
            for canvas, axis in [(h_canvas, 0), (v_canvas, 1)]:
                cnts, _ = cv2.findContours(canvas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                cnts = sorted(cnts, key=lambda c: cv2.arcLength(c, True), reverse=True)[:2]
                for cnt in cnts:
                    cnt = cnt.reshape(-1, 2)
                    min_idx = np.argmin(cnt[:, axis])
                    max_idx = np.argmax(cnt[:, axis])
                    min_pt = tuple(cnt[min_idx])
                    max_pt = tuple(cnt[max_idx])
                    corners.extend([min_pt, max_pt])
            overlap = (h_canvas + v_canvas) == 2
            y, x = np.where(overlap)
            corners.extend(zip(x, y))
        return self.filter_corners(corners)

    def is_valid_contour(self, cnt, width, height):
        """Check if contour is a valid document quadrilateral."""
        return (
            len(cnt) == 4
            and cv2.contourArea(cnt) > width * height * self.min_quad_area_ratio
            and self.angle_range(cnt) < self.max_quad_angle_range
        )

    def get_contour(self, image):
        """Find the document contour in the image."""
        MORPH, CANNY = 9, 84
        height, width = image.shape[:2]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (7, 7), 0)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (MORPH, MORPH))
        dilated = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        edged = cv2.Canny(dilated, 0, CANNY)
        corners = self.get_corners(edged)
        candidates = []
        if len(corners) >= 4:
            quads = [
                np.array([pt for pt in quad], dtype="float32")
                for quad in itertools.combinations(corners, 4)
            ]
            quads = [ScanTransform.order_points(q) for q in quads]
            quads = sorted(quads, key=cv2.contourArea, reverse=True)[:5]
            quads = sorted(quads, key=self.angle_range)
            approx = quads[0]
            if self.is_valid_contour(approx, width, height):
                candidates.append(approx)
        cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]
        for c in cnts:
            approx = cv2.approxPolyDP(c, 80, True)
            if self.is_valid_contour(approx, width, height):
                candidates.append(np.squeeze(approx))
                break
        if not candidates:
            return np.array([
                [width, 0],
                [width, height],
                [0, height],
                [0, 0]
            ], dtype="float32")
        return max(candidates, key=cv2.contourArea)

    def interactive_get_contour(self, contour, image):
        """Let user adjust the detected contour interactively."""
        poly = Polygon(contour, animated=True, fill=False, color="yellow", linewidth=5)
        fig, ax = plt.subplots()
        ax.add_patch(poly)
        ax.set_title("Drag the corners to the document. Close window when finished.")
        PolygonInteractor(ax, poly)
        plt.imshow(image)
        plt.show()
        new_points = np.array(poly.xy[:4], dtype="float32")
        return new_points

    def scan(self, image_path):
        """Scan a single image and save the result."""
        RESCALED_HEIGHT = 500.0
        OUTPUT_DIR = 'output'
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        image = cv2.imread(image_path)
        if image is None:
            print(f"Could not read image: {image_path}")
            return
        ratio = image.shape[0] / RESCALED_HEIGHT
        orig = image.copy()
        rescaled = ScanTransform.resize(image, height=int(RESCALED_HEIGHT))
        contour = self.get_contour(rescaled)
        if self.interactive:
            contour = self.interactive_get_contour(contour, rescaled)
        warped = ScanTransform.four_point_transform(orig, contour * ratio)
        gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        sharpen = cv2.addWeighted(gray, 1.5, cv2.GaussianBlur(gray, (0, 0), 3), -0.5, 0)
        thresh = cv2.adaptiveThreshold(
            sharpen, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 15
        )
        basename = os.path.basename(image_path)
        out_image_path = os.path.join(OUTPUT_DIR, basename)
        out_pdf_path = os.path.splitext(out_image_path)[0] + ".pdf"

        # Save the processed image
        cv2.imwrite(out_image_path, warped)

        # Convert the image to PDF
        pil_image = Image.fromarray(cv2.cvtColor(warped, cv2.COLOR_BGR2RGB))
        pil_image.save(out_pdf_path, "PDF", resolution=100.0)

        print(f"Processed {basename} and saved as {out_pdf_path}")

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--images", help="Directory of images to be scanned")
    group.add_argument("--image", help="Path to single image to be scanned")
    parser.add_argument("-i", action='store_true', help="Interactive mode for corner adjustment")
    args = parser.parse_args()
    scanner = DocScanner(interactive=args.i)
    valid_exts = {".jpg", ".jpeg", ".jp2", ".png", ".bmp", ".tiff", ".tif"}
    if args.image:
        scanner.scan(args.image)
    else:
        files = [
            f for f in os.listdir(args.images)
            if os.path.splitext(f)[1].lower() in valid_exts
        ]
        for fname in files:
            scanner.scan(os.path.join(args.images, fname))

if __name__ == "__main__":
    main()
