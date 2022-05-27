import imp
import numpy as np
from pathlib import Path
import matplotlib.pylab as plt
import tikzplotlib

unipolar_arr = np.array([1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1])
bipolar = 2*unipolar_arr - 1

bit_duration = 1
amplitude_scaling_factor = bit_duration/2  # This will result in unit amplitude waveforms
freq = 1/bit_duration/2  # carrier frequency
samples_per_symbol = 200
n_samples = samples_per_symbol * int(len(unipolar_arr)/2)
time = np.linspace(0, len(unipolar_arr), n_samples)
time_symbol = np.linspace(0, len(unipolar_arr)/2, n_samples)

print(n_samples)

dd = np.repeat(unipolar_arr, samples_per_symbol/2)  # replicate each bit Nsb times
bb = np.repeat(bipolar, samples_per_symbol/2)  # Transpose the rows and columns

phase = np.zeros((int(n_samples)))
for i in range(int(len(unipolar_arr)/2)):
    phase_shift = np.pi * unipolar_arr[i*2] + np.pi/2*unipolar_arr[i*2+1]
    phase[i*int(samples_per_symbol):(i+1)*int(samples_per_symbol)] = np.ones((int(samples_per_symbol))) * phase_shift

waveform = np.sqrt(2*amplitude_scaling_factor/bit_duration) * np.cos(2*np.pi * freq * time)  # no need for np.dot to perform scalar-scalar multiplication or scalar-array multiplication
bpsk_w = np.sqrt(2*amplitude_scaling_factor/bit_duration) * np.cos(2*np.pi * freq * time + phase)

f, ax = plt.subplots(3, 1)
ax[0].plot(time_symbol, dd)
ax[0].axis([0, len(unipolar_arr)/2, -0.3, 1.3])
ax[0].set_title("Bit stream")
ax[0].set_ylabel('Bit')
ax[0].set_xticks( np.linspace(0, len(unipolar_arr)/2, len(unipolar_arr)+1) )
ax[0].set_xticklabels( [] )

ax[1].plot(time_symbol, waveform)
ax[1].axis([0, len(unipolar_arr)/2, -1.3, 1.3])
ax[1].set_title("Carrier Signal")
ax[1].set_ylabel('Amplitude')
ax[1].set_xticks( np.linspace(0, len(unipolar_arr)/2, int(len(unipolar_arr)/2)+1) )
ax[1].set_xticklabels( [] )

ax[2].plot(time_symbol, bpsk_w)
ax[2].axis([0, len(unipolar_arr)/2, -1.3, 1.3])
ax[2].set_title("Modulated signal")
ax[2].set_ylabel('Amplitude')
ax[2].set_xticks( np.linspace(0, len(unipolar_arr)/2, int(len(unipolar_arr)/2)+1) )

ax[2].set_xlabel('Symbols')
f.tight_layout()

tikzplotlib.save(str(Path(__file__).parent) + "/figures/QPSK.tex")

plt.show()

