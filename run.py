import sys
import sounddevice as sd
import numpy as np
import matplotlib.pyplot as plt
from scipy.fftpack import fft, ifft, fftshift
import logging

from ring import Ring, AnnotatedRing
from stretcher import Stretcher

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
blocksize = 2**13
# latency (float): latency in seconds
latency = None



try:
    cumulated_status = sd.CallbackFlags()
    size = 128 * 1024 * 120
    print 'duration in seconds: {0}'.format(float(size) / samplerate)
    input_buffer  = AnnotatedRing(size / 512, 512)
    tap           = input_buffer.create_tap()
    stretcher     = Stretcher(tap)
    tap.index     = input_buffer.index_of(-8392 + 1)
    print 'valid tap buffer length in seconds: {0}'.format(float(tap.valid_buffer_length) / samplerate)
    shape           = (0,0)
    frames_elapsed  = 0
    samples_elapsed = 0


    def callback(indata, outdata, frames, time, status):
        global cumulated_status
        global shape
        global ring
        global stretcher
        global frames_elapsed
        global samples_elapsed
        cumulated_status |= status

        # np.shape(indata) will equal (frames, in_channels) where frames is the
        # number of samples provided by sounddevice, and in_channels is the
        # number of input channels.

        if shape != np.shape(indata):
            shape = np.shape(indata)
            print 'input shape: {0}'.format(np.shape(indata))

        # How many frames have we processed
        samples_elapsed += shape[0]
        seconds_elapsed = float(samples_elapsed) / samplerate
        frames_elapsed += 1

        # raise 2 to this power to get windowsize
        exponent = 15
        windowsize = 2 ** exponent
        number_to_fill = blocksize / (windowsize / 2)

        # sys.stdout.write('window: {0} seconds elapsed: {1}. \r'.format(windowsize, seconds_elapsed))
        # sys.stdout.flush()
        samples_to_next_transient = tap.samples_to_next_transient
        if samples_to_next_transient is not None:
            sys.stdout.write("{0} \r".format(float(samples_to_next_transient) / samplerate))
            sys.stdout.flush()

        audio_input = indata.flatten()
        input_buffer.append(audio_input)

        results = np.concatenate([stretcher.step(2**14, 8) for i in range(1)])
        outdata[:] = np.column_stack((results, results))


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
    print 'error caught:'
    print type(e).__name__ + ': ' + str(e)
    sys.exit()

