import sys
import sounddevice as sd
import numpy as np
import matplotlib.pyplot as plt
from scipy.fftpack import fft, ifft, fftshift
import logging

from Ring import Ring

# arguments to sd.Stream are here:
# http://python-sounddevice.readthedocs.io/en/0.3.5/index.html?highlight=CallbackFlags#sounddevice.Stream

# input_device (int or str): input device id
input_device = None
# output_device (int or str): output device id
output_device = None
# channels (int): number of channels. is this input or output?
in_channels = 1
out_channels = 2
# dtype: audio data type: float32, int32, int16, int8, uint8
dtype = None
# samplerate (float): sampleing rate. I'm not sure why this is float and not int
samplerate = 44100
# blocksize (int): block size
blocksize = 128
# latency (float): latency in seconds
latency = None


try:
    import sounddevice as sd

    cumulated_status = sd.CallbackFlags()
    size = 128 * 1024
    print 'duration in seconds: {0}'.format(float(size) / samplerate)
    ring_l = Ring(size)
    ring_r = Ring(size)
    shape = (0,0)

    def callback(indata, outdata, frames, time, status):
        global cumulated_status
        global shape
        global ring
        cumulated_status |= status
        # outdata[:] = indata

        if shape != np.shape(indata):
            shape = np.shape(indata)
            print 'input shape: {0}'.format(np.shape(indata))

        ring_l.append(indata.flatten())
        delayed = ring_l.recent(22050)[:blocksize]
        delayed = np.column_stack((delayed, delayed))

        outdata[:] = delayed



    with sd.Stream(device=(input_device, output_device),
                   channels=(in_channels, out_channels),
                   samplerate=samplerate,
                   blocksize=blocksize,
                   dtype=dtype,
                   latency=latency,
                   callback=callback):
        print("#" * 80)
        print("press Return to quit")
        print("#" * 80)
        raw_input()

    if cumulated_status:
        logging.warning(str(cumulated_status))

except KeyboardInterrupt:
    print('KeyboardInterrupt')
    sys.exit()
except Exception as e:
    print type(e).__name__ + ': ' + str(e)
    sys.exit()

