import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtCore import QTimer
import pyqtgraph as pg
import TimeTagger

# Constants
LASER_CH = 2
DETECTOR_CH1 = 3
SYNC_CH = 4
N_MEASUREMENTS = 15000
INTEGRATION_TIME_PS = int(.1e10)  # 100 ms in picoseconds
BIN_WIDTH = 200
N_BINS = 256
UPDATE_INTERVAL_MS = 1

class RealTimePlot(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_timetagger()
        self.setup_timer()

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
        self.tagger.setConditionalFilter(trigger=[DETECTOR_CH1, SYNC_CH], filtered=[LASER_CH])

        self.delayed_channel = TimeTagger.DelayedChannel(self.tagger, SYNC_CH, INTEGRATION_TIME_PS)
        pixel_end_ch = self.delayed_channel.getChannel()

        self.gated_channel = TimeTagger.GatedChannel(self.tagger, DETECTOR_CH1, SYNC_CH, pixel_end_ch)
        self.gated_detector_ch = self.gated_channel.getChannel()

        self.Histogram = TimeTagger.TimeDifferences(
            tagger=self.tagger,
            click_channel=self.gated_detector_ch,
            start_channel=LASER_CH,
            next_channel=SYNC_CH,
            binwidth=BIN_WIDTH,
            n_bins=N_BINS,
            n_histograms=N_MEASUREMENTS
        )

    def setup_timer(self):
        """Configure the QTimer for periodic data updates."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(UPDATE_INTERVAL_MS)

    def update_plot(self):
        """Fetch new data and update the plot."""

        # get current measurement index
        idx = self.Histogram.getHistogramIndex()

        data = self.Histogram.getData()[idx]
        self.curve.setData(self.x, data)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RealTimePlot()
    window.show()
    sys.exit(app.exec_())