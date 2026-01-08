from enum import Enum

class ProcessingMode(Enum):
    OFF = 0       # No processing
    NORMAL = 1    # ROI-based processing
    TRACKING = 2  # ROI tracking mode
    DEBUG = 3     # Debug mode
