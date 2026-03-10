import collections
from time import monotonic
from PyQt5.QtCore import QObject, pyqtSignal, QCoreApplication, pyqtSlot
from utils.ProcessingMode import ProcessingMode
import numpy as np
import cv2

class CameraWorker(QObject):
    signal = pyqtSignal(int, np.ndarray, np.ndarray, int, int, int, float, int, int)  # Emit processed frame and spot coordinates
    finished = pyqtSignal()

    def __init__(self, cam, processing_mode=ProcessingMode.NORMAL):
        super().__init__()
        self.cam = cam
        self.running = False

        # ROI tracking state
        self.scale = 0.5
        self.roi_size = 100
        self.roi_x, self.roi_y = 0, 0
        self.initialize_roi = False

        # Control variables
        self.processing_mode = processing_mode

        # Frames
        self.frame = None
        self.bkg = None

        # Control processing rate
        self.frame_skip = 0
        self.frame_count = 0

        # Tracking history — deque for O(1) append/trim
        self.max_history = 500
        self.history = collections.deque(maxlen=self.max_history)

        # Pre-computed morphological kernel (constant — no need to rebuild per frame)
        self._morph_kernel = np.ones((11, 11), np.uint8)

        # Last measurement index of TT
        self.latest_measurement_index_1 = -1
        self.latest_measurement_index_2 = -1

    @pyqtSlot(int, int)
    def update_measurement_index(self, idx1, idx2):
        """
        Slot to receive data from the instrument.
        This is thread-safe; Qt handles the transfer.
        """
        self.latest_measurement_index_1 = idx1
        self.latest_measurement_index_2 = idx2

    def start(self):
        self.running = True
        self.frame_count = 0
        # Direct loop — cam.acquire() blocks until a frame arrives (~frame period),
        # so there is no benefit to a QTimer; the camera rate is the natural throttle.
        while self.running:
            self.process_frame()
            # Drain the Qt event queue so queued slot deliveries (e.g. update_measurement_index)
            # are processed between frames while the event loop is not running.
            QCoreApplication.processEvents()
        self.finished.emit()

    def stop(self):
        self.running = False
        self.processing_mode = ProcessingMode.OFF

    def process_frame(self):
        # grab frame and set acquisition time
        frame_time = monotonic()
        frame = self.cam.acquire()
        self.frame = frame

        # Snapshot TT measurement indices
        current_index_1 = self.latest_measurement_index_1
        current_index_2 = self.latest_measurement_index_2

        if frame is None or frame.size == 0:
            return

        self.frame_count += 1
        if self.frame_skip != 0 and self.frame_count % self.frame_skip != 0:
            return

        height, width = frame.shape[:2]
        x_full, y_full, r_full = -1, -1, -1

        # video_frame: reference to the unmodified frame for storage/display.
        # cam.acquire() returns a fresh NumPy array each call, so no copy is needed.
        video_frame = frame

        # --- Optional background subtraction ---
        # Pre-compute HSV of the masked result so process_frame_and_find_spot
        # can reuse it without a second cvtColor call (M3).
        hsv_full = None
        if self.bkg is not None and self.bkg.shape == frame.shape:
            hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hsv_bkg = cv2.cvtColor(self.bkg, cv2.COLOR_BGR2HSV)
            diff_v = cv2.absdiff(hsv_frame[..., 2], hsv_bkg[..., 2])
            _, mask = cv2.threshold(diff_v, 30, 255, cv2.THRESH_BINARY)
            frame = cv2.bitwise_and(frame, frame, mask=mask)
            hsv_full = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # ---------------------------------------

        if self.processing_mode != ProcessingMode.OFF:
            # output copy only needed when overlays will be drawn
            output = frame.copy()

            # --- ROI initialization ---
            if self.initialize_roi:
                scaled = cv2.resize(frame, (0, 0), fx=self.scale, fy=self.scale)
                result = self.process_frame_and_find_spot(scaled, scale=self.scale)

                if result:
                    x_full, y_full, r_full = result
                    self.roi_x = max(0, x_full - self.roi_size // 2)
                    self.roi_y = max(0, y_full - self.roi_size // 2)
                    self.initialize_roi = False

                    cv2.circle(output, (x_full, y_full), r_full, (0, 255, 0), 2)
                    cv2.circle(output, (x_full, y_full), 2, (0, 0, 255), 3)

            # --- ROI tracking ---
            else:
                rx = max(0, min(self.roi_x, width - self.roi_size))
                ry = max(0, min(self.roi_y, height - self.roi_size))
                roi = frame[ry:ry + self.roi_size, rx:rx + self.roi_size]

                # Pass pre-computed HSV ROI slice when available (avoids redundant cvtColor)
                hsv_roi = hsv_full[ry:ry + self.roi_size, rx:rx + self.roi_size] if hsv_full is not None else None
                result = self.process_frame_and_find_spot(roi, offset_x=rx, offset_y=ry, hsv=hsv_roi)

                if result:
                    x_full, y_full, r_full = result
                    r_full = int(r_full / 2)
                    cv2.circle(output, (x_full, y_full), r_full, (0, 255, 0), 2)
                    cv2.circle(output, (x_full, y_full), 2, (0, 0, 255), 3)

                    # Update ROI center
                    self.roi_x = max(0, x_full - self.roi_size // 2)
                    self.roi_y = max(0, y_full - self.roi_size // 2)
                else:
                    # Lost target, try to reinitialize
                    self.initialize_roi = True

            # --- Maintain and draw trajectory ---
            if self.processing_mode == ProcessingMode.TRACKING:
                if x_full != -1 and y_full != -1:
                    self.history.append((x_full, y_full))
                elif self.history:
                    # Use last known position if detection fails
                    x_full, y_full = self.history[-1]

                # Draw motion trail
                if len(self.history) > 1:
                    overlay = output.copy()
                    color = (255, 0, 0)  # blue
                    thickness = 2
                    alpha = 0.2  # 0 = transparent, 1 = opaque

                    for i in range(1, len(self.history)):
                        cv2.line(overlay, self.history[i - 1], self.history[i], color, thickness)

                    cv2.addWeighted(overlay, alpha, output, 1 - alpha, 0, output)

            # --- Debug ROI outline ---
            if self.processing_mode == ProcessingMode.DEBUG:
                cv2.rectangle(output,
                            (self.roi_x, self.roi_y),
                            (self.roi_x + self.roi_size, self.roi_y + self.roi_size),
                            (255, 255, 0), 1)

        else:
            output = frame

        # Emit processed frame and coordinates
        self.signal.emit(self.frame_count, video_frame, output, x_full, y_full, r_full, frame_time, current_index_1, current_index_2)


    def process_frame_and_find_spot(self, image, offset_x=0, offset_y=0, scale=1.0, hsv=None):
        """Find the largest blueish spot in the given image."""
        if hsv is None:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Mask 1: The Violet Ring
        lower_violet = np.array([130, 60, 40])
        upper_violet = np.array([155, 255, 255])
        mask_violet = cv2.inRange(hsv, lower_violet, upper_violet)

        # Mask 2: The Saturated White Core
        # (High Value, Low Saturation)
        lower_white = np.array([0, 0, 230])
        upper_white = np.array([180, 50, 255])
        mask_white = cv2.inRange(hsv, lower_white, upper_white)

        # Combine and clean up
        combined_mask = cv2.bitwise_or(mask_violet, mask_white)

        # Close small holes (the 'donut' effect)
        mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, self._morph_kernel)

        if self.processing_mode == ProcessingMode.DEBUG:
            cv2.imshow("Robust Mask", mask)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        min_area = 50
        valid_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]

        if valid_contours:
            largest = max(valid_contours, key=cv2.contourArea)
            (x, y), radius = cv2.minEnclosingCircle(largest)

            return (
                int(offset_x + x / scale),
                int(offset_y + y / scale),
                int(radius / scale)
            )

        return None


    def capture_background(self):
        """Capture and store a background frame."""
        if self.frame is not None:
            self.bkg = self.frame.copy()
            cv2.imshow("background", self.bkg)

    def reset_background(self):
        """Reset stored background."""
        self.bkg = None

    def capture_single_frame(self):
        """Captures and returns a single camera frame."""
        if self.frame is not None:
            frame = self.frame.copy()

            window_name = "snapshot"
            cv2.imshow(window_name, frame)

            # Force the window to stay on top
            cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

            # Process the draw event (essential for the image to appear)
            cv2.waitKey(1)

            return frame
        return None

    def reset_tracking_history(self):
        """Clear tracking history."""
        self.history = collections.deque(maxlen=self.max_history)

    def reset_frame_counter(self):
        """Clear frame counter."""
        self.frame_count = 0
