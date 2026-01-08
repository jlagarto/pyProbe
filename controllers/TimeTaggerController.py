# =====================================================
# TimeTaggerController.py
#
# Controller for TimeTagger acquisition
#
# Author: Joao Lagarto
# Date  : 2025/03/11
# =====================================================

from instruments.TimeTagger import TimeTagger

class TimeTaggerController:

    def __init__(self, laser_ch, detector_ch1, detector_ch2, external_trigger, delay_sync, delay_ch1, delay_ch2, sync_trigger_level, external_trigger_level, deadtime_ch1, deadtime_ch2):
        """Initialize Time Tagger and set up default parameters for the acquisition."""
        self.tagger = TimeTagger()

        if self.tagger is None:
            raise Exception("TimeTagger not found. Please check the connection.")

        # set properties
        self.laser_ch = laser_ch
        self.detector_ch1 = detector_ch1
        self.detector_ch2 = detector_ch2
        self.external_trigger = external_trigger

        # set sync delay
        self.set_delay(self.laser_ch, delay_sync)

        # set ch1 and ch2 delays
        self.set_delay(self.detector_ch1, delay_ch1)
        self.set_delay(self.detector_ch2, delay_ch2)    

        # set dead time on channels
        self.tagger.set_dead_time(self.detector_ch1, 50000)
        self.tagger.set_dead_time(self.detector_ch2, 50000)

        # set sync trigger level
        self.set_trigger_level(self.laser_ch, sync_trigger_level)

        # set external sync trigger
        self.set_trigger_level(self.external_trigger, external_trigger_level)

        # set filtering
        #self.tagger.set_conditional_filter(trigger=[self.detector_ch1, self.detector_ch2], filtered=[])
        
    def set_delay(self, channel, delay):
        """Set delay on input channel"""
        self.tagger.set_delay(channel, delay)

    def set_trigger_level(self, channel, level):
        """Set trigger level on input channel"""
        self.tagger.set_trigger_level(channel, level)

    def set_detection_gate(self, detection_ch, integration_time_ps):
        """Set up detection channel gate"""

        name = {self.detector_ch1: 'ch1', self.detector_ch2: 'ch2'}.get(detection_ch, 'unknown')

        delayed_channel = self.tagger.set_delayed_channel(name, self.external_trigger, integration_time_ps)
        return self.tagger.set_gated_channel(name, detection_ch, self.external_trigger, delayed_channel)

    def start_measurement(self, detector_channel, laser_channel, external_trigger, binwidth, n_bins, n_histograms):
        """Start histogram measurement."""
        return self.tagger.create_histogram(detector_channel, laser_channel, external_trigger, binwidth, n_bins, n_histograms)
    
    def get_count_rate(self, channels):
        """Get count rate on input channels.""" 
        return self.tagger.get_count_rate(channels)

    def get_status(self):
        """Get TimeTagger status."""
        self.tagger.get_status()

    def __del__(self):
        """Destructor for TimeTaggerController."""
        del self.tagger
