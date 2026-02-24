import numpy as np
import matplotlib.pyplot as plt
from scipy import signal as scipy_signal
from LoRaTX import LoRa_Tx
from LoRaRX import LoRa_Rx

# Параметры
SF = 10
BW = 125e3
fc = 915e6
Power = 14
message = "Hello World!"

# Частота дискретизации и несущая приёмника
Fs = 10e6
Fc = 921.5e6

# Передача
signalIQ = LoRa_Tx(message, BW, SF, Power, Fs, Fc - fc)
Sxx = 10 * np.log10(np.mean(np.abs(signalIQ)**2))
print(f'Transmit Power   = {Sxx:.2f} dBm')

# Графики
plt.figure(1)
plt.specgram(signalIQ, NFFT=500, Fs=Fs, noverlap=0, cmap='viridis')
plt.title('Spectrogram')
plt.xlabel('Time (s)')
plt.ylabel('Frequency (Hz)')

plt.figure(2)
# Периодограмма (двусторонняя) с помощью scipy
f, Pxx = scipy_signal.periodogram(signalIQ, Fs, return_onesided=False)

# fftshift для центрирования нулевой частоты
f_shift = np.fft.fftshift(f)
Pxx_shift = np.fft.fftshift(Pxx)
plt.plot(f_shift / 1e3, 10 * np.log10(Pxx_shift))  # частота в кГц, dB
plt.title('Power Spectral Density')
plt.xlabel('Frequency (kHz)')
plt.ylabel('PSD (dB/Hz)')
plt.grid(True)

plt.show()

# Приём
message_out = LoRa_Rx(signalIQ, BW, SF, 2, Fs, Fc - fc)
print(f'Message Received = {message_out}')