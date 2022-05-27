import numpy as np

def get_reference_chirp(band, T_symbol, f_sample, f_center=500e3, include_last=False) -> np.array:

    tau = get_time( T_symbol, f_sample, include_last=include_last)            # Entfernungszeit-Vektor von -Tp/2 bis +Tp/2 -> verwenden sie np.arange(..)
    kr = band/T_symbol                              # Chirp-Rate [Hz/s]

    sr_ref = np.exp(2j*np.pi*(f_center +band/2 - kr/2*tau) * tau)
    return sr_ref

def get_chirp(band, T_symbol, f_sample, shift, f_center=500e3, include_last=False) -> np.array:
   
    tau = get_time( T_symbol, f_sample, include_last=include_last)          # Entfernungszeit-Vektor von -Tp/2 bis +Tp/2 -> verwenden sie np.arange(..)
    kr = band/T_symbol                              # Chirp-Rate [Hz/s]

    sr = np.exp(2j*np.pi*(f_center -band/2 + kr/2*tau) * tau)

    sr_symbol = np.zeros((len(sr)), dtype=complex)

    idx_1 = int((1-shift)*len(sr))
    idx_2 = int(shift*len(sr))
    if(idx_2 + idx_1 < len(sr_symbol)):
        if(idx_1 > idx_2):
            idx_1 += 1
        else:
            idx_2 += 1
    sr_symbol[0:idx_1] = sr[idx_2:]
    sr_symbol[idx_1:] = sr[0:idx_2]

    return sr_symbol

def correlate(sr_symbol, sr_ref) -> np.array:
    # freq multiplikation
    sr_f =      np.fft.fft(sr_symbol)    # Chirp-Signal sr mittels FFT in den Frequenzbereich transformieren
    sr_f_ref =       np.fft.fft(sr_ref)  # Chirp-Signal sr_ref mittels FFT in den Frequenzbereich transformieren
    sr_f_compr =      sr_f*sr_f_ref      # Entfernungs-Kompression im Frequenbereich durchführen
    sr_compr =         np.fft.ifft(sr_f_compr)     # Komprimiertes Signal mittels IFFT zurück in den Zeitbereich transformieren

    return np.flip( np.abs(sr_compr) / np.max(np.abs(sr_compr)) )

def get_time(T_symbol, f_sample, include_last=False) -> np.array:
    return np.linspace(0, T_symbol, num=int(T_symbol*f_sample)+include_last , endpoint=include_last) 

def get_frequency(band, T_symbol, f_sample, shift, f_center=500e3, include_last=False) -> np.array:

    tau = get_time( T_symbol, f_sample, include_last=include_last)             # Entfernungszeit-Vektor von -Tp/2 bis +Tp/2 -> verwenden sie np.arange(..)
    kr = band/T_symbol   

    freq = (f_center -band/2 + kr*tau)
    freq_symbol = np.zeros((len(freq)))

    idx_1 = int((1-shift)*len(freq))
    idx_2 = int(shift*len(freq))
    if(idx_2 + idx_1 < len(freq_symbol)):
        if(idx_1 > idx_2):
            idx_1 += 1
        else:
            idx_2 += 1
    freq_symbol[0:idx_1] = freq[idx_2:]
    freq_symbol[idx_1:] = freq[0:idx_2]

    return freq_symbol
