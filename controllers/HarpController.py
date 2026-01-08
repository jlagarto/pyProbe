from instruments.Harp import HarpDevice

class HarpController:

    def __init__(self, port):
        self.device = HarpDevice(port)
        self.active = False

    def start(self):
        """Connect to Harp."""
        self.device.connect()
        self.active = True
        self.enable(state=True)

    def enable (self, state: bool):
        """ Enable/Disable Harp output """
        if self.active:
            self.device.set_mode(state)

    def set_detectors(self, state: int):
        """ Enable/Disable detectors """
        if self.active:
            self.device.set_detectors(state)

    def set_laser_frequency (self, frequency: int):
        """ Set laser frequency in Hz """
        if self.active:

            # mapping from combobox index to frequency index as per LaserFrequency Enum    
            map_frequency = [0, 1, 2, 4, 8]
            self.device.set_laser_frequency(map_frequency[frequency])

    def set_laser_intensity (self, intensity: int):
        """ Set laser intensity from 0 to 255 """
        if self.active:

            # make sure it is an integer
            try:
                intensity = int(intensity)
            except ValueError:
                intensity = 0

            # make sure it is in range
            if intensity < 0:
                intensity = 0

            if intensity > 255:  
                intensity = 255
            
            self.device.set_laser_intensity(intensity)

    def set_laser_state (self, state: bool):
        """ Enable/Disable laser output """
        if self.active:
            if state:
                self.device.set_laser_frequency(1)  # enable laser with default frequency
            else:
                self.device.set_laser_frequency(0)  # disable laser

    def set_measurement_trigger (self):
        """ Set clock function for measurement trigger """
        if self.active:
            self.device.set_clk2_fnc()

    def set_camera_trigger (self):
        """ Set clock function for camera trigger """
        if self.active:
            self.device.set_clk1_fnc()

    def get_laser_intensity (self):
        """ Get current laser intensity """
        if self.active:
            return self.device.get_laser_intensity()
        return 0

    def get_laser_frequency (self):
        """ Get current laser frequency in Hz """
        if self.active:
            return self.device.get_laser_frequency()
        return 0
    
    def stop(self):
        """ Disconnect from Harp """
        self.active = False
        self.device.disconnect()