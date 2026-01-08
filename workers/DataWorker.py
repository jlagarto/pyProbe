from time import sleep, monotonic
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np 

UPDATE_INTERVAL_MS = 1 

class DataWorker(QObject):
    """Worker thread to acquire data and emit signals to update the UI."""
    
    signal = pyqtSignal(int, int, np.ndarray, float) 
    finished = pyqtSignal() 
    measurement_index_changed = pyqtSignal(int, int)
    
    def __init__(self, histogram_ch1, histogram_ch2, number_of_measurements, show_curves):
        super().__init__()

        self.running = True 
        self.histogram_ch1 = histogram_ch1
        self.histogram_ch2 = histogram_ch2
        self.number_of_measurements = number_of_measurements
        self.show_curves = show_curves
        
        # Track last index for each channel independently
        self.last_idx_ch1 = -1
        self.last_idx_ch2 = -1

    def run(self):
        """Main loop for acquiring data."""
        acquisition_counter = 0
        
        # Local variables for current indices
        idx_ch1 = 0
        idx_ch2 = 0
        
        while self.running:
            # 1. Get current counts
            idx_ch1 = self.histogram_ch1.getHistogramIndex()
            idx_ch2 = self.histogram_ch2.getHistogramIndex()

            # 2. Check for validity (must not be -1)
            valid_ch1 = idx_ch1 != -1
            valid_ch2 = idx_ch2 != -1

            # 3. Check for changes (Has Ch1 moved? Has Ch2 moved?)
            ch1_updated = valid_ch1 and (idx_ch1 != self.last_idx_ch1)
            ch2_updated = valid_ch2 and (idx_ch2 != self.last_idx_ch2)

            # 4. Update if both channels have new data
            if ch1_updated and ch2_updated:
                
                # Determine the "Main" index to emit
                # We use the highest available index to represent current progress
                # (Handle case where one might still be -1 at very start)
                current_max_idx = max(self.last_idx_ch1, self.last_idx_ch2)

                # Safety check: ensure we have at least one valid index to grab data
                if current_max_idx > -1:
                    measurement_time = monotonic()

                    # 5. Retrieve data using the SPECIFIC index for each channel
                    # If a channel hasn't updated, we use its last known valid index
                    i1 = self.last_idx_ch1 if self.last_idx_ch1 != -1 else 0
                    i2 = self.last_idx_ch2 if self.last_idx_ch2 != -1 else 0

                    self.measurement_index_changed.emit(i1, i2)
                    
                    if self.show_curves:
                        h1 = self.histogram_ch1.getData()[i1]
                        h2 = self.histogram_ch2.getData()[i2]
                    else:
                        h1 = np.ndarray([])
                        h2 = np.ndarray([])
                    
                    data = np.array([h1, h2])

                    self.signal.emit(i1, i2, data, measurement_time)  

                    acquisition_counter += 1
                
                    # 6. Exit Condition
                    # Stop if the furthest ahead channel reaches the limit
                    if current_max_idx == (self.number_of_measurements - 1) or (current_max_idx == 0 and acquisition_counter > 1):
                        break
                
                # Update internal trackers
                if ch1_updated: self.last_idx_ch1 = idx_ch1
                if ch2_updated: self.last_idx_ch2 = idx_ch2
            # sleep(UPDATE_INTERVAL_MS / 1000)

        self.finished.emit()  

    def stop(self):
        self.running = False