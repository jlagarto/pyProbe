import threading
from time import sleep
from PyQt5.QtCore import QObject
from PyQt5.QtCore import pyqtSignal
import numpy as np

UPDATE_INTERVAL_SEC = 1  # Interval for update, in ms

class CountRateWorker(QObject, threading.Thread):
    """Worker thread to fetch count rates from the TT."""
    
    signal = pyqtSignal(np.ndarray)  # Signal for passing data to the main thread
    finished = pyqtSignal()  # Signal to notify when stopped

    def __init__(self, countrate):
        super().__init__()
        self.running = True  # Flag to control the loop
        self.countrate = countrate
        self.daemon = True  # Daemon thread will exit when the program ends


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
