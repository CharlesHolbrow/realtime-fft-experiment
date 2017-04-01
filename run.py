import sys
import sounddevice as sd
import numpy as np
# import matplotlib.pyplot as plt
from scipy.fftpack import fft, ifft, fftshift
import logging

from ring import Ring, AnnotatedRing
from stretcher import Stretcher, StretchGroup
from stretch_io import StretchIO

print('\nProtip: use "$ python sounddevice -m" do see available audio devices')

# arguments to sd.Stream are here:
# http://python-sounddevice.readthedocs.io/en/0.3.5/index.html?highlight=CallbackFlags#sounddevice.Stream
devices = sd.query_devices()

# input_device (int or str): input device id
input_device = 2 if len(devices) == 3 else None
# output_device (int or str): output device id
output_device = 2 if len(devices) == 3 else None
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


sendIp=("18.85.25.231", 12341)
# sendIp=("26.67.222.83", 12341)

# for d in devices: print(d['name'], d['max_input_channels'], d['max_output_channels'])

input_device = 3
output_device = 1

print('input:  '+ devices[input_device]['name'])
print('output: '+ devices[output_device]['name'])

try:
    cumulated_status = sd.CallbackFlags()
    size = 128 * 1024 * 120 * 16
    print('duration in minutes: {0}'.format(float(size) / samplerate / 60))
    osc_io          = StretchIO(sendIp)
    input_buffer    = AnnotatedRing(size / 512, 512)
    stretch_group   = StretchGroup(input_buffer, osc_io)
    shape           = (0,0)
    frames_elapsed  = 0
    samples_elapsed = 0
    previous_energy = 0
    last_activation = -99999999999

    def button_callback(button, state):
        # touchOSC buttons index at one
        if button > len(stretch_group.stretches_list):
            return

        s = stretch_group.stretches_list[button-1]
        if state == 0:
            print('fade out: {0}'.format(s.tap.name))
            s.fade_out()
        else:
            print('ACTIVATE: {0}'.format(s.tap.name))
            s.tap.index = input_buffer.index - blocksize
            s.activate()


    osc_io.set_toggle_handler(button_callback)


    def audio_callback(indata, outdata, frames, time, status):
        global cumulated_status
        global shape
        global frames_elapsed
        global samples_elapsed
        global previous_energy
        global last_activation
        cumulated_status |= status

        # np.shape(indata) will equal (frames, in_channels) where frames is the
        # number of samples provided by sounddevice, and in_channels is the
        # number of input channels.

        osc_io.step()

        if shape != np.shape(indata):
            shape = np.shape(indata)
            print('input shape: {0}'.format(np.shape(indata)))

        audio_input        = indata.flatten()
        boundaries_crossed = input_buffer.append(audio_input)
        new_transients     = input_buffer.recent_transients(boundaries_crossed)

        if np.any(new_transients) and frames_elapsed > 0:
            boundary_indices   = np.array(input_buffer.recent_block_indices(boundaries_crossed))
            # these are block_indices of transients in the last .append call
            transient_block_indices = boundary_indices[np.nonzero(new_transients)[0]]
            raw_transient_indices   = transient_block_indices * input_buffer.blocksize
            transient_index         = raw_transient_indices[0]

        results = stretch_group.step(blocksize)
        outdata[:] = results
        # sys.stdout.write(' {0:.3f}\r'.format(previous_energy)); sys.stdout.flush()

        # How many frames have we processed
        samples_elapsed += shape[0]
        seconds_elapsed = float(samples_elapsed) / samplerate
        frames_elapsed += 1
        previous_energy = np.sum(outdata ** 2)


    with sd.Stream(device=(input_device, output_device),
                   channels=(in_channels, out_channels),
                   samplerate=samplerate,
                   blocksize=blocksize,
                   dtype=dtype,
                   latency=latency,
                   callback=audio_callback):
        print("\npress Return to quit")
        raw_input()

    if cumulated_status:
        logging.warning(str(cumulated_status))

except KeyboardInterrupt:
    print('KeyboardInterrupt')
    sys.exit()
except Exception as e:
    print('error caught:')
    print(type(e).__name__ + ': ' + str(e))
    sys.exit()

