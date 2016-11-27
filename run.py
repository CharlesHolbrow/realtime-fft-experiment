import sys
import sounddevice as sd
import numpy as np
import matplotlib.pyplot as plt
from scipy.fftpack import fft, ifft, fftshift

import logging


# input_device (int or str): input device id
input_device = None
# output_device (int or str): output device id
output_device = None
# channels (int): number of channels. is this input or output?
channels = 2
# dtype: audio data type
dtype = None
# samplerate (float): sampleing rate. I'm not sure why this is float and not int
samplerate = None
# blocksize (int): block size
blocksize = None
# latency (float): latency in seconds
latency = None


try:
    import sounddevice as sd

    cumulated_status = sd.CallbackFlags()

    def callback(indata, outdata, frames, time, status):
        global cumulated_status
        cumulated_status |= status
        outdata[:] = indata

    with sd.Stream(device=(input_device, output_device),
                   samplerate=samplerate, blocksize=blocksize,
                   dtype=dtype, latency=latency,
                   channels=channels, callback=callback):
        print("#" * 80)
        print("press Return to quit")
        print("#" * 80)
        input()

    if cumulated_status:
        logging.warning(str(cumulated_status))

except KeyboardInterrupt:
    parser.exit('\nInterrupted by user')
except Exception as e:
    print type(e).__name__ + ': ' + str(e)
    sys.exit()
