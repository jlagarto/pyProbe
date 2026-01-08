import sys
import numpy as np
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import pyqtSignal, QTimer
import pyqtgraph as pg
import TimeTagger
from time import sleep, time

# Constants
LASER_CH = 2
DETECTOR_CH1 = 3
SYNC_CH = 4
N_MEASUREMENTS = 15000
INTEGRATION_TIME_MS = 10  # in milliseconds
INTEGRATION_TIME_PS = int(INTEGRATION_TIME_MS * 1e9)  # in picoseconds
BIN_WIDTH = 200
N_BINS = 256
UPDATE_INTERVAL_MS = 1  # Interval for update, 200 ms

class DataWorker(threading.Thread):
    # Signal to notify the main thread to update the plot
    def __init__(self, histogram, signal):
        super().__init__()
        self.histogram = histogram
        self.signal = signal
        self.daemon = True  # Daemon thread will exit when the program ends
        self.last_idx = None    # idx initialization

    def run(self):
        """Fetch data at regular intervals and emit signal for updating the plot."""
        while True:
            idx = self.histogram.getHistogramIndex()

            # If the index has changed, emit the signal.
            # -1 is returned if the index is not available
            if idx != self.last_idx and idx != -1:
                data = self.histogram.getData()[self.last_idx]
                self.signal.emit(data)  # Emit data to the main thread

                # check if total number of measurements was reached
                
                #print (self.histogram.ready())
                

            # update the last index
            self.last_idx = idx    
            sleep(UPDATE_INTERVAL_MS / 1000)  # Sleep for the defined update interval (converted to seconds)

class RealTimePlot(QMainWindow):
    data_signal = pyqtSignal(np.ndarray)  # Signal for passing data to the main thread

    def __init__(self):
        super().__init__()
        self.timestamps = []
        self.start_time = None  # Initialize start time
        self.setup_ui()
        self.setup_timetagger()
        #self.setup_worker()

    def setup_ui(self):
        """Set up the GUI layout."""
        self.setWindowTitle("Real-Time Data Acquisition")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout()
        self.central_widget.setLayout(layout)

        self.plot_widget = pg.PlotWidget()
        layout.addWidget(self.plot_widget)

        self.x = np.linspace(0, N_BINS - 1, N_BINS)
        self.y = np.zeros(N_BINS)
        self.curve = self.plot_widget.plot(self.x, self.y, pen='y')

    def setup_timetagger(self):
        """Initialize TimeTagger hardware and measurement setup."""
        self.tagger = TimeTagger.createTimeTagger()

        # delay laser channel by 30 ns to adjust the decay curve to the start of the acquisition window
        self.tagger.setInputDelay(LASER_CH, 30000)

        # adjust laser trigger level
        self.tagger.setTriggerLevel(LASER_CH, .25)

        # Set conditional filter to filter out events on the detector channel that are not triggered by the laser channel
        self.tagger.setConditionalFilter(trigger=[DETECTOR_CH1], filtered=[LASER_CH])

        # Set up delayed channel for integration time definition
        self.delayed_channel = TimeTagger.DelayedChannel(self.tagger, SYNC_CH, INTEGRATION_TIME_PS)
        pixel_end_ch = self.delayed_channel.getChannel()

        # Set up gated channel for the detector channel - this is required for integration time definition
        self.gated_channel = TimeTagger.GatedChannel(self.tagger, DETECTOR_CH1, SYNC_CH, pixel_end_ch)
        self.gated_detector_ch = self.gated_channel.getChannel()

        # Set up histogram of photon arrival times
        self.Histogram = TimeTagger.TimeDifferences(
            tagger=self.tagger,
            click_channel=self.gated_detector_ch,
            start_channel=LASER_CH,
            next_channel=SYNC_CH,
            binwidth=BIN_WIDTH,
            n_bins=N_BINS,
            n_histograms=N_MEASUREMENTS
        )

        # get histogram time array in ps
        self.x = self.Histogram.getIndex()

    def setup_worker(self):
        """Initialize and start the worker thread."""
        self.data_signal.connect(self.update_plot)  # Connect the signal to the slot
        self.worker = DataWorker(self.Histogram, self.data_signal)
        self.worker.start()  # Start the worker thread

    def update_plot(self, data):
        """Update the plot with the new data."""
        if self.start_time is None:
            self.start_time = time()

        # Calculate elapsed time in milliseconds
        elapsed_ms = int((time() - self.start_time) * 1000)
        self.timestamps.append(elapsed_ms)
        # print(f"Elapsed time: {elapsed_ms} ms")
        self.curve.setData(self.x, data)
        total_counts = np.sum(data)
        # print(f"Total counts: {total_counts}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RealTimePlot()
    window.show()
    sys.exit(app.exec_())
