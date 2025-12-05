import numpy as np


def loramod(x, SF, BW, fs, Inv=1):
    """LoRa modulation of symbol vector"""
    M = 2 ** SF

    # Check input
    x = np.array(x, dtype=int)
    if np.any(x < 0) or np.any(x > (M - 1)):
        raise ValueError("Symbol values must be in range [0, 2^SF-1]")

    # Symbol constants
    Ts = (2 ** SF) / BW
    Ns = int(fs * M / BW)

    gamma = x / Ts
    beta = BW / Ts

    # Time vector
    time = np.arange(Ns).reshape(-1, 1) / fs

    # Frequency chirp
    freq = np.mod(gamma + Inv * beta * time, BW) - BW / 2

    # Phase integration
    Theta = np.cumsum(freq, axis=0) * (1 / fs) * 2 * np.pi

    # Complex signal
    y = np.exp(1j * Theta).flatten()

    return y


def LoRa_Modulate_Full(packet, SF, Bandwidth, n_preamble, SyncKey, Fs):
    """Construct LoRa packet (preamble + sync header + payload)"""
    # Preamble upchirps
    signal_prmb = loramod((SyncKey - 1) * np.ones(n_preamble), SF, Bandwidth, Fs, 1)

    # Sync upchirp
    signal_sync_u = loramod([0, 0], SF, Bandwidth, Fs, 1)

    # Header downchirp
    signal_sync_d1 = loramod(0, SF, Bandwidth, Fs, -1)

    # Concatenate header
    signal_sync_d = np.concatenate([
        signal_sync_d1,
        signal_sync_d1,
        signal_sync_d1[:len(signal_sync_d1) // 4]
    ])

    # Add sync key to payload message
    signal_mesg = loramod((packet + SyncKey) % (2 ** SF), SF, Bandwidth, Fs, 1)

    # Concatenate LoRa packet
    signal = np.concatenate([signal_prmb, signal_sync_u, signal_sync_d, signal_mesg])

    return signal