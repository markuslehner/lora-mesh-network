import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import scipy.signal

def plot_time_spectrogram(sr, tau, win_size, f_center, band, fig_num, name):
    fs = 1/(tau[1]-tau[0])
    f, t, Zxx = scipy.signal.stft(np.real(sr), fs=fs, nperseg=win_size)

    fig, axs = plt.subplots(1, 2, constrained_layout=True, num=fig_num)
    fig.suptitle(name)
    axs[0].plot(tau*1e3, np.real(sr), color='b', linewidth=2)
    axs[0].grid(True )
    axs[0].tick_params(axis="both", direction="in")
    axs[0].set_xlim([0, tau[-1]*1e3]) 
    axs[0].set_title('Chirp')     
    axs[0].set_xlabel('Time t in ms')          
    axs[0].set_ylabel('Amplitude')       

    axs[1].pcolormesh(t*1e3, f, np.abs(Zxx), shading='gouraud')
    axs[1].set_title('STFT')
    axs[1].tick_params(axis="both", direction="in")
    axs[1].set_ylim(((f_center-1.2*(band/2)), f_center+1.2*(band/2)))
    axs[1].set_ylabel('Frequency f in Hz')
    axs[1].set_xlabel('Time t in ms')

def plot_correlation_single(d, sr_compr, fig_num, name):

    fig, axs = plt.subplots(1, 1, constrained_layout=True, num=fig_num)
    fig.suptitle(name)  

    axs.plot(d, sr_compr)
    axs.tick_params(axis="both", direction="in")
    axs.grid(True )
    axs.set_ylabel('Correlation for data in decimal')
    axs.set_xlabel('data in binary')

def plot_spectrogram(sr, tau, win_size, f_center, band, fig_num, name):
    fs = 1/(tau[1]-tau[0])
    f, t, Zxx = scipy.signal.stft(np.real(sr), fs=fs, nperseg=win_size)

    fig, axs = plt.subplots(1, 1, constrained_layout=True, num=fig_num)
    fig.suptitle(name)  

    axs.pcolormesh(t*1e3, f, np.abs(Zxx), shading='gouraud')
    axs.set_title('STFT Magnitude')
    axs.tick_params(axis="both", direction="in")
    axs.set_ylim(((f_center-1.2*(band/2)), f_center+1.2*(band/2)))
    axs.set_ylabel('Frequency $f$ in Hz')
    axs.set_xlabel('Time $t$ in ms')

def plot_frequency(freq, tau, f_center, band, fig_num, name):

    fig, axs = plt.subplots(1, 1, constrained_layout=True, num=fig_num)
    fig.suptitle(name)  

    axs.plot(tau*1e3, freq, '.', color='b', ms=0.5, )
    axs.set_title('Momentanous frequency')
    axs.tick_params(axis="both", direction="in")
    axs.set_ylim(((f_center-1.2*(band/2)), f_center+1.2*(band/2)))
    axs.set_ylabel('Frequency $f$ in Hz')
    axs.set_xlabel('Time $t$ in ms')

def plot_time_spectrogram_analytical(sr, freq, tau, f_center, band, fig_num, name):

    fig, axs = plt.subplots(1, 2, constrained_layout=True, num=fig_num)
    fig.suptitle(name)
    axs[0].plot(tau*1e3, np.real(sr), color='b', linewidth=2)
    axs[0].grid(True )
    axs[0].tick_params(axis="both", direction="in")
    axs[0].set_xlim([0, tau[-1]*1e3]) 
    axs[0].set_title('Time signal')     
    axs[0].set_xlabel('Time t in ms')          
    axs[0].set_ylabel('Amplitude y in V')       

    axs[1].plot(tau*1e3, freq*1e-3, '.', color='b', ms=0.5, )
    axs[1].set_title('Momentanous frequency')
    axs[1].grid(True )
    axs[1].tick_params(axis="both", direction="in")
    axs[1].set_xlim([0, tau[-1]*1e3]) 
    axs[1].set_ylim(((f_center*1e-3-1.2*(band*1e-3/2)), f_center*1e-3+1.2*(band*1e-3/2)))
    axs[1].set_ylabel('Frequency $f$ in kHz')
    axs[1].set_xlabel('Time $t$ in ms')

def plot_time_spectrogram_analytical_shifted(sr, freq, tau, f_center, band, shift, fig_num, name):

    fig, axs = plt.subplots(1, 2, constrained_layout=True, num=fig_num)
    fig.suptitle(name)
    axs[0].plot(tau*1e3, np.real(sr), color='b', linewidth=2)
    axs[0].grid(True )
    axs[0].tick_params(axis="both", direction="in")
    axs[0].set_xlim([0, tau[-1]*1e3]) 
    axs[0].set_title('Time signal')     
    axs[0].set_xlabel('Time t in ms')          
    axs[0].set_ylabel('Amplitude y in V')       

    axs[1].plot(tau*1e3, freq*1e-3, '.', color='b', ms=0.5, )
    axs[1].set_title('Momentanous frequency')
    axs[1].grid(True )
    axs[1].tick_params(axis="both", direction="in")
    axs[1].set_xlim([0, tau[-1]*1e3]) 
    axs[1].set_ylim(((f_center*1e-3-1.2*(band*1e-3/2)), f_center*1e-3+1.2*(band*1e-3/2)))
    axs[1].set_ylabel('Frequency $f$ in kHz')
    axs[1].set_xlabel('Time $t$ in ms')

    # plot the arrows

    print((f_center + band/2)*1e-3*shift)
    print(tau[-1]*1e3*(1-shift))

    axs[1].add_patch(patches.FancyArrowPatch(
                            (0, 0),
                            (0, (f_center + band/2)*1e-3*shift),
                            arrowstyle='->',
                            mutation_scale=15,
                            color='darkorange',
                            lw=2
                        ))

    axs[1].add_patch(patches.FancyArrowPatch(
                            (0, 0),
                            (tau[-1]*1e3*(1-shift), 0),
                            arrowstyle='->',
                            mutation_scale=15,
                            color='darkorange',
                            lw=2
                        ))

