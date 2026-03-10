from time import sleep
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np

UPDATE_INTERVAL_SEC = 1  # Interval between count rate updates, in seconds

class CountRateWorker(QObject):
    """Worker thread to fetch count rates from the TT."""

    signal = pyqtSignal(np.ndarray)  # Signal for passing data to the main thread
    finished = pyqtSignal()  # Signal to notify when stopped

    def __init__(self, countrate):
        super().__init__()
        self.running = True  # Flag to control the loop
        self.countrate = countrate


    def run(self):
        """Main loop for acquiring data."""

        while self.running:
            
            data = self.countrate.getDataObject().getFrequencyInstantaneous()
            self.signal.emit(data)  
                
            
            # Sleep for the defined update interval
            sleep(UPDATE_INTERVAL_SEC)  

        # Notify that the worker has stopped
        self.finished.emit()  

    def stop(self):
        
        """Stop the worker thread."""
        self.running = False
