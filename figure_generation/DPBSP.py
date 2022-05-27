import numpy as np
from pathlib import Path
import matplotlib.pylab as plt
import tikzplotlib

unipolar_arr = np.array([1, 1, 0, 0, 1, 0, 1])
bipolar = 2*unipolar_arr - 1

bit_duration = 1
amplitude_scaling_factor = bit_duration/2  # This will result in unit amplitude waveforms
freq = 1/bit_duration  # carrier frequency
samples_per_bit = 200
n_samples = samples_per_bit * len(unipolar_arr)
time = np.linspace(0, len(unipolar_arr), n_samples)

print(n_samples)

dd = np.repeat(unipolar_arr, samples_per_bit)  # replicate each bit Nsb times
bb = np.repeat(bipolar, samples_per_bit)  # Transpose the rows and columns

phase = np.zeros((int(samples_per_bit)))
for i in range(len(unipolar_arr) - 1):
    phase_shift = np.pi if unipolar_arr[i+1] == 1 else 0
    phase = np.concatenate((phase, np.ones((int(samples_per_bit))) * phase[i*int(samples_per_bit)] + phase_shift))

waveform = np.sqrt(2*amplitude_scaling_factor/bit_duration) * np.cos(2*np.pi * freq * time)  # no need for np.dot to perform scalar-scalar multiplication or scalar-array multiplication
bpsk_w = np.sqrt(2*amplitude_scaling_factor/bit_duration) * np.cos(2*np.pi * freq * time + phase)

f, ax = plt.subplots(3, 1, sharex=True)
ax[0].plot(time, dd)
ax[0].axis([0, len(unipolar_arr), -0.3, 1.3])
ax[0].set_title("Bit stream")
ax[0].set_ylabel('Bit')

ax[1].plot(time, waveform)
ax[1].axis([0, len(unipolar_arr), -1.3, 1.3])
ax[1].set_title("Carrier Signal")
ax[1].set_ylabel('Amplitude')

ax[2].plot(time, bpsk_w)
ax[2].axis([0, len(unipolar_arr), -1.3, 1.3])
ax[2].set_title("Modulated signal")
ax[2].set_ylabel('Amplitude')

ax[2].set_xlabel('Symbols')
f.tight_layout()

tikzplotlib.save( str(Path(__file__).parent) + "/figures/D-BPSK.tex")

plt.show()

