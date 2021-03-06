import numpy as np
from numpy import fft
import sys

from ring import Ring, AnnotatedRing

class StretchWindow(object):
    def __init__(self, size):
        if not float(np.log2(size)).is_integer():
            raise RuntimeError('StretchWindow size must be a power of two')

        self.size = int(size)
        self.half = int(size / 2.)

        # The hann window function and tremelo compensation (hinv_buf) are copied
        # directly from paulstretch
        hinv_sqrt2    = (1 + np.sqrt(0.5)) * 0.5
        hinv_buf_cos  = np.cos(np.arange(self.half, dtype='float') * 2.0 * np.pi / self.half)
        self.hinv_buf = hinv_sqrt2 - (1.0 - hinv_sqrt2) * hinv_buf_cos
        self.window   = 0.5 - np.cos(np.arange(self.size, dtype='float') * 2.0 * np.pi / (self.size - 1.)) * 0.5

        # We want to be able to apply only the first half of the window to the
        # audio stream. For size = 4 this would look like [0, 0.5, 1, 1]
        self.half_ones = np.ones(self.half)
        self.open_window  = np.concatenate((self.window[:self.half], self.half_ones))
        # We also need to be able to close the previous window. Note that
        # unlike open_window close window is not padded with 'ones'
        self.close_window = self.window[self.half:]

        # If we have a single window size, we can apply the tremolo
        # compensation to the both parts of the sample simultaneously, by
        # multiplying the tremolo curve to the overlapping region after
        # completing the overlap add. However, we do not know what the next
        # window size will be, so here we will apply tremelo compensation to
        # each half of the audio snippit separately.
        self.double_hinv_buf = np.concatenate((self.hinv_buf, self.hinv_buf))


    def hopsize(self, stretch_amount):
        return int(np.floor(self.size * 0.5 / stretch_amount))

stretches = {}
def get_strech(windowsize):
    if windowsize not in stretches:
        stretches[windowsize] = StretchWindow(windowsize)
    return stretches[windowsize]

fade_outs = {}
def get_fade_out(size):
    if size not in fade_outs:
        fade_outs[size] = np.logspace(1, np.finfo(float).eps, size, base=10.) / 10
    return fade_outs[size]

class Stretcher(object):
    """ Given a tap pointer in a Ring buffer, generate the stretched audio
    """

    def __init__(self, tap):
        """
        tap (RingPosition): the starting point where our stretch begins
        """
        self.__in_tap     = tap
        self.__buffer     = Ring(2**16)
        self.__fading_out = False


    def step(self, windowsize, *args, **kwargs):
        results = self.stretch(windowsize, *args, **kwargs)

        return results

    def stretch(self, windowsize, stretch_amount = 4):
        """
        Run paulstretch once from the current location of the tap point
        """
        sw = get_strech(windowsize)
        audio_in = self.__in_tap.get_samples(sw.size)

        # Magnitude spectrum of windowed samples
        mX = np.abs(fft.rfft(audio_in * sw.window))
        # Randomise the phases for each bin between 0 and 2pi
        pX = np.random.uniform(0, 2 * np.pi, len(mX)) * 1j
        # use e^x to Convert our array of random values from 0 to 2pi to an
        # array of cartesian style real+imag vales distributed around the unit
        # circle. Then multiply with magnitude spectrum to rotate the magnitude
        # spectrum around the circle.
        freq = mX * np.exp(pX)
        # Get the audio samples with randomized phase. When we randomized the
        # phase, we changed the waveform so it no longer starts and ends at
        # zero. We will need to apply another window -- however do not know the
        # size of the next window, so instead of applying the full window to
        # our audio samples, we will close the window from the previous step,
        # and open the window on our current samples.
        audio_phased = fft.irfft(freq)
        # counter the tremelo for both halves of the audio snippet
        audio_phased *= sw.double_hinv_buf
        # Open the window to the newly generated audio sample
        audio_phased *= sw.open_window

        # Next we will do the overlap/add with the tail of our local buffer.
        # First, retrive the the samples, apply the closing window
        previous = self.__buffer.recent(sw.half) * sw.close_window

        # overlap add this the newly generated audio with the closing tail of
        # the previous signal
        audio_phased[:sw.half] += previous
        # replace the tail end of the output buffer with the new signal
        self.__buffer.rewind(sw.half)
        self.__buffer.append(audio_phased)
        # The last <sw.half> samples are not valid (the window has not yet
        # been closed). These will be closed the next time we call step.

        # Advance our input tap
        self.__in_tap.advance(sw.hopsize(stretch_amount))

        # append the audio output to our output buffer
        self.__buffer.append(audio_phased)

        return audio_phased[:sw.half]

    def fade_out(self):
        """Begin fading the stretch with each .step() .step should deactivate
    
        Caution: fade_out is currently implemeted in StretchGroup. See:
        https://github.com/CharlesHolbrow/realtime-fft-experiment/issues/4
        """
        self.__fading_out = True

    def activate(self):
        self.__fading_out = False
        self.tap.activate()

    def deactivate(self):
        self.clear()
        self.tap.deactivate()

    @property
    def fading_out(self):
        return self.__fading_out

    @fading_out.setter
    def fading_out(self, val):
        self.__fading_out = bool(val)

    @property
    def tap(self):
        return self.__in_tap

    def clear(self):
        self.__buffer.raw.fill(0.)

class StretchGroup(object):
    def __init__(self, ring, osc_io):

        if not isinstance(ring, AnnotatedRing):
            raise TypeError('Stretch Group requires annotated Ring')

        self.__ring          = ring
        self.__active_taps   = ring.active_taps
        self.__inactive_taps = ring.inactive_taps
        self.__io            = osc_io
        self.stretches       = {}
        self.stretches_list  = []

        self.create_stretcher()
        self.create_stretcher()
        self.create_stretcher()
        self.create_stretcher()


    def create_stretcher(self):
        tap = self.ring.create_tap()
        tap.deactivate()

        stretch = Stretcher(tap)
        self.stretches[tap.name] = stretch
        self.stretches_list.append(stretch)
        return stretch

    def step(self, num_samples):
        """ take a step num_samples long

        num samples must be a in integer multiple of the halfwindowsize calculated here
        """
        exponent = 14 # raise 2 to this power to get windowsize
        windowsize = 2 ** exponent
        num_strech_steps = num_samples / (windowsize / 2)

        results = np.zeros((num_samples, 2)) # should dtype be set explicitly?

        for i, stretcher in enumerate(self.stretches_list):
            tap = stretcher.tap
            name = tap.name
            # make sure that this tap is active before we try to stretch it
            if name not in self.__active_taps:
                continue

            # Get the current position of the fader from touchosc
            stretch_amt = self.__io.fader_state(i)
            answer = np.concatenate([stretcher.step(windowsize, stretch_amt) for j in range(num_strech_steps)])

            if stretcher.fading_out:
                stretcher.fading_out = False
                answer *= get_fade_out(len(answer))
                stretcher.deactivate()
                self.__io.led(i + 1, 0)
            else:
                self.__io.led(i + 1, tap.energy_unit())

            if i in [0, 1, 2]:
                results[:, 0] += answer
            if i in [1, 2, 3]:
                results[:, 1] += answer

        return results

    def get_inactive_stretcher(self):
        """ Return an unused stretcher from this group if one exists. If all
        stretchers are in use, return None.
        """
        if len(self.__inactive_taps) == 0:
            return None
        name = self.__inactive_taps.iterkeys().next()
        return self.stretches[name]

    @property
    def ring(self):
        return self.__ring

