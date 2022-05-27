import matplotlib.pyplot as plt
import numpy as np
import scipy.signal
from lib import LoRa, LoRa_plot
from bitarray import bitarray
from bitarray.util import ba2int

SF = 7
CR = 1

bit_data = bitarray('1001001001110101000101010110100011110010111000')

data = 95
win_size = 1024*3

Br = 100e3      # Bandbreite des ausgesendeten Down-Chirps [Hz]
fs = 20e6        # Abtastfrequenz [Hz]
Tp = 1e-3      # Dauer des Up-Chirps [s]
#Tp = 2**SF/Br

fc = Br/2

print("Abtastintervall: %.2f ms" % (1/fs*1e6) )   # Abtastintervall in Entfernungsrichtung [s]
print("Chirprate kr: %.2f MHz/s" % (Br/Tp/1e6) )

print("T_symbol: %.3f ms" % (Tp * 1e3) )
print("R_b: %.3f" % (Br/2**SF*SF) )
print("R_b_code: %.3f" % (SF* (4/(4+CR))/(2**SF/Br) ) )

sr = LoRa.get_chirp(Br, Tp, fs, 0, fc, include_last=True)
sr_ref = LoRa.get_reference_chirp(Br, Tp, fs, fc, include_last=True)
sr_ref_start = LoRa.get_reference_chirp(Br, Tp, fs, fc, include_last=False)
sr_symbol = LoRa.get_chirp(Br, Tp, fs, data / 2**SF, fc, include_last=True)
tau = LoRa.get_time(Tp, fs, include_last=True)

# generate signal from bit data
for i in range( len(bit_data)% SF ):
    bit_data.append(0)

time_signal = LoRa.get_chirp(Br, Tp, fs, 0, fc, include_last=False)
freq_signal = LoRa.get_frequency(Br, Tp, fs, 0, fc)

# start pattern for LoRa
# 6 normal and 2 inverse chirps
# for i in range(6):
#     time_signal = np.concatenate(( time_signal, sr.copy()))
# time_signal = np.concatenate(( time_signal, sr_ref.copy()))
# time_signal = np.concatenate(( time_signal, sr_ref.copy()))


# calculate data and encode in chirp
for i in range(int(len(bit_data)/SF)-1):
    # slice bit array
    data = ba2int(bit_data[i*SF:(i+1)*SF])
    print("data %i: %i" % (i, data))
    time_signal = np.concatenate(( time_signal, LoRa.get_chirp(Br, Tp, fs, data / 2**SF, fc) ))
    freq_signal = np.concatenate(( freq_signal, LoRa.get_frequency(Br, Tp, fs, data / 2**SF, fc) ))

time_signal = np.concatenate(( time_signal, LoRa.get_chirp(Br, Tp, fs, data / 2**SF, fc, include_last=True) ))
freq_signal = np.concatenate(( freq_signal, LoRa.get_frequency(Br, Tp, fs, data / 2**SF, fc, include_last=True) ))


# --- Textausgabe und grafische Ausgabe ---------------
# LoRa_plot.plot_time_spectrogram(sr, tau, win_size, fc, Br, 1, "No shift")
# LoRa_plot.plot_time_spectrogram(sr_ref, tau, win_size, fc, Br, 2, "Reference")
# LoRa_plot.plot_time_spectrogram(sr_symbol, tau, win_size, fc, Br, 3, "Symbol")

time_vector = LoRa.get_time( (len(time_signal)-1)/len(sr_ref_start) * Tp, fs, include_last=True)

LoRa_plot.plot_spectrogram(time_signal, time_vector, win_size, fc, Br, 4, "Signal")

# calculate corelation
time_corr = LoRa.get_reference_chirp(Br, Tp, fs, fc, include_last=False)

for i in range( int(len(time_signal)/len(sr_ref)) - 1):
    time_corr = np.concatenate((time_corr, LoRa.get_reference_chirp(Br, Tp, fs, fc, include_last=False)))
time_corr = np.concatenate((time_corr, LoRa.get_reference_chirp(Br, Tp, fs, fc, include_last=True)))

LoRa_plot.plot_spectrogram(time_signal*time_corr, time_vector, win_size, fc, Br, 10, "In time domain correlated Signal")


sr_compr_norm = LoRa.correlate(sr_symbol, sr_ref)
d = np.linspace(0, 2**SF, len(sr_compr_norm))
LoRa_plot.plot_correlation_single(d, sr_compr_norm, 11, 'In frequency domain correlated Signal')


# freq = LoRa.get_frequency(Br, Tp, fs, 0, fc)
# LoRa_plot.plot_frequency(freq, tau, fc, Br, 12, "frequency")
LoRa_plot.plot_frequency(freq_signal, time_vector, fc, Br, 13, "frequency")

plt.show()