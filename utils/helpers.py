# =====================================================
# helpers.py
#
# Utility functions
#
# Author: Joao Lagarto
# Date  : 2025/03/11
# =====================================================

import yaml
import PySpin
import sys

def load_config(config_file):
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    return config

def find_cameras ():
    """
    Find cameras connected to the system
    """
    # Retrieve singleton reference to system object
    system = PySpin.System.GetInstance()

    # Retrieve list of cameras from the system
    cam_list = system.GetCameras()

    # get number of cameras connected to the system
    num_cameras = cam_list.GetSize()      

    if num_cameras == 0:

        # Clear camera list before releasing system
        cam_list.Clear()

        # Release system instance
        system.ReleaseInstance()
            
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

    print (detected_cams)    
    return detected_cams
