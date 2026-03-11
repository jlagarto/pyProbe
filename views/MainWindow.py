# =====================================================
# MainWindow.py
#
# UI controller for the main window
#
# Author: Joao Lagarto
# Date  : 2025/03/11
# =====================================================

from PyQt5 import uic, QtGui
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QShortcut
from PyQt5.QtCore import Qt, QThread, QTimer, QIODevice
from PyQt5.QtSerialPort import QSerialPort, QSerialPortInfo
import PySpin

from workers.DataWorker import DataWorker  
from workers.CountRateWorker import CountRateWorker   
from workers.CameraWorker import CameraWorker   
from workers.FLIMWorker import FLIMWorker   

from controllers.TimeTaggerController import TimeTaggerController
from controllers.CameraController import CameraController
from controllers.HarpController import HarpController
from utils.DataSaver import *
from utils.ProcessingMode import ProcessingMode
import numpy as np
import math
from time import time, monotonic
from datetime import datetime
import collections
import traceback
import os

class MainWindow(QMainWindow):

    
    def __init__(self, config):
        super().__init__()

         # Load UI dynamically
        uic.loadUi("views/MainWindow.ui", self)

        self._config = config

        # properties
        self.cam = None
        self.metadata = None
        self.acquisition_start_time = 0
        self.acquisition_stop_time = 0
        self.acquisition_time = 0
        self.acquisition_time_track = 0
        self.in_acquisition = False
        self.enable_curves = True
       
        # read config file
        self._read_configs()

        # setup default values
        self._setup_defaults()

        # setup threads and workers
        self._setup_workers()
        
        # setup connect actions
        self._connect_actions()

        # setup plot
        self._setup_plot()

        # setup hardware
        self._setup_hardware()

        # setup keyboard shortcuts
        self._setup_shortcuts()

        # Show message indefinitely (until cleared or overwritten)
        self.statusBar().showMessage("Ready")

    # ===================================================================== #
    # UI configuration and setup
    # ===================================================================== #
    def _connect_actions(self):
        """ Connect UI actions to methods."""

         # Connect buttons
        self.acquisition_start_button.clicked.connect(self.start_measurement)
        self.acquisition_stop_button.clicked.connect(self.stop_thread)
        self.save_data_button.clicked.connect(self.save_data)
        self.capture_background_button.triggered.connect(self.capture_image_background)
        self.reset_background_button.triggered.connect(self.reset_image_background)
        self.snapshot_button.clicked.connect(self.take_snapshot)

        # Connect controllers
        self.no_bins_ctrl.valueChanged.connect(self.set_number_of_bins)
        self.number_of_measurements_ctrl.valueChanged.connect(self.set_number_of_measurements)
        self.integration_time_ctrl.valueChanged.connect(self.set_integration_time)
        self.sync_delay_ctrl.valueChanged.connect(self.set_sync_delay)  
        self.delay_ch1_ctrl.valueChanged.connect(self.set_ch1_delay)  
        self.delay_ch2_ctrl.valueChanged.connect(self.set_ch2_delay)  
        self.bin_width_ctrl.valueChanged.connect(self.set_bin_width)  
        self.camera_on.currentTextChanged.connect(self.toggle_camera)
        self.exposure_time_ctrl.valueChanged.connect(self.set_exposure_time)
        self.white_balance_ctrl.valueChanged.connect(self.set_white_balance)
        self.trigger_mode_ctrl.currentTextChanged.connect(self.set_trigger_mode)
        self.image_processing_ctrl.currentTextChanged.connect(self.enable_image_processing)
        self.laser_power_ctrl.valueChanged.connect(self.set_laser_intensity)
        self.laser_enable_ctrl.toggled.connect(self.set_laser_interlock)
        self.laser_power_toggle.toggled.connect(self.set_laser_intensity)
        self.detectors_ctrl.currentTextChanged.connect(self.set_detectors)
        self.update_curves_ctrl.toggled.connect(self.set_curves_update)
        self.holdout_time_ctrl.valueChanged.connect(self.set_holdout_time)
        self.led_power_ctrl.valueChanged.connect(self.set_led_brightness)
        self.led_enable_ctrl.toggled.connect(self.toggle_led)
        self.acquisition_mode_ctrl.currentTextChanged.connect(self.set_acquisition_mode)

    def _read_configs(self):
        """Read configuration file and set initial values"""

        # time trigger channels
        self.laser_trigger = self._config["time_tagger"]["laser_sync"]
        self.detector1_trigger = self._config["time_tagger"]["detector_1"]
        self.detector2_trigger = self._config["time_tagger"]["detector_2"]
        self.external_trigger = self._config["time_tagger"]["external_sync"]

        # set properties
        self.led_power = self._config["led"]["power"]
        self.led_enable = self._config["led"]["enable"]
        self.laser_power = self._config["laser"]["power"]
        self.laser_enable = self._config["laser"]["enable"]
        self.number_of_bins = self._config["time_tagger"]["acquisition"]["number_of_bins"]
        self.bin_width = self._config["time_tagger"]["acquisition"]["bin_width"]
        self.integration_time_ms = self._config["time_tagger"]["acquisition"]["integration_time"]
        self.integration_time_ps = int (self.integration_time_ms * 1e9)
        self.sync_delay_ps = self._config["time_tagger"]["acquisition"]["sync_delay"]
        self.ch1_delay_ps = self._config["time_tagger"]["acquisition"]["ch1_delay"]
        self.ch2_delay_ps = self._config["time_tagger"]["acquisition"]["ch2_delay"]
        self.deadtime_ch1 = self._config["time_tagger"]["acquisition"]["ch1_deadtime"]
        self.deadtime_ch2 = self._config["time_tagger"]["acquisition"]["ch2_deadtime"]
        self.sync_trigger_level = self._config["time_tagger"]["acquisition"]["sync_trigger_level"]
        self.external_sync_trigger_level = self._config["time_tagger"]["acquisition"]["external_sync_trigger_level"]
        self.number_of_measurements = self._config["time_tagger"]["acquisition"]["number_of_measurements"]
        self.holdout_time = self._config["time_tagger"]["acquisition"]["holdout_time"]
        self.default_data_folder = self._config["default_data_folder"]

        # camera properties
        self.camera_device_id = self._config["camera"]["device_id"]
        self.camera_format_width = self._config["camera"]["format"]["width"]
        self.camera_format_height = self._config["camera"]["format"]["height"]
        self.camera_exposure_time = self._config["camera"]["exposure_time"]
        self.camera_enable = self._config["camera"]["enable"]
        self.camera_offset = self._config["camera"]["offset"]
        self.camera_trigger_mode = self._config["camera"]["trigger_mode"]

    def _setup_workers(self):
        """Setup threads and workers."""
        
        self.data_thread = None
        self.data_worker = None
        self.count_rate_worker = None
        self.count_rate_thread = None
        self.camera_worker = None
        self.camera_thread = None   
        self.flim_worker = None

    def _setup_defaults (self):
        """Setup default values for controls."""
        self.led_power_ctrl.setValue(self.led_power)
        self.laser_power_ctrl.setValue(self.laser_power)
        self.laser_enable_ctrl.setChecked(self.laser_enable)
        self.exposure_time_ctrl.setValue(self.camera_exposure_time)
        self.camera_on.setCurrentIndex(self.camera_enable)
        self.integration_time_ctrl.setValue(self.integration_time_ms)
        self.number_of_measurements_ctrl.setValue(self.number_of_measurements)
        self.no_bins_ctrl.setValue(self.number_of_bins)
        self.bin_width_ctrl.setValue(self.bin_width)
        self.sync_delay_ctrl.setValue(self.sync_delay_ps)
        self.delay_ch1_ctrl.setValue(self.ch1_delay_ps)
        self.delay_ch2_ctrl.setValue(self.ch2_delay_ps)
        self.trigger_mode_ctrl.setCurrentText(self.camera_trigger_mode)
        self.update_curves_ctrl.setChecked(True)
        self.holdout_time_ctrl.setValue(self.holdout_time)
        
    def _setup_plot(self):
        """Setup the plot widget."""
        # Access existing plotWidget
        self.curve_ch1 = self.plot_widget.plot([], [], pen="b")  
        self.curve_ch2 = self.plot_widget.plot([], [], pen="g")
        self.plot_widget.setLogMode(y=True)

    def _setup_hardware(self):
        """Setup hardware controllers."""
        # Initialize TimeTagger 
        try:
            self.setup_timetagger()
            self.init_timetagger = True
        except Exception as e:
            self.show_alert("Error", f"TimeTagger not found. Please check the connection.\n{e}")
            #return
        
         # start count rate worker
        try:
            self.start_count_rate_worker()       
        except Exception as e:
            self.show_alert( "Error", f"Failed to start count rate worker thread.\n{e}")
                        
        # Initialize Camera
        try:
            # search cameras to populate dropdown
            self.cameras_available = self.find_cameras()
            if self.cameras_available is not None:
                self.camera_device.addItems(self.cameras_available)

            self.toggle_camera()
        except Exception as e:
            self.cam = None
            self.show_alert("Error", f"Camera not found. Please check the connection.\n{e}")
            
       
        # initialize Harp controller
        try:
            self.setup_harp()

            # enable laser
            self.set_laser_interlock()

        except Exception as e:
            self.harp = None
            self.show_alert( "Error", f"Failed to start controller unit.\n{e}")

        # Initialize Serial
        try:
            self.setup_serial()
        except Exception as e:
            self.show_alert("Error", f"Serial setup failed: {e}")

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        
        # F5 / start measurement
        shortcut_start_measurement = QtGui.QKeySequence(Qt.Key.Key_F5)
        QShortcut(shortcut_start_measurement, self).activated.connect(self.start_measurement)

        # F9 / stop measurement
        shortcut_stop_measurement = QtGui.QKeySequence(Qt.Key.Key_F9)
        QShortcut(shortcut_stop_measurement, self).activated.connect(self.stop_thread)

        # CTRL+s / save data
        shortcut_save_date = QtGui.QKeySequence(Qt.CTRL + Qt.Key.Key_S)
        QShortcut(shortcut_save_date, self).activated.connect(self.save_data)

    # ===================================================================== #
    # Serial communications with NeoPixel  
    # ===================================================================== #
    def setup_serial(self):
        """Setup serial port without a separate thread."""
        self.serial = QSerialPort()
        
        # Get port from config or default (e.g., COM3 or /dev/ttyUSB0)
        port_name = self._config.get("arduino_port", "COM6") 
        self.serial.setPortName(port_name)
        self.serial.setBaudRate(QSerialPort.Baud9600)
        
        # CONNECT SIGNAL: This is the key. 
        # The 'read_from_arduino' function is ONLY called when data arrives.
        self.serial.readyRead.connect(self.read_from_arduino)

        # Open the port
        if self.serial.open(QIODevice.ReadWrite):
            print(f"Serial port {port_name} opened successfully.")
            # Defer initial command: Arduino resets on DTR and needs ~2 s to boot
            QTimer.singleShot(2000, self.toggle_led)
        else:
            self.show_alert("Serial Error", f"Could not open {port_name}")

    def read_from_arduino(self):
        """Called automatically when Arduino sends data."""
        while self.serial.canReadLine():
            # Read line, decode bytes to string, strip whitespace
            data = self.serial.readLine().data().decode("utf-8").strip()
            print(f"Received from Arduino: {data}")  # For debugging
            
            # Do whatever you need with the data
            self.statusBar().showMessage(f"LED: {data}", 3000) 

    def write_to_arduino(self, command):
        """Call this to send data."""
        if self.serial.isOpen():
            # Ensure newline if Arduino expects it
            if not command.endswith('\n'):
                command += '\n'
            self.serial.write(command.encode("utf-8"))
            self.serial.flush()
            print (f"Sent to Arduino: {command.strip()}")  # For debugging
        else:
            self.show_alert("Serial Error", "Serial port not open!")

    # ===================================================================== #
    # UI setters and functional methods  
    # ===================================================================== #
    def find_cameras (self):
        """Search for available cameras."""
        
        # Retrieve singleton reference to system object
        self.system = PySpin.System.GetInstance()

        # Retrieve list of cameras from the system
        cam_list = self.system.GetCameras()

        # get number of cameras connected to the system
        num_cameras = cam_list.GetSize()      

        if num_cameras == 0:

            # Clear camera list before releasing system
            cam_list.Clear()

            # Release system instance
            self.system.ReleaseInstance()
            
            return None
        
        detected_cams = {}

        # iterate over detected cameras in the system
        for i, cam in enumerate(cam_list):
                
            # map device nodes and get device ID    
            nodemap_tldevice = cam.GetTLDeviceNodeMap()
            node_device_ID = PySpin.CStringPtr(nodemap_tldevice.GetNode('DeviceID'))

            if PySpin.IsReadable(node_device_ID):

                device_ID = node_device_ID.GetValue()
                detected_cams[device_ID] = cam
            
        return detected_cams

    def set_curves_update(self):
        """Display or hide curves from plot"""
        self.enable_curves = self.update_curves_ctrl.isChecked()

    def set_number_of_measurements(self):
        """Set the number of measurements to acquire."""
        self.number_of_measurements = self.number_of_measurements_ctrl.value()

    def set_number_of_bins(self):
        """Set the number of bins for the histogram."""
        self.number_of_bins = self.no_bins_ctrl.value()

    def set_bin_width(self):
        """Set the bin width for the histogram."""
        self.bin_width = self.bin_width_ctrl.value()

    def set_holdout_time(self):
        """Set the holdout time before starting acquisition."""
        self.holdout_time = self.holdout_time_ctrl.value()

    def enable_image_processing(self):
        """Enable or disable image processing."""
        if self.camera_worker is not None:
            self.camera_worker.processing_mode = ProcessingMode(self.image_processing_ctrl.currentIndex())

    def set_acquisition_mode(self):
        """Sets the acquisition mode & adjusts parameters accordingly."""
        
        mode = self.acquisition_mode_ctrl.currentText()

        if mode == "solution":
            # limited number of measurements
            self.number_of_measurements_ctrl.setValue(200)

            # histogram only, that is, no image processing
            self.image_processing_ctrl.setCurrentIndex(0)

            # set holdout time to 0 for solution mode
            self.holdout_time_ctrl.setValue(0)

        else:
            # in vivo/ex vivo mode: unlimited measurements and image processing enabled
            self.number_of_measurements_ctrl.setValue(15000)  # long unreachable value to simulate "unlimited" acquisition

            # enable image processing for in vivo/ex vivo mode
            self.image_processing_ctrl.setCurrentIndex(1)  

            # holdout time can be set by user for in vivo/ex vivo mode, but set it back to default time (as per app configuration)
            self.holdout_time_ctrl.setValue(self._config["time_tagger"]["acquisition"]["holdout_time"])

            # if in vivo, current model for spot tracking appears to be working
            # in ex vivo, the current model does not appear to be working. needs better adjustment for detection of the saturated spot (blue on the outside but the center is white) 
    
    # ===================================================================== #
    # Camera methods
    # ===================================================================== #

    def toggle_camera(self):
        """
        Initialize camera
        """

        # get value
        turn_on = self.camera_on.currentIndex()

        if turn_on and self.cameras_available is not None:

            # get device id
            self.camera_device_id = self.camera_device.currentText()

            # instantiate 
            self.cam = CameraController(self.camera_device_id, self.camera_format_width, self.camera_format_width, self.camera_exposure_time, self.camera_trigger_mode, self.camera_offset)

            # camera frame acquisition thread
            self.start_camera()

            # enable UI elements
            self.enable_cam_UI(True)

        else:

            # stop camera
            if self.cam is not None:
                self.stop_camera()

                # disable UI elements
                self.enable_cam_UI(False)

    def set_trigger_mode(self):
        """
        Set camera trigger mode to selection
        """      
        if self.cam is not None:
            self.cam.set_trigger_mode(self.trigger_mode_ctrl.currentText())

    def set_exposure_time(self):
        """Set the exposure time for the camera."""
        self.camera_exposure_time = self.exposure_time_ctrl.value()
        self.cam.set_exposure_time(self.camera_exposure_time)

    def set_white_balance(self):
        """Set the white balance for the camera.""" 
        
        if self.cam is not None: 
            white_balance_value = self.white_balance_ctrl.value()
            self.cam.set_white_balance(white_balance_value)

    # ===================================================================== #
    # Harp methods
    # ===================================================================== #

    def setup_harp(self):
        """Initialize Harp controller."""
        
        # instantiate harp controller and initiate startup sequence
        self.harp = HarpController(port=self._config["harp"]["port"])
        self.harp.start()

        # set laser frequency to None - laser disabled
        self.harp.set_laser_frequency(0)

        # set measurement trigger clock 
        self.harp.set_measurement_trigger()

        # set camerca trigger clock
        self.harp.set_camera_trigger()

    def set_detectors(self):
        """Enable detectors for the measurement."""

        if self.harp is not None:

            # get dropdown value / index matches state 0/1
            state = self.detectors_ctrl.currentIndex()
            self.harp.set_detectors(state)

    def set_laser_interlock (self):
        """Sets laser on/off"""
        
        if self.harp is not None:
            state = self.laser_enable_ctrl.isChecked()
            self.harp.set_laser_state(state)

    def set_laser_intensity(self):
        """Set the laser intensity."""

        if self.laser_power_toggle.isChecked():
            self.laser_power = self.laser_power_ctrl.value()
        else:
            self.laser_power = 0

        if self.harp is not None:
            self.harp.set_laser_intensity(self.laser_power)

    def toggle_laser_output (self, is_enabled = False):
        """ sets laser output """

        self.laser_power_toggle.setChecked(is_enabled)
        self.set_laser_intensity()

    # ==================================================================== #
    # NeoPixel Ring light serial control
    # ==================================================================== #
    def toggle_led (self):
        """ controls neopixel led state """
        
        if self.led_enable_ctrl.isChecked():
            # write value
            self.write_to_arduino("on")     
            print("LED turned ON")  # For debugging
        else:
            # write value
            self.write_to_arduino("off") 
            print("LED turned OFF")  # For debugging

    def set_led_brightness(self):
        """ controls led pixel intensity """

        # get intensity
        self.led_power = self.led_power_ctrl.value() * 255 / 100

        # write value
        self.write_to_arduino(f"color 0 0 0 {self.led_power}") 


    # ==================================================================== #
    # TimeTagger methods
    # ==================================================================== #

    def setup_timetagger(self):
        """Initialize TimeTagger hardware and measurement setup."""
        self.tagger = TimeTaggerController(self.laser_trigger, self.detector1_trigger, self.detector2_trigger, self.external_trigger, self.sync_delay_ps, self.ch1_delay_ps, self.ch2_delay_ps, self.sync_trigger_level, self.external_sync_trigger_level, self.deadtime_ch1, self.deadtime_ch2)

        # set detection gate for integration time
        self.gated_channel_1 = self.tagger.set_detection_gate(self.detector1_trigger, self.integration_time_ps)
        self.gated_channel_2 = self.tagger.set_detection_gate(self.detector2_trigger, self.integration_time_ps)

    def set_sync_delay(self):
        """Set the sync delay for the detection gate."""
        self.sync_delay_ps = self.sync_delay_ctrl.value()
        self.tagger.set_delay(self.laser_trigger, self.sync_delay_ps)

    def set_ch1_delay(self):
        """Set delay for detection channel 1."""
        self.ch1_delay_ps = self.delay_ch1_ctrl.value()
        self.tagger.set_delay(self.detector1_trigger, self.ch1_delay_ps)

    def set_ch2_delay(self):
        """Set delay for detection channel 2."""
        self.ch2_delay_ps = self.delay_ch2_ctrl.value()
        self.tagger.set_delay(self.detector2_trigger, self.ch2_delay_ps)

    def set_integration_time(self):
        """Set the integration time for the detection gate."""
        self.integration_time_ms = self.integration_time_ctrl.value()
        self.integration_time_ps = int(self.integration_time_ms * 1e9)

        # set detection gate for integration time
        self.gated_channel_1 = self.tagger.set_detection_gate(self.detector1_trigger, self.integration_time_ps)
        self.gated_channel_2 = self.tagger.set_detection_gate(self.detector2_trigger, self.integration_time_ps)
        
    # ==================================================================== #
    # Threads and Workers
    # ==================================================================== #
    
    def stop_thread(self):
        """Stop data acquisition thread """
        if self.data_worker:
            self.data_worker.stop()

    def start_measurement(self):
        """Start the measurement."""
        
        if self.data_thread is not None:
            self.stop_measurement()

        # status bar
        self.statusBar().showMessage("In acquisition")

        # start and stop acquisition buttons
        self.acquisition_start_button.setEnabled(False)
        self.acquisition_stop_button.setEnabled(True)

        # disable integration time and number of measurements input
        self.integration_time_ctrl.setEnabled(False)
        self.number_of_measurements_ctrl.setEnabled(False)

        # toggle laser output
        self.toggle_laser_output(True)
        
        # initialize logging vars
        self.frames = collections.deque(maxlen=3000)  # cap at ~3.3 GB for 600x600 BGR frames
        self.frame_no = 0
        self.frame_idx = []
        self.frame_time = []
        self.spot_x = []
        self.spot_y = []
        self.spot_r = []
        self.time_trace = []
        self.hist_idx_1 = []
        self.hist_idx_2 = []
        self.measurement_idx1 = []
        self.measurement_idx2 = []

        # reset tracking history and frame counter
        if self.camera_worker is not None:
            self.camera_worker.reset_tracking_history()
            self.camera_worker.reset_frame_counter()

        # holdout time before starting acquisition
        if self.holdout_time > 0:
            # Notify user and start countdown
            self.remaining_holdout = int(self.holdout_time)
            self.status_ctrl.setText(f"Starting in {self.remaining_holdout} s...")
            self.status_ctrl.setStyleSheet("background-color: orange;")

            # Create and start a timer for countdown
            self.holdout_timer = QTimer(self)
            self.holdout_timer.timeout.connect(self._update_holdout_countdown)
            self.holdout_timer.start(1000)  # every 1 second
            return  # Exit now — measurement starts automatically when countdown ends

        # If no holdout delay, start measurement immediately
        self._start_actual_measurement()

    def _start_actual_measurement(self):
        """Start the actual measurement after holdout time."""

        # start measurement - ch1
        self.histogram_ch1 = self.tagger.start_measurement(self.gated_channel_1, self.laser_trigger, self.external_trigger, self.bin_width, self.number_of_bins, self.number_of_measurements)
        self.histogram_ch2 = self.tagger.start_measurement(self.gated_channel_2, self.laser_trigger, self.external_trigger, self.bin_width, self.number_of_bins, self.number_of_measurements)

        # x axis
        self.x_ch1 = self.histogram_ch1.getIndex()
        self.x_ch2 = self.histogram_ch2.getIndex()

        # display curves?
        show_curves = self.update_curves_ctrl.isChecked()

        # Initialize DataWorker (runs in a separate thread)
        self.data_worker = DataWorker(self.histogram_ch1, self.histogram_ch2, self.number_of_measurements, show_curves)
        self.flim_worker = FLIMWorker(self.bin_width)

        # Move worker to a new thread
        self.data_thread = QThread()
        self.data_worker.moveToThread(self.data_thread)
            
        # Connect data and processing thread
        self.data_thread.started.connect(self.data_worker.run)
        #self.data_worker.signal.connect(self.update_measurement)  # Connect the signal to the slot
        self.data_worker.signal.connect(self.flim_worker.process)
        self.data_worker.finished.connect(self.data_thread.quit)
        self.data_worker.finished.connect(self.data_worker.deleteLater)
        self.data_worker.finished.connect(self.stop_measurement)  # not required
        self.data_thread.finished.connect(self.data_thread.deleteLater)
        self.flim_worker.processed.connect(self.update_measurement)  # Connect the FLIM worker signal to the slot

        # Connect the DataWorker's signal directly to the CameraWorker's slot.
        # This is thread-safe. Qt handles the data transfer.
        self.data_worker.measurement_index_changed.connect(self.camera_worker.update_measurement_index)

        # Start thread
        self.data_thread.start()
        self.in_acquisition = True

        # initialization
        self.acquisition_start_time = monotonic()

        # keep track of acquisition time
        self.acquisition_time_track = 0
        self.status_ctrl.setStyleSheet("background-color: green;")
        self.status_ctrl.setText("Running")

        # Create and start a timer for countdown
        self.acquisition_timer = QTimer(self)
        self.acquisition_timer.timeout.connect(self._update_acquisition_time)
        self.acquisition_timer.start(1000)  # every 1 second
        
        self.acquisition_counter = 0

    def _update_acquisition_time (self):
        """ Acquisition time display """
        self.acquisition_time_track+=1  # increment one second

        if self.in_acquisition:
            self.status_ctrl.setText(f"Running... {self.acquisition_time_track} s")
        else:
            self.acquisition_timer.stop()
            # change status button
            self.status_ctrl.setStyleSheet("background-color: gray;")
            self.status_ctrl.setText("Idle")
            self.status_ctrl.append(f"(acquisition time {self.acquisition_time_track} s)")


    def _update_holdout_countdown(self):
        """Countdown display and start measurement when done."""
        self.remaining_holdout -= 1
        if self.remaining_holdout > 0:
            self.status_ctrl.setText(f"Starting in {self.remaining_holdout} s...")
        else:
            self.holdout_timer.stop()
            self.status_ctrl.setText("Starting measurement...")
            self._start_actual_measurement()

    def stop_measurement(self):
        """Stop the measurement."""
        
        self.in_acquisition = False

        if self.data_worker:
            self.data_worker.stop()
            self.data_thread.quit()
            self.data_thread.wait()

            self.data_thread = None
            self.data_worker = None


        # stop acquisition time counter
        self.acquisition_stop_time = monotonic()
        self.acquisition_time = self.acquisition_stop_time - self.acquisition_start_time

        # toggle laser output
        self.toggle_laser_output(False)

        # enable save data button
        self.save_data_button.setEnabled(True)

        # start and stop acquisition buttons
        self.acquisition_start_button.setEnabled(True)
        self.acquisition_stop_button.setEnabled(False)

        # enable integration time and number of measurements input
        self.integration_time_ctrl.setEnabled(True)
        self.number_of_measurements_ctrl.setEnabled(True)

        # set acquisition metadata
        self.set_acquisition_metadata()

        # status bar
        self.statusBar().showMessage(f"Acquisition ended with acquisition time of {self.acquisition_time_track} s", 10000)

    def set_acquisition_metadata (self):
        """Set the acquisition metadata."""
        
        self.metadata = {
            "acquisition_date": datetime.now().isoformat(),
            "laser_power": self.laser_power,
            "led_power": self.led_power,
            "exposure_time": self.camera_exposure_time,
            "integration_time": self.integration_time_ms,
            "number_of_measurements": self.number_of_measurements,
            "number_of_bins": self.number_of_bins,
            "bin_width": self.bin_width,
            "sync_delay": self.sync_delay_ps
        }

    def update_measurement(self, idx1, idx2, data, results, timestamp):
        """Update the plot with the new data."""
        
        # increment counter
        self.acquisition_counter += 1

        # display every other curve to reduce lag in UI (seems to be working)
        if self.enable_curves and (self.acquisition_counter % 2 == 0 or self.acquisition_counter == 1):
            self.curve_ch1.setData(self.x_ch1, data[0])
            self.curve_ch2.setData(self.x_ch2, data[1])
        
        # SAVE PRECISE SOURCE TIMESTAMP
        # We calculate the relative time using the source timestamp, not "now()"
        rel_time = timestamp - self.acquisition_start_time

        # save data for log
        self.time_trace.append(rel_time)
        self.hist_idx_1.append(idx1)
        self.hist_idx_2.append(idx2)
      
    def start_count_rate_worker(self):
        """Start the count rate worker."""
        self.count_rate_worker = CountRateWorker(self.tagger.get_count_rate([self.laser_trigger, self.detector1_trigger, self.detector2_trigger, self.external_trigger]))
        self.count_rate_thread = QThread()
        self.count_rate_worker.moveToThread(self.count_rate_thread)
        
        # Connect signals
        self.count_rate_thread.started.connect(self.count_rate_worker.run)
        self.count_rate_worker.signal.connect(self.update_count_rate)
        self.count_rate_worker.finished.connect(self.count_rate_thread.quit)
        self.count_rate_worker.finished.connect(self.count_rate_worker.deleteLater)
        self.count_rate_thread.finished.connect(self.count_rate_thread.deleteLater)

        # Start thread
        self.count_rate_thread.start()

    def update_count_rate(self, data):
        """Update the count rate label."""

        if data is None or data.size == 0:  # For NumPy arrays
            return  # Avoid computation on empty data

        self.update_count_rate_single(self.laser_sync_ctrl, data[0][-1])
        self.update_count_rate_single(self.detector1_count_rate_ctrl, data[1][-1])
        self.update_count_rate_single(self.detector2_count_rate_ctrl, data[2][-1])
        self.update_count_rate_single(self.ext_sync_rate_ctrl, data[3][-1])
        
    def update_count_rate_single (self, ctrl, value):
        """Update the count rate label."""

        if not math.isnan(value):
            ctrl.setText("{:.2e}".format(value))
        else:
            ctrl.setText("Nan")

    def start_camera_worker(self):
        """Start the camera worker."""
        self.camera_worker = CameraWorker(self.cam, ProcessingMode(self.image_processing_ctrl.currentIndex()))
        self.camera_thread = QThread()
        self.camera_worker.moveToThread(self.camera_thread)
        
        # Connect signals
        self.camera_thread.started.connect(self.camera_worker.start)
        self.camera_worker.finished.connect(self.camera_thread.quit)
        self.camera_worker.signal.connect(self.update_frame)

        # Start thread
        self.camera_thread.start()

    def start_camera (self):
        """Start the camera stream."""
        # initialize camera
        self.cam.start_camera_stream()

        # start thread
        self.start_camera_worker()

    def stop_camera(self):
        """Stop the camera stream."""
        
        if self.camera_worker:
            self.camera_worker.stop()
            self.camera_thread.quit()
            self.camera_thread.wait()

            self.camera_thread = None
            self.camera_worker = None

        if self.cam is not None:    
            self.cam.stop_camera_stream()

            # release camera
            self.cam = None

    def update_frame(self, frame_idx, raw_image, cv_image, x, y, r, timestamp, measurement_idx1, measurement_idx2):
        """Update the camera display."""

        # store frames for video. use raw image because it does not contain overlay information
        if self.data_worker is not None and self.data_worker.running:
            self.frames.append(raw_image)

        # Update the camera display
        self.image = QtGui.QImage(cv_image.data, cv_image.shape[1], cv_image.shape[0], QtGui.QImage.Format_RGB888).rgbSwapped()
        self.camera_frame.setPixmap(QtGui.QPixmap.fromImage(self.image))

        # print spot coordinates
        if self.in_acquisition and x is not None and y is not None and r is not None:
            self.spot_x.append(x)
            self.spot_y.append(y)
            self.spot_r.append(r)
            self.frame_no += 1
            self.frame_idx.append(frame_idx)
            self.measurement_idx1.append(measurement_idx1)
            self.measurement_idx2.append(measurement_idx2)
            
            # SAVE PRECISE SOURCE TIMESTAMP
            rel_time = timestamp - self.acquisition_start_time
            self.frame_time.append(rel_time)
                        
            # Print the coordinates to console
            #print(f"Spot Coordinates: ({x}, {y}), Radius: {r}")


    def take_snapshot (self):
        """ Captures current frame and saves it to target folder"""
        if self.camera_worker is not None:
            
            frame = self.camera_worker.capture_single_frame()
            
            if frame is not None:
                # Ask User for Confirmation
                reply = QMessageBox.question(self, "Confirm Snapshot", "Do you want to save this snapshot?", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

                # Proceed only if Yes
                if reply == QMessageBox.Yes:
                    self.save_snapshot(frame)
                else:
                    pass

    def capture_image_background (self):
        """Capture background frame for subtraction with processing frame"""
        if self.camera_worker is not None:
            self.camera_worker.capture_background()

    def reset_image_background (self):
        """Capture background frame for subtraction with processing frame"""
        if self.camera_worker is not None:
            self.camera_worker.reset_background()

    # ===================================================================== #
    # Data saving methods
    # ===================================================================== #

    def save_data(self):
        """Save the data to a file."""

        try:
            # Build folder name
            data_type = self.data_type_ctrl.currentText()
            data_label = self.data_label_ctrl.text().strip()

            # Validate data label
            if not data_label:
                self.show_alert("Error", "Please provide a data label")
                return

            folder_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{data_type}.{data_label}"

            # Open dialog to select a folder
            folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", self.default_data_folder)
            if not folder_path:
                return  # User cancelled dialog

            # Full folder path
            full_folder_path = os.path.join(folder_path, folder_name)

            # Attempt to create folder
            os.makedirs(full_folder_path, exist_ok=True)

            # Save histograms
            try:
                HistogramSaver(full_folder_path).save(self.x_ch1, self.histogram_ch1.getData(), self.metadata, "ch1.h5")
                HistogramSaver(full_folder_path).save(self.x_ch2, self.histogram_ch2.getData(), self.metadata, "ch2.h5")
            except Exception as e:
                self.show_alert("Error Saving Histogram", f"An error occurred while saving histogram data:\n{str(e)}")
                return
            
            # save log 
            try :
                LogSaver(full_folder_path).save(self.hist_idx_1, self.hist_idx_2, self.time_trace)

            except Exception as e:
                self.show_alert("Error Saving Measurement Log", f"An error occurred while saving the measurement log file:\n{str(e)}")

            # Save video if frames are available
            if self.frames:
                try:
                    fps = round(len(self.frames) / self.acquisition_time, 1)
                    VideoSaver(full_folder_path).save(self.frames, fps)
                except Exception as e:
                    self.show_alert("Error Saving Video", f"An error occurred while saving video:\n{str(e)}")
                    return
                
                # save video log (frame idx, spot x, spot y, spot r)
                try:
                    VideoSaver(full_folder_path).log(list(zip(self.frame_idx,self.frame_time, self.spot_x, self.spot_y, self.spot_r, self.measurement_idx1, self.measurement_idx2)))
                except Exception as e:
                    self.show_alert("Error Saving Video Log", f"An error occurred while saving video log:\n{str(e)}")
                    return
                
            self.show_alert("Success", "Data saved successfully!")

        except Exception as e:
            # Catch any unexpected error
            error_details = traceback.format_exc()
            self.show_alert("Unexpected Error", f"An unexpected error occurred:\n{str(e)}\n\nDetails:\n{error_details}")

    def save_snapshot (self, frame):
        """ saves camera snapshot """
        if frame is not None:

            folder_path = QFileDialog.getExistingDirectory(self, "Select Folder", self.default_data_folder)
            if not folder_path:
                return  # User cancelled dialog

            # save image
            ImageSaver(folder_path).save(frame, "snapshot.png")

            # notify succsess
            self.show_alert("Success", "Image successfully saved!")
        else:
            self.show_alert("Error", f"No frame to be saved")

    # ===================================================================== #
    # UI Helpers
    # ===================================================================== #
    def show_alert(self, title="Alert", message="Something happened!"):
        """Show an alert message."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)  # Options: Critical, Warning, Information, Question
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def enable_cam_UI(self, state):
        """Toggle state of widgets associated with the camera"""
        self.exposure_time_ctrl.setEnabled(state)
        self.trigger_mode_ctrl.setEnabled(state)
        self.image_processing_ctrl.setEnabled(state)    
        self.menu_imaging_background.setEnabled(state)

    def closeEvent(self, event):
        """Ensure the thread stops when the window is closed."""
        
        # stop TT acquisition
        self.stop_measurement()
        self.tagger = None

        # stop count rate measurement
        if self.count_rate_worker:
            self.count_rate_worker.stop()
            self.count_rate_thread.quit()
            self.count_rate_thread.wait()

            self.count_rate_thread = None
            self.count_rate_worker = None

        # stop camera
        if self.cam is not None:
            self.stop_camera()

        # stop harp
        if self.harp is not None:
            self.harp.stop()
            self.harp = None

        event.accept()

       