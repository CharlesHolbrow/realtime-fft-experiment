import numpy as np
from numpy import fft

from ring import Ring

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
        # audio stream. For size = 4 this would look like [-1, 0, 1, 1]
        half_ones = np.ones(self.half)
        self.open_window  = np.concatenate((self.window[:self.half], half_ones))
        self.close_window = np.concatenate((half_ones, self.window[self.half:]))

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

class Stretcher(object):
    """ Given a tap pointer in a Ring buffer, generate the stretched audio
    """

    def __init__(self, tap):
        """
        tap (RingPosition): the starting point where our stretch begins
        """
        self.__in_tap   = tap
        self.__previous = np.zeros(16384) # take from the output buffer instead
        self.__buffer   = Ring(2**16)
        # self.__out_tap  = self.__buffer.create_tap()

    def step(self, windowsize, stretch_amount = 4):
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
        # array of cartesian style real*imag vales distributed around the unit
        # circle. Then multiply with magnitude spectrum to rotate the magnitude
        # spectrum around the unit circle. 
        freq = mX * np.exp(pX)
        # Get the audio samples with randomized phase. When we randomized the
        # phase, we changed the waveform so it no longer starts and ends at
        # zero. Now re-window the audio.
        audio_phased = fft.irfft(freq) * sw.window
        # counter the tremelo for both halves of the audio snippet
        audio_phased *= sw.double_hinv_buf
        hs = sw.half
        audio_output = audio_phased[0:hs] + self.__previous[hs:]
        # counter the tremelo
        audio_output *= sw.hinv_buf

        self.__previous = audio_phased
        self.__in_tap.advance(sw.hopsize(4))

        # append the audio output to our output buffer
        self.__buffer.append(audio_output)

        return audio_output
