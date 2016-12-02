import numpy as np
from numpy import fft

from ring import Ring

# Parameters for stretching
windowsize  = 32768 / 2
half_windowsize = windowsize / 2
stretch     = 4
source_hopsize = int(np.floor(windowsize * 0.5 / stretch))

print 'hopsize: {0} ({1} seconds), {2} hz'.format(source_hopsize, source_hopsize / 44100., 44100. / source_hopsize)

# The hann window function and tremelo compensation (hinv_buf) are copied
# directly from paulstretch
window       = 0.5 - np.cos(np.arange(windowsize, dtype='float') * 2.0 * np.pi / (windowsize - 1.)) * 0.5
hinv_sqrt2   = (1 + np.sqrt(0.5)) * 0.5
hinv_buf_cos = np.cos(np.arange(half_windowsize, dtype='float') * 2.0 * np.pi / half_windowsize)
hinv_buf     = hinv_sqrt2 - (1.0 - hinv_sqrt2) * hinv_buf_cos

class Stretcher(object):
    """ Given a tap pointer in a Ring buffer, generate the stretched audio
    """

    def __init__(self, tap):
        """
        tap (RingPosition): the starting point where our stretch begins
        """
        self.__tap = tap
        self.previous = np.zeros(windowsize)

    def step(self):
        """
        Run paulstretch once from the current location of the tap point
        """

        audio_in = self.__tap.get_samples(windowsize)

        # Magnitude spectrum of windowed samples
        mX = np.abs(fft.rfft(audio_in * window))
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
        audio_phased = fft.irfft(freq) * window
        hs = half_windowsize
        audio_output = audio_phased[0:hs] + self.previous[hs:windowsize]
        # counter the tremelo
        audio_output *= hinv_buf
        # restrict range to -1, 1
        audio_output[audio_output >  1.0] =  1.0
        audio_output[audio_output < -1.0] = -1.0

        self.previous = audio_phased
        self.__tap.advance(source_hopsize)

        return audio_output

