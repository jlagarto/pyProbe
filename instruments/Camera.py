#
# =====================================================
# CameraSpinnaker.py
#
# Wrapper Class for PySpin, to control FLIR camera
#
# Author: Joao Lagarto
# Date  : 2024/07/22
# =====================================================

import PySpin
import time
class Camera:

    def __init__ (self, cam):
        """
        Class constructor

        :param cam -> camera to run on (CameraPtr)
        """        
        # cameraPtr
        self.cam = cam

        # image frame
        self.frame = None

    def open (self):
        """ 
        Initialize camera
        """
        self.cam.Init()

    def close (self):
        """
        Deinitialize camera
        """
        self.cam.DeInit()

    def start (self):
        """
        Start acquisition
        """
        self.cam.BeginAcquisition()

    def stop (self):
        """
        End acquisition
        """
        self.cam.EndAcquisition()

    def acquire (self):
        """
        Retrieve frame in camera buffer
        """
        try:
            # retrieve next received image
            img = self.cam.GetNextImage(1000)

            # check if acquisition is completed
            if img.IsIncomplete():
            
                raise PySpin.SpinnakerException('Image incomplete with image status %d ...' % img.GetImageStatus())
            else:
                #width = img.GetWidth()
                #height = img.GetHeight()

                # convert image to openCV format and make it public
                self.frame = img.GetNDArray()

                # Images need to be released in order to keep from filling the buffer.
                img.Release()

                return self.frame
                
        except PySpin.SpinnakerException as ex:

            print (ex)
            self.error_msg = ex
            return None
    
    def set_throughput (self):
        """
        Set camera throughput
        """
        try:
            nodemap = self.cam.GetNodeMap()
            # Set the DeviceLinkThroughputLimit to 500 MB/s
            # This is a common setting to prevent buffer overflow
            # and ensure smooth data transfer.
            node_throughput_limit = PySpin.CIntegerPtr(nodemap.GetNode('DeviceLinkThroughputLimit'))
            if PySpin.IsReadable(node_throughput_limit) and PySpin.IsWritable(node_throughput_limit):
                node_throughput_limit.SetValue(500000000)  # Set to 500 MB/s
            else:
                raise PySpin.SpinnakerException('Throughput limit not readable or writable...')

            return True

        except PySpin.SpinnakerException as ex:

            print (ex)
            self.error_msg = ex
            return False

    def config_white_balance(self, value = 1.5):

        try:
            
            nodemap = self.cam.GetNodeMap()

            # image format RGB8 bits
            node_pixel_white_balance = PySpin.CEnumerationPtr(nodemap.GetNode("BalanceWhiteAuto"))
            if PySpin.IsWritable(node_pixel_white_balance):
                node_pixel_white_balance.SetIntValue(False)
            else:
                raise PySpin.SpinnakerException("White Balance enum not writable...")
           
            node_pixel_balance_ratio = PySpin.CFloatPtr(nodemap.GetNode("BalanceRatio"))
            if PySpin.IsWritable(node_pixel_balance_ratio):
                node_pixel_balance_ratio.SetValue(value)
            else:
                raise PySpin.SpinnakerException("Balance ratio not writable...")
           
            return True
                
        except PySpin.SpinnakerException as ex:

            self.error_msg = ex
            return None

    def config_format (self, width_to_set, height_to_set, offset):
        """
        Configure image format
        """

        try:

            nodemap = self.cam.GetNodeMap()

            # image format RGB8 bits
            node_pixel_format = PySpin.CEnumerationPtr(nodemap.GetNode('PixelFormat'))
            if PySpin.IsReadable(node_pixel_format) and PySpin.IsWritable(node_pixel_format):

                # Retrieve the desired entry node from the enumeration node
                node_pixel_format_bgr8 = PySpin.CEnumEntryPtr(node_pixel_format.GetEntryByName('BGR8'))
                if PySpin.IsReadable(node_pixel_format_bgr8):

                    # Retrieve the integer value from the entry node
                    pixel_format_bgr8 = node_pixel_format_bgr8.GetValue()

                    # Set integer as new value for enumeration node
                    node_pixel_format.SetIntValue(pixel_format_bgr8)

                else:
                    raise PySpin.SpinnakerException('Pixel format BGR8 not readable...')

            else:
                raise PySpin.SpinnakerException ('Pixel format not readable or writable...')
                    
            # set image width
            node_width = PySpin.CIntegerPtr(nodemap.GetNode('Width'))
            if PySpin.IsReadable(node_width) and PySpin.IsWritable(node_width):
                node_width.SetValue(width_to_set)
            else:
                raise PySpin.SpinnakerException('Width not readable or writable...')

            # set image height
            node_height = PySpin.CIntegerPtr(nodemap.GetNode('Height'))
            if  PySpin.IsReadable(node_height) and PySpin.IsWritable(node_height):
                node_height.SetValue(height_to_set)
            else:
                raise PySpin.SpinnakerException('Height not readable or writable...')

            # set image offset
            node_offset_x = PySpin.CIntegerPtr(nodemap.GetNode('OffsetX'))
            if PySpin.IsReadable(node_offset_x) and PySpin.IsWritable(node_offset_x):
                node_offset_x.SetValue(offset["x"])
            else:
                raise PySpin.SpinnakerException('Offset X not readable or writable...')
            node_offset_y = PySpin.CIntegerPtr(nodemap.GetNode('OffsetY'))
            if PySpin.IsReadable(node_offset_y) and PySpin.IsWritable(node_offset_y):
                node_offset_y.SetValue(offset["y"])
            else:
                raise PySpin.SpinnakerException('Offset Y not readable or writable...')

            return True
        except PySpin.SpinnakerException as ex:

            self.error_msg = ex
            print(ex)
            return False
        

    def config_exposure (self, exposure_time):
        """ 
        Configure frame exposure time. Exposure time in ms
        """

        try:
            # set manual exposure
            self.cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)

            # set exposure mode
            self.cam.ExposureMode.SetValue(PySpin.ExposureMode_Timed)

            # set exposure time. requires adjustment to us
            self.cam.ExposureTime.SetValue(exposure_time * 1000)

            return True
        
        except PySpin.SpinnakerException as ex:

            print (ex)
            self.error_msg = ex
            return False

    def config_trigger (self, mode):
        """
        Configure camera trigger by SW
        """
        try:

            # Turn off before changes
            self.cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)  

            # set trigger to hardware
            self.cam.TriggerSelector.SetValue(PySpin.TriggerSelector_FrameStart)

            if mode == "hardware":

                # set trigger source
                self.cam.TriggerSource.SetValue(PySpin.TriggerSource_Line2)

            elif mode == "software":

                # set trigger source
                self.cam.TriggerSource.SetValue(PySpin.TriggerSource_Software)
                
                # execute software trigger
                self.cam.TriggerSoftware.Execute()

            else:
                raise PySpin.SpinnakerException('Unknown trigger mode: %s' % mode)

            # Enable trigger mode
            self.cam.TriggerMode.SetValue(PySpin.TriggerMode_On)  # Enable trigger mode


            return True
        
        except PySpin.SpinnakerException as ex:

            #print (ex)
            self.error_msg = ex
            return False
        
    def reset_trigger (self):
        """
        Reset camera trigger mode - set it to 0
        """
        
        try:
            
            nodemap = self.cam.GetNodeMap()

            node_trigger_mode = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerMode'))
            if not PySpin.IsReadable(node_trigger_mode) or not PySpin.IsWritable(node_trigger_mode):
                raise PySpin.SpinnakerException('Unable to disable trigger mode (node retrieval). Aborting...')
                

            node_trigger_mode_off = node_trigger_mode.GetEntryByName('Off')
            if not PySpin.IsReadable(node_trigger_mode_off):
                raise PySpin.SpinnakerException('Unable to disable trigger mode (enum entry retrieval). Aborting...')
                
            node_trigger_mode.SetIntValue(node_trigger_mode_off.GetValue())

            return True

        except PySpin.SpinnakerException as ex:
            print (ex)
            self.error_msg = ex
            return False


    def error (self):

        return self.error_msg