import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from scipy.signal import spectrogram
import sys
import os

# Путь к модулям LoRa
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from lora_Tx import LoRa_Tx
except ImportError:
    # Если импорт не работает, пробуем другой способ
    try:
        from lora_Tx import LoRa_Tx
    except:
        print("Ошибка импорта модуля LoRa_Tx. Проверьте структуру проекта.")
        exit(1)


def rms(x):
    return np.sqrt(np.mean(np.abs(x) ** 2))


def main():
    # Parameters
    SF = 10
    BW = 125e3
    fc = 915e6
    Power = 14

    message = "Hello World!"

    # Sampling
    Fs = 10e6
    Fc = 921.5e6

    # Transmit Signal
    print("Создание LoRa сигнала...")
    try:
        signalIQ, packet = LoRa_Tx(message, BW, SF, Power, Fs, Fc - fc)
        print(f"Сигнал создан. Длина: {len(signalIQ)} отсчетов")
        print(f"Длина пакета: {len(packet)} символов")
    except Exception as e:
        print(f"Ошибка при создании сигнала: {e}")
        import traceback
        traceback.print_exc()
        return

    # Calculate transmit power
    Sxx = 20 * np.log10(rms(signalIQ))  # Power в dB, а не dBm
    print(f'Transmit Power = {Sxx:.2f} dB')

    # Проверка данных сигнала
    print(f"Мин амплитуда: {np.abs(signalIQ).min():.6f}")
    print(f"Макс амплитуда: {np.abs(signalIQ).max():.6f}")
    print(f"Средняя амплитуда: {np.abs(signalIQ).mean():.6f}")

    # Спектрограмма
    print("\nСоздание спектрограммы...")
    plt.figure(figsize=(12, 8))

    try:

        nperseg = min(256, len(signalIQ) // 10)
        noverlap = nperseg // 2

        f, t, Sxx_spec = spectrogram(
            signalIQ,
            fs=Fs,
            window='hann',
            nperseg=nperseg,
            noverlap=noverlap,
            nfft=1024,
            return_onesided=False,
            scaling='spectrum',
            mode='complex'
        )

        # Сдвиг частот для центрированного отображения
        f_shifted = np.fft.fftshift(f)
        Sxx_shifted = np.fft.fftshift(Sxx_spec, axes=0)

        # Масштабирование в дБ
        Sxx_db = 10 * np.log10(np.abs(Sxx_shifted) + 1e-20)

        # Ограничение диапазона
        vmin = np.percentile(Sxx_db, 20)
        vmax = np.percentile(Sxx_db, 99)

        plt.subplot(2, 1, 1)
        im = plt.pcolormesh(t, f_shifted, Sxx_db,
                            shading='gouraud',
                            cmap='viridis',
                            vmin=vmin, vmax=vmax)
        plt.ylabel('Frequency [Hz]')
        plt.xlabel('Time [sec]')
        plt.title('Spectrogram of LoRa Signal')
        plt.colorbar(im, label='Power [dB]')

        print(f"Спектрограмма: f shape: {f.shape}, t shape: {t.shape}, Sxx shape: {Sxx_spec.shape}")

    except Exception as e:
        print(f"Ошибка при создании спектрограммы: {e}")
        # Альтернативный простой график
        plt.subplot(2, 1, 1)
        plt.plot(np.real(signalIQ[:1000]), label='Real')
        plt.plot(np.imag(signalIQ[:1000]), label='Imag')
        plt.xlabel('Sample')
        plt.ylabel('Amplitude')
        plt.title('LoRa Signal (first 1000 samples)')
        plt.legend()
        plt.grid(True)

    # Спектральная плотность
    print("\nСоздание графика спектральной плотности...")
    try:
        # PSD
        f_psd, psd = signal.welch(
            signalIQ,
            fs=Fs,
            window='hann',
            nperseg=1024,
            noverlap=512,
            nfft=2048,
            return_onesided=False,
            scaling='density'
        )

        psd_db = 10 * np.log10(psd + 1e-20)
        f_psd_shifted = np.fft.fftshift(f_psd)
        psd_db_shifted = np.fft.fftshift(psd_db)

        plt.subplot(2, 1, 2)
        plt.plot(f_psd_shifted, psd_db_shifted, linewidth=1)

        # Занятая полоса пропускания
        total_power = np.sum(psd)
        cumulative_power = np.cumsum(psd)

        if total_power > 0:
            lower_idx = np.where(cumulative_power >= 0.005 * total_power)[0]
            upper_idx = np.where(cumulative_power >= 0.995 * total_power)[0]

            if len(lower_idx) > 0 and len(upper_idx) > 0:
                lower_idx = lower_idx[0]
                upper_idx = upper_idx[0]

                occupied_bw = f_psd[upper_idx] - f_psd[lower_idx]

                # Добавление вертикальной линии
                plt.axvline(f_psd_shifted[lower_idx], color='r',
                            linestyle='--', alpha=0.7, linewidth=1)
                plt.axvline(f_psd_shifted[upper_idx], color='r',
                            linestyle='--', alpha=0.7, linewidth=1)

                # Окрашивание области
                mask = (f_psd_shifted >= f_psd_shifted[lower_idx]) & (f_psd_shifted <= f_psd_shifted[upper_idx])
                plt.fill_between(f_psd_shifted[mask], psd_db_shifted[mask],
                                 alpha=0.3, color='gray',
                                 label=f'Occupied BW: {occupied_bw / 1e3:.2f} kHz')

                plt.text(0.05, 0.95, f'OBW: {occupied_bw / 1e3:.2f} kHz',
                         transform=plt.gca().transAxes,
                         verticalalignment='top',
                         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        plt.xlabel('Frequency [Hz]')
        plt.ylabel('PSD [dB/Hz]')
        plt.title('Power Spectral Density')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xlim([-Fs / 2, Fs / 2])

        print(f"PSD: f shape: {f_psd.shape}, psd shape: {psd.shape}")

    except Exception as e:
        print(f"Ошибка при создании PSD: {e}")
        # Альтернативный график
        plt.subplot(2, 1, 2)
        plt.specgram(signalIQ[:10000], NFFT=256, Fs=Fs,
                     noverlap=128, cmap='viridis')
        plt.xlabel('Time')
        plt.ylabel('Frequency')
        plt.title('Alternative Spectrogram')

    # Показать все графики
    plt.tight_layout()
    print("\nОтображение графиков...")
    plt.show()

    # Дополнительные графики
    print("\nСоздание дополнительных графиков...")

    # График 3: Форма сигнала во времени
    plt.figure(figsize=(12, 8))

    plt.subplot(3, 1, 1)
    time_axis = np.arange(len(signalIQ)) / Fs
    plt.plot(time_axis[:2000], np.real(signalIQ[:2000]),
             label='Real', linewidth=0.5)
    plt.plot(time_axis[:2000], np.imag(signalIQ[:2000]),
             label='Imag', linewidth=0.5, alpha=0.7)
    plt.xlabel('Time [s]')
    plt.ylabel('Amplitude')
    plt.title('LoRa Signal (first 2000 samples)')
    plt.legend()
    plt.grid(True, alpha=0.3)

    # График 4: Констелляция
    plt.subplot(3, 1, 2)
    plt.scatter(np.real(signalIQ[:1000]), np.imag(signalIQ[:1000]),
                s=1, alpha=0.5, c='blue')
    plt.xlabel('I')
    plt.ylabel('Q')
    plt.title('Constellation Diagram')
    plt.axis('equal')
    plt.grid(True, alpha=0.3)

    # График 5: Амплитуда сигнала
    plt.subplot(3, 1, 3)
    amplitude = np.abs(signalIQ)
    plt.plot(time_axis[:2000], amplitude[:2000], linewidth=0.5)
    plt.xlabel('Time [s]')
    plt.ylabel('Amplitude')
    plt.title('Signal Amplitude')
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    print("\nГрафики успешно отображены!")


if __name__ == "__main__":
    main()