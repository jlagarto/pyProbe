#
# =====================================================
# CameraController.py
#
# Controller for FLIR camera using PySpin
#
# Author: Joao Lagarto
# Date  : 2024/07/22
# =====================================================

from instruments.Camera import Camera
import PySpin 

class CameraController:

    def __init__(self, deviceID, img_width, img_height, exposure_time, trigger_mode, offset):
        """
        Class constructor. Initialize camera. Needs to find the correct pointer for given device id
        """

        # camera instantiation
        self.system = PySpin.System.GetInstance()

        # Retrieve list of cameras from the system
        cams = self.system.GetCameras()

        # initialize camera Pointer
        camPtr = None

        # find camera with given device ID
        for i, cam in enumerate(cams):

            # map device nodes and get device ID    
            nodemap_tldevice = cam.GetTLDeviceNodeMap()
            node_device_ID = PySpin.CStringPtr(nodemap_tldevice.GetNode('DeviceID'))

            if PySpin.IsReadable(node_device_ID) and node_device_ID.GetValue() == deviceID:
                camPtr = cam
                break

        # pointer to camera
        if camPtr is not None:

            # instantiation
            self.cam = Camera(camPtr)

            # init camera
            self.cam.open()

            # configure trigger and other acquisition parameters
            self.configure(img_width, img_height, exposure_time, trigger_mode, offset)

   

    def configure (self, img_width, img_height, exposure_time, trigger_mode, offset):
        """
        Configure parameters
        """

        # configure exposure time
        self.cam.config_exposure(exposure_time)

        # set trigger mode to Acquisition start and software
        self.cam.config_trigger(trigger_mode)

        # set image format
        self.cam.config_format(img_width, img_height, offset)
        
        # set white balance        
        self.cam.config_white_balance()
        
        # set throughput        
        self.cam.set_throughput()

    
    def set_trigger_mode(self, mode):
        """
        Set camera trigger mode
        """
        if not self.cam.config_trigger(mode):
            return False


    def set_exposure_time (self, exposure_time):
        """
        Set exposure time
        """
        self.cam.config_exposure(exposure_time)

    def start_camera_stream (self):
        """
        Start acquisition
        """
        self.cam.start()

    def acquire (self):

        return self.cam.acquire()
    
    def stop_camera_stream (self):
        """
        kill thread
        """
        # stop camera
        self.cam.stop()

        # stop reset trigger
        #self.cam.reset_trigger()

    def error(self):

        return self.cam.error()

    def __del__ (self):
        """
        class destructor, close camera connection
        """
        # close connection
        self.cam.close()

        # delete camera object
        del self.cam

        # release cam instance
        self.system.ReleaseInstance()