def plot_data_frequency(freq, data, tau, num_data, Tp, f_center, band, SF, bit_data, fig_num, name):

    fig, axs = plt.subplots(1, 1, constrained_layout=True, num=fig_num)   

    axs.plot(tau, freq*1e-3, '.', color='b', ms=0.5)
    axs.set_title('Momentanous frequency')
    axs.grid(True )
    axs.tick_params(axis="both", direction="in")
    axs.set_xlim([0, tau[-1]]) 
    axs.set_ylim(((f_center*1e-3-1.2*(band*1e-3/2)), f_center*1e-3+1.2*(band*1e-3/2)))
    axs.set_xticks(np.arange(num_data+1)*Tp)
    axs.set_xticklabels(np.arange(num_data+1))
    axs.set_yticks(np.arange(5) * (band/4) * 1e-3)
    axs.set_ylabel('Frequency $f$ in kHz')
    axs.set_xlabel('Time in $n \cdot T_s$')

    for i in range(0, num_data):

        data_idx = i* int(len(data)/(num_data))
        x_start = i*Tp
        x_end = i*Tp
        y_start = 0
        y_end = (band*1e-3) * (data[data_idx] / 2**SF)

        if(i > 0):
            axs.add_patch(patches.FancyArrowPatch(
                            (x_start, y_start),
                            (x_end, y_end),
                            arrowstyle='->',
                            mutation_scale=15,
                            color='darkorange',
                            lw=2
                        ))
            axs.text(x_start + Tp*0.1, y_end*0.4, "%i" % (int(data[data_idx])), rotation= 0 , ha='center', va='center')  

        axs.text(x_start + 0.5*Tp , 1e-3*(f_center + band*0.53), "%s" % (str(bit_data[i*SF:(i+1)*SF])[9:-1]), rotation= 0, ha='center', va='center')  


def plot_data_frequency_2(freq, data, tau, num_data, Tp, f_center, band, SF, bit_data, fig_num, name):

    fig, axs = plt.subplots(2, 1, constrained_layout=True, num=fig_num)
    # fig.suptitle(name)
    axs[0].plot(tau, data, '.', color='b', ms=0.5)
    axs[0].grid(True )
    axs[0].tick_params(axis="both", direction="in")
    axs[0].set_xlim([0, tau[-1]]) 
    axs[0].set_xticks(np.arange(num_data+1)*Tp)
    axs[0].set_xticklabels([])
    axs[0].set_yticks(np.arange(5) * (2**SF/4))
    axs[0].set_title('Data')              
    axs[0].set_ylabel('Data in decimal')       

    axs[1].plot(tau, freq*1e-3, '.', color='b', ms=0.5)
    axs[1].set_title('Momentanous frequency')
    axs[1].grid(True )
    axs[1].tick_params(axis="both", direction="in")
    axs[1].set_xlim([0, tau[-1]]) 
    axs[1].set_ylim(((f_center*1e-3-1.2*(band*1e-3/2)), f_center*1e-3+1.2*(band*1e-3/2)))
    axs[1].set_xticks(np.arange(num_data+1)*Tp)
    axs[1].set_xticklabels(np.arange(num_data+1))
    axs[1].set_yticks(np.arange(5) * (band/4) * 1e-3)
    axs[1].set_ylabel('Frequency $f$ in kHz')
    axs[1].set_xlabel('Time in $n \cdot T_s$')

    for i in range(0, num_data):

        data_idx = i* int(len(data)/(num_data))
        x_start = i*Tp
        x_end = i*Tp
        y_start = 0
        y_end = (band*1e-3) * (data[data_idx] / 2**SF)

        if(i > 0):
            axs[1].add_patch(patches.FancyArrowPatch(
                            (x_start, y_start),
                            (x_end, y_end),
                            arrowstyle='->',
                            mutation_scale=15,
                            color='darkorange',
                            lw=2
                        ))
            axs[1].text(x_start + Tp*0.1, y_end*0.4, "%i" % (int(data[data_idx])), rotation= 0 , ha='center', va='center')  

        axs[0].text(x_start + 0.5*Tp , int(data[data_idx]) + 2**SF*0.05, "%s" % (str(bit_data[i*SF:(i+1)*SF])[9:-1]), rotation= 0, ha='center', va='center')  


