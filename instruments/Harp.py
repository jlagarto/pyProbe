# =====================================================
# Harp.py
#
# Low-level interface to the Harp device
#
# Author: Joao Lagarto
# Date  : 2025/039/22
# =====================================================


from harp.protocol import OperationMode
from harp.devices.laserdrivercontroller import LaserDriverController, FrequencySelect, Bncs

class HarpDevice:
    def __init__(self, port: str):
        self.port = port
        self.device = None
        self.running = False

    def connect(self):
        """Open connection to device."""
        if self.device is None:
            self.device = LaserDriverController(self.port)
            self.device.__enter__()  # start context
            #self.device.info()

    def disconnect(self):
        """Close connection to device."""
        if self.device:
            self.device.__exit__(None, None, None)
            self.device = None

    def is_connected(self):
        """Check if device is connected."""
        return self.device
    
    def set_mode(self, state: bool):
        """ Enable/Disable Harp output """
        if self.device:
            self.device.set_mode(OperationMode.ACTIVE) if state else self.device.set_mode(OperationMode.STANDBY)

    def get_laser_intensity (self):
        """ Get current laser intensity """
        if self.device:
            return self.device.read_laser_intensity()
        return 0
    
    def get_laser_frequency (self):
        """ Get current laser frequency in Hz """
        if self.device:
            return self.device.read_laser_frequency_select()
        return 0

    def set_laser_frequency (self, frequency: int):
        """ Set laser frequency in Hz """
        if self.device:
            self.device.write_laser_frequency_select(FrequencySelect(frequency))  # select internal frequency

    def set_laser_intensity (self, intensity: int):
        """ Set laser intensity from 0 to 255 """
        if self.device:
            self.device.write_laser_intensity(intensity)  # set intensity (0-100%)

    def set_laser_state (self, state: bool):
        """ Enable/Disable laser output """
        if self.device:
            self.device.write_laser_frequency_select(FrequencySelect.NONE)  # select internal frequency
            # self.device.write_laser_state(0)  # enable/disable laser

    def set_detectors(self, state: int):
        """ Enable/Disable detectors """
        if self.device:
            self.device.write_spad_switch(state)  # enable/disable detectors

    def set_clk1_fnc (self):
        """ Set parameters of bnc1 clock output """
        
        if self.device:

            # clock on-period in ms
            self.device.write_bnc1_on(2)

            # clock off-period in ms
            self.device.write_bnc1_off(18)

            # clock number of pulses, 0 for continuous
            self.device.write_bnc1_pulses(0)

            # clock frequency 
            self.device.write_bncs_state(Bncs.BNC1 | Bncs.BNC2)  # enable bnc1 output

    def set_clk2_fnc (self):
        """ Set parameters of bnc2 clock output """
            
        if self.device:

            # clock on-period in ms
            self.device.write_bnc2_on(18)

            # clock off-period in ms
            self.device.write_bnc2_off(2)

            # clock number of pulses, 0 for continuous
            self.device.write_bnc2_pulses(0)

            # set up delay
            self.device.write_bnc2_tail(0)  # delay in ms

            # clock frequency 
            self.device.write_bncs_state(Bncs.BNC1 | Bncs.BNC2)  # enable bnc1 output