# =====================================================
# TimeTagger.py
#
# Low-level interface to the Time Tagger
#
# Author: Joao Lagarto
# Date  : 2025/03/11
# =====================================================

import TimeTagger as TT

class TimeTagger:
    def __init__(self):
        """Initialize TimeTagger hardware."""
        self.tagger = TT.createTimeTagger()

        self.gated_channel = {}
        self.delayed_channel = {}

    def set_dead_time(self, channel, dead_time):
        """ Set dead time on input channel """
        self.tagger.setDeadtime(channel, dead_time)

    def set_delay (self, channel, delay):
        """ Set delay on input channel """
        self.tagger.setInputDelay(channel, delay)

    def set_trigger_level (self, channel, level):
        """ Set trigger level on input channel """
        self.tagger.setTriggerLevel(channel, level)

    def set_conditional_filter (self, trigger, filtered):
        """ Set conditional filter to filter out events on the detector channel that are not triggered by the laser channel """
        self.tagger.setConditionalFilter(trigger, filtered)

    def set_delayed_channel (self, name, sync_channel, integration_time):
        """ Set up delayed channel for integration time definition """
        
        self.delayed_channel[name] = TT.DelayedChannel(self.tagger, sync_channel, integration_time)
        return self.delayed_channel[name].getChannel()
    
    def set_gated_channel (self, name, input_channel, start_channel, end_channel):
        """ Set up gated channel for the detector channel - this is required for integration time definition """
        
        self.gated_channel[name] = TT.GatedChannel(self.tagger, input_channel, start_channel, end_channel)
        return self.gated_channel[name].getChannel()
      
    def set_max_counts (self):
        """
        Sets the number of rollovers at which the measurement stops integrating. To integrate infinitely, set the value to 0, which is the default value.
        """

    def create_histogram(self, click_ch, start_ch, next_ch, binwidth, n_bins, n_histograms):
        """Create a histogram measurement."""
        hist = TT.TimeDifferences(
            tagger=self.tagger,
            click_channel=click_ch,
            start_channel=start_ch,
            next_channel=next_ch,
            binwidth=binwidth,
            n_bins=n_bins,
            n_histograms=n_histograms,
        )

        #hist = TT.Histogram(self.tagger, click_channel=click_ch, start_channel=start_ch, binwidth=binwidth, n_bins=n_bins)

        # set maximum number of rollovers
        # hist.setMaxCounts(1)

        return hist
    
    def get_count_rate (self, channels): 
        """ Get count rate on input channels """
        return TT.FrequencyCounter(self.tagger, channels, 1e12, 1e12, 1000)
    
    def get_status (self):
        """ Get TimeTagger status """
        print (self.tagger.getConfiguration())

    def __del__(self):
        """
        Destructor, free TimeTagger resources
        """
        TT.freeTimeTagger(self.tagger)
        del self.tagger 