from numpy import *
import matplotlib.pyplot as plt

windowsize = 256
half_windowsize = windowsize / 2


#create Hann window
window=0.5-cos(arange(windowsize,dtype='float')*2.0*pi/(windowsize-1))*0.5

old_windowed_buf=zeros(windowsize)
hinv_sqrt2=(1+sqrt(0.5))*0.5
hinv_buf=hinv_sqrt2-(1.0-hinv_sqrt2)*cos(arange(half_windowsize,dtype='float')*2.0*pi/half_windowsize)

buf = cos((pi * 2 * 3.5 * arange(windowsize) / windowsize))
# buf *= window
# buf = concatenate((buf[half_windowsize:], buf[:half_windowsize]))

plt.plot(buf); plt.show()
meanigless = raw_input('plotted buf') # wait

# get the amplitudes of the frequency components and discard the phases
fft_results = fft.rfft(buf)
freqs = abs(fft_results)
old_angles = angle(fft_results)

# randomize the phases by multiplication with a random complex number with modulus=1
ph = random.uniform(0,2*pi,len(freqs))*1j

plt.plot(freqs); plt.plot(old_angles); plt.plot(imag(ph)); plt.show()
meanigless = raw_input('plotted abs, old_angles and imaginary part of random phase') # wait

freqs = freqs * exp(ph)
plt.plot(abs(freqs)); plt.plot(angle(freqs)); plt.show()
meanigless = raw_input('plotted abs, angles of new spectrum') # wait

buf2 = fft.irfft(freqs)
plt.plot(buf2); plt.plot(buf); plt.show()
meanigless = raw_input('plotted buf2 and original buf') # wait

