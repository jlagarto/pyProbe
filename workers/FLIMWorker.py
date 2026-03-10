from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
import numpy as np

class FLIMWorker(QObject):
    """
    Worker that receives histogram data and processes fluorescence lifetime curves in real time.
    Assumes two histograms per data packet (channel 1 and channel 2).
    """
    processed = pyqtSignal(int, int, np.ndarray, dict, float)  # Emit lifetime results per channel as a dictionary

    def __init__(self, bin_width):
    
        super().__init__()
        self.enable_processing = False  # Control variable to enable/disable processing
        self.bin_width = bin_width  # Store bin width for lifetime estimation
        self._time_bins = None  # Cached arange; rebuilt only when histogram length changes
    
    @pyqtSlot(int, int, np.ndarray, float)
    def process(self, idx1, idx2, data, timestamp):
        
        if not self.enable_processing:
            self.processed.emit(idx1, idx2, data, {}, timestamp)
            return

        try:
            ch1 = data[0]
            ch2 = data[1]

            # Process both channels
            com1 = self.estimate_com(ch1)
            com2 = self.estimate_com(ch2)

            result = {
                'ch1': com1,
                'ch2': com2
            }

            self.processed.emit(idx1, idx2, data, result, timestamp)

        except Exception as e:
            print(f"[FLIMWorker] Processing error: {e}")

    def estimate_com (self, histogram, background_bins=10):
        """
        Estimate center of mass. Requires calibration for lifetime conversion.
        This is a simple method that computes the centroid of the histogram.
        This avoids fitting and is suitable for real-time processing.
        """

        # Ensure histogram is a numpy array
        histogram = np.asarray(histogram)
        
        # compute background and subtract it
        background = np.mean(histogram[:background_bins])
        histogram = histogram - background  # Remove baseline if present
        histogram[histogram < 0] = 0

        total = np.sum(histogram)
        if total == 0:
            return -1  # No signal

        # Assume time bins are uniformly spaced; cache the array to avoid per-call allocation
        n = len(histogram)
        if self._time_bins is None or len(self._time_bins) != n:
            self._time_bins = np.arange(n)
        time = self._time_bins
        centroid = np.sum(histogram * time) / total

        # Convert centroid in time units
        com = centroid * self.bin_width

        return com  # in ps
    
    def enable(self):
        """Enable FLIM processing."""
        self.enable_processing = True

    def disable(self):
        """Disable FLIM processing."""
        self.enable_processing = False