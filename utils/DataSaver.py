import h5py
import numpy as np
from datetime import datetime
import cv2
import os

class DataSaver:
    def __init__(self, base_dir="data"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

class LogSaver(DataSaver):
    
    def save(self, idx_1, idx_2, t, filename="log.txt"):
        path = os.path.join(self.base_dir, filename)

        # merge data
        data = np.column_stack((idx_1, idx_2, t))

        # Save to file with tab delimiter
        np.savetxt(path, data, fmt="%.3f", delimiter="\t", header="Idx1\tIdx2\tTime", comments='')

class VideoSaver(DataSaver):
    def save(self, frames, fps = 50, filename="video.avi"):
        """
        Save video data to AVI file.

        :param frames: List of frames (NumPy arrays).
        :param filename: Optional custom filename. Defaults to video.avi.
        """
        if frames:

            # Generate default filename if not provided
            filepath = os.path.join(self.base_dir, filename)

            # Get frame dimensions
            height, width, layers = frames[0].shape

            # Initialize video writer
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))

            # Write frames to video
            for frame in frames:
                out.write(frame)

            # Release video writer
            out.release()
    
    def log (self, data, filename="video.txt"):
        """
        Save video log data to text file.

        :param data: List of tuples (frame_idx, spot_x, spot_y, spot_r).
        :param filename: Optional custom filename. Defaults to video_log.txt.
        """
        path = os.path.join(self.base_dir, filename)

        # Save to file with tab delimiter
        np.savetxt(path, data, fmt="%d\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%.3f", delimiter="\t", header="Frame Index\tTime\tSpot X\tSpot Y\tSpot Radius\tIdx1\tIdx2", comments='')  

class HistogramSaver(DataSaver):
    def save(self, x, histograms, metadata, filename=None):
        """
        Save histogram data to HDF5 with metadata.

        :param x: 1D NumPy array (Bin indices).
        :param histograms: 2D NumPy array (bins × acquisitions).
        :param metadata: Dictionary containing metadata.
        :param filename: Optional custom filename. Defaults to timestamped filename.
        """
        # Generate default filename if not provided
        if filename is None:
            #timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"histogram.h5"
        
        filepath = os.path.join(self.base_dir, filename)

        with h5py.File(filepath, "w") as f:
            # Save histogram data
            f.create_dataset("x", data=x)
            f.create_dataset("histograms", data=histograms)

            # Save metadata as attributes
            meta_group = f.create_group("metadata")
            for key, value in metadata.items():
                meta_group.attrs[key] = str(value)  # Convert to string for compatibility

        