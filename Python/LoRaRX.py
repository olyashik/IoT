import numpy as np
import scipy.signal as scipy_signal
import scipy.integrate as integrate

# Вспомогательные битовые функции (аналог de2bi / bi2de MATLAB)
def de2bi(num, width):
    return [(num >> i) & 1 for i in range(width)]

def bi2de(bits):
    num = 0
    for i, b in enumerate(bits):
        num |= (b << i)
    return num

# Функции модуляции/демодуляции (необходимые для демодуляции)
def loramod(x, SF, BW, fs, polarity=1):
    """Generate LoRa modulated signal (same as in TX)."""
    M = 2**SF
    Ts = M / BW
    Ns = int(fs * M / BW)
    x = np.atleast_1d(x)
    t = np.arange(Ns) / fs
    y = np.zeros(len(x) * Ns, dtype=complex)
    for i, sym in enumerate(x):
        gamma = sym / Ts
        beta = BW / Ts
        freq = (gamma + polarity * beta * t) % BW - BW/2
        theta = integrate.cumulative_trapezoid(freq, t, initial=0)
        y[i*Ns : (i+1)*Ns] = np.exp(1j * 2 * np.pi * theta)
    return y

def rotl(bits, count, size):
    """Rotate left modulo size."""
    mask = (1 << size) - 1
    count %= size
    bits &= mask
    return ((bits << count) & mask) | (bits >> (size - count))

# Функции декодирования LoRa
def LoRa_decode_gray(symbols):
    """Degray symbols."""
    return np.bitwise_xor(symbols, symbols >> 1)

def LoRa_decode_hamming(symbols, CR):
    """Hamming decode."""
    if CR > 2 and CR <= 4:
        H = [0,0,0,0,0,0,3,3,0,0,5,5,14,14,7,7,0,0,9,9,2,2,7,7,4,4,7,7,7,7,
             7,7,0,0,9,9,14,14,11,11,14,14,13,13,14,14,14,14,9,9,9,9,10,10,9,
             9,12,12,9,9,14,14,7,7,0,0,5,5,2,2,11,11,5,5,5,5,6,6,5,5,2,2,1,1,
             2,2,2,2,12,12,5,5,2,2,7,7,8,8,11,11,11,11,11,11,12,12,5,5,14,14,
             11,11,12,12,9,9,2,2,11,11,12,12,12,12,12,12,15,15,0,0,3,3,3,3,3,
             3,4,4,13,13,6,6,3,3,4,4,1,1,10,10,3,3,4,4,4,4,4,4,7,7,8,8,13,13,
             10,10,3,3,13,13,13,13,14,14,13,13,10,10,9,9,10,10,10,10,4,4,13,
             13,10,10,15,15,8,8,1,1,6,6,3,3,6,6,5,5,6,6,6,6,1,1,1,1,2,2,1,1,
             4,4,1,1,6,6,15,15,8,8,8,8,8,8,11,11,8,8,13,13,6,6,15,15,8,8,1,1,
             10,10,15,15,12,12,15,15,15,15,15,15]
        decoded = []
        for i in range(0, len(symbols), 2):
            r0 = symbols[i] & 0xFF
            r1 = symbols[i+1] & 0xFF if i+1 < len(symbols) else 0
            s0 = H[r0]
            s1 = H[r1]
            decoded.append(((s0 << 4) & 0xFF) | s1)
        return np.array(decoded)
    elif CR > 0 and CR <= 2:
        def selectbits(data, indices):
            res = 0
            for j, idx in enumerate(indices):
                if (data >> idx) & 1:
                    res |= (1 << j)
            return res
        indices = [0,1,2,4]   # MATLAB bits 1,2,3,5 (1-based) -> 0,1,2,4
        decoded = []
        for i in range(0, len(symbols), 2):
            s0 = selectbits(symbols[i] & 0xFF, indices)
            s1 = selectbits(symbols[i+1] & 0xFF, indices) if i+1 < len(symbols) else 0
            decoded.append(((s0 << 4) & 0xFF) | s1)
        return np.array(decoded)
    else:
        return symbols

def LoRa_decode_interleave(symbols, ppm, rdd):
    """Deinterleave symbols."""
    deinterleaved = []
    idx = 0
    num_blocks = len(symbols) // (4+rdd)
    for _ in range(num_blocks):
        sym_int = np.zeros(ppm, dtype=int)
        for sym_idx in range(4+rdd):
            sym_rot = rotl(symbols[idx], sym_idx, ppm)
            mask = 1 << (ppm-1)
            ctr = ppm - 1
            while mask > 0:
                if sym_rot & mask:
                    sym_int[ctr] |= (1 << sym_idx)
                mask >>= 1
                ctr -= 1
            idx += 1
        deinterleaved.extend(sym_int)
    return np.array(deinterleaved)

def LoRa_decode_shuffle(symbols, N):
    """Unshuffle symbols (inverse of encode shuffle)."""
    pattern = [5,0,1,2,4,3,6,7]   # as in MATLAB decode_shuffle
    symbols_shuf = np.zeros(N, dtype=int)
    for i in range(N):
        val = 0
        for j, p in enumerate(pattern):
            if (symbols[i] >> p) & 1:
                val |= (1 << j)
        symbols_shuf[i] = val
    return symbols_shuf

def LoRa_decode_swap(symbols):
    """Swap nibbles (same as encode)."""
    symbols_swp = np.zeros_like(symbols)
    for i, s in enumerate(symbols):
        low = (s & 0x0F) << 4
        high = (s & 0xF0) >> 4
        symbols_swp[i] = low | high
    return symbols_swp

def LoRa_decode_white(symbols, CR, DE):
    """Dewhitening (XOR with same sequence as encode)."""
    if DE == 0:
        if CR > 2 and CR <= 4:
            white_seq = [255,255,45,255,120,255,225,255,0,255,210,45,85,
                         120,75,225,102,0,30,210,255,85,45,75,120,102,225,
                         30,210,255,135,45,204,120,170,225,180,210,153,135,
                         225,204,0,170,0,180,0,153,0,225,210,0,85,0,153,0,
                         225,0,210,210,135,85,30,153,45,225,120,210,225,135,
                         210,30,85,45,153,120,51,225,85,210,75,85,102,153,
                         30,51,45,85,120,75,225,102,0,30,0,45,0,120,210,225,
                         135,0,204,0,120,0,51,210,85,135,153,204,51,120,85,
                         51,153,85,51,153,135,51,204,85,170,153,102,51,30,
                         135,45,204,120,170,51,102,85,30,153,45,225,120,0,
                         51,0,85,210,153,85,225,75,0,180,0,75,210,102,85,
                         204,75,170,180,102,75,204,102,170,204,180,170,75,
                         102,102,204,204,170,120,180,51,75,85,102,75,204,
                         102,120,204,51,120,85,225,75,0,102,210,204,135,120,
                         30,225,255,0,255,210,45,135,170,30,102,255,204,255,
                         170,45,102,170,30,102,255,204,45,170,170,102,180,
                         30,75,255,102,45,30,170,45,180,170,75,180,102,153,
                         30,225,45,210,170,85,180,153,153,225,225,0,210,210,
                         85,135,153,204,225,170,0,102,210,204,135,120,204,
                         225,170,210,102,135,204,30,120,255,225,45,210,120,
                         135,51,30,135,255,30,45,45,120,120,51,51,135,135,
                         30,204,45,120,120,225,51,210,135,85,204,75,120,102,
                         225,204,210,170,85,180,75,153,102,51,204,85,170,
                         153,180,225,153,210,51,85,85,75,153,180,225,153,
                         210,51,85,85,75,75,180,180,153,75,51,180,85,153,
                         75,51,180,135,75,30,180,45,153,170,51,102,199,30,
                         30,45,45,170,170,102,102,204,30,120,45,51,170,135,
                         102,30,204,255,120,45,51,170,135,102,30,30,255,255,
                         45,255,170,255,102,45,30,170,255,180,255,153,255,
                         51,45,135,170,204,180,120,153,51,51,135,135,204,
                         204,170,120,180,51,75,135,180,204,153,170,225,180,
                         210,75,135,180,204,153,120,225,225,210,0,135,0,204,
                         210,120,135,225,30,0,45,0,170,210,180,135,75,30,
                         180,45,75,170,180,180,75,75,102,180,30,75,255,180,
                         255,75,45,102,120,30,51,255,85,255,75,45,180,120,
                         153,51,225,85,0,75,210,180,85,153,153,225,51,0,135,
                         210,30,85,255,153,255,51,255,135,255,30,0,0,0,0,
                         135,225,170,204]
        elif CR > 0 and CR <= 2:
            white_seq = [255,255,45,255,120,255,48,46,0,46,18,60,20,40,10,
                         48,54,0,30,18,46,20,60,10,40,54,48,30,18,46,6,60,
                         12,40,58,48,36,18,24,6,48,12,0,58,0,36,0,24,0,48,
                         18,0,20,0,24,0,48,0,18,18,6,20,30,24,60,48,40,18,
                         48,6,18,30,20,60,24,40,34,48,20,18,10,20,54,24,30,
                         34,60,20,40,10,48,54,0,30,0,60,0,40,18,48,6,0,12,
                         0,40,0,34,18,20,6,24,12,34,40,20,34,24,20,34,24,6,
                         34,12,20,58,24,54,34,30,6,60,12,40,58,34,54,20,30,
                         24,60,48,40,0,34,0,20,18,24,20,48,10,0,36,0,10,18,
                         54,20,12,10,58,36,54,10,12,54,58,12,36,58,10,54,54,
                         12,12,58,40,36,34,10,20,54,10,12,54,40,12,34,40,20,
                         48,10,0,54,18,12,6,40,30,48,46,0,46,18,60,6,58,30,
                         54,46,12,46,58,60,54,58,30,54,46,12,60,58,58,54,36,
                         30,10,46,54,60,30,58,60,36,58,10,36,54,24,30,48,60,
                         18,58,20,36,24,24,48,48,0,18,18,20,6,24,12,48,58,0,
                         54,18,12,6,40,12,48,58,18,54,6,12,30,40,46,48,60,
                         18,40,6,34,30,6,46,30,60,60,40,40,34,34,6,6,30,12,
                         60,40,40,48,34,18,6,20,12,10,40,54,48,12,18,58,20,
                         36,10,24,54,34,12,20,58,24,36,48,24,18,34,20,20,10,
                         24,36,48,24,18,34,20,20,10,10,36,36,24,10,34,36,20,
                         24,10,34,36,6,10,30,36,60,24,58,34,54,6,30,30,60,
                         60,58,58,54,54,12,30,40,60,34,58,6,54,30,12,46,40,
                         60,34,58,6,54,30,30,46,46,60,46,58,46,54,60,30,58,
                         46,36,46,24,46,34,60,6,58,12,36,40,24,34,34,6,6,12,
                         12,58,40,36,34,10,6,36,12,24,58,48,36,18,10,6,36,
                         12,24,40,48,48,18,0,6,0,12,18,40,6,48,30,0,60,0,58,
                         18,36,6,10,30,36,60,10,58,36,36,10,10,54,36,30,10,
                         46,36,46,10,60,54,40,30,34,46,20,46,10,60,36,40,24,
                         34,48,20,0,10,18,36,20,24,24,48,34,0,6,18,30,20,46,
                         24,46,34,46,6,46,30,0,0,0,0,36,6]
        else:
            white_seq = []
    N = min(len(symbols), len(white_seq))
    return np.bitwise_xor(symbols[:N], white_seq[:N])

def LoRa_Decode_Full(symbols_message, SF):
    """Decode full payload packet."""
    # Decode header
    rdd_hdr = 4
    ppm_hdr = SF - 2
    symbols_hdr = np.round(symbols_message[:8] / 4).astype(int) % (2**ppm_hdr)
    symbols_hdr_gry = LoRa_decode_gray(symbols_hdr)
    symbols_hdr_int = LoRa_decode_interleave(symbols_hdr_gry, ppm_hdr, rdd_hdr)
    symbols_hdr_shf = LoRa_decode_shuffle(symbols_hdr_int, len(symbols_hdr_int))
    symbols_hdr_fec = LoRa_decode_hamming(symbols_hdr_shf[:5], rdd_hdr)
    CR_pld = (symbols_hdr_fec[1] >> 5) & 0x7
    if CR_pld > 4 or CR_pld < 1:
        return None, None, None, None
    CRC_pld = (symbols_hdr_fec[1] >> 4) & 1
    pld_length = symbols_hdr_fec[0] + CRC_pld*2
    # Decode payload
    rdd_pld = CR_pld
    ppm_pld = SF
    symbols_pld = symbols_message[8:]
    symbols_pld_gry = LoRa_decode_gray(symbols_pld)
    symbols_pld_int = LoRa_decode_interleave(symbols_pld_gry, ppm_pld, rdd_pld)
    symbols_pld_shf = LoRa_decode_shuffle(symbols_pld_int, len(symbols_pld_int))
    if SF > 7:
        symbols_pld_hdr = np.concatenate([symbols_hdr_shf[-SF+8:], symbols_pld_shf])
    else:
        symbols_pld_hdr = symbols_pld_shf
    symbols_pld_wht = LoRa_decode_white(symbols_pld_hdr, rdd_pld, 0)
    symbols_pld_fec = LoRa_decode_hamming(symbols_pld_wht, rdd_pld)
    symbols_pld_fin = LoRa_decode_swap(symbols_pld_fec)
    message_full = np.concatenate([symbols_hdr_fec, symbols_pld_fin])
    return message_full, CR_pld, pld_length, CRC_pld


# FSK Detection
def FSKDetection(signal, SF, detection):
    """FSK detection (coherent or non-coherent)."""
    M = 2**SF
    N = len(signal)
    num_sym = N // M
    if detection == 1:  # coherent
        t = np.linspace(0, 0.999, M)
        r = np.zeros((M, num_sym))
        for sym in range(M):
            freq_idx = M - sym
            ref = np.exp(-1j * 2 * np.pi * freq_idx * t)
            conv_full = np.correlate(signal, ref, mode='full')
            start = M
            r[sym, :] = np.real(conv_full[start : start + num_sym*M : M])
        symbols = np.argmax(r, axis=0)
        return symbols
    elif detection == 2:  # non-coherent
        signal_mat = signal.reshape(M, num_sym, order='F')
        fft_vals = np.abs(np.fft.fft(signal_mat, axis=0))
        symbols = np.argmax(fft_vals, axis=0)
        return symbols


# Демодуляция полного пакета
def LoRa_Demodulate_Full(signal, SF, Bandwidth, Coherece, n_preamble=8):
    """Demodulate full LoRa packet."""
    M = 2**SF
    if len(signal) < M:
        return None, None, None
    Nsymbols = len(signal) // M
    UChirpsDemod = loramod(np.zeros(Nsymbols), SF, Bandwidth, Bandwidth, 1)
    min_len = min(len(signal), len(UChirpsDemod))
    SniffSignal = signal[:min_len] * UChirpsDemod[:min_len]
    if Coherece == 2:
        num_cols = len(SniffSignal) // M
        if num_cols == 0:
            return None, None, None
        sniff_mat = SniffSignal[:num_cols*M].reshape(M, num_cols, order='F')
        fftSync = np.fft.fft(sniff_mat, axis=0)
        max_vals = np.max(fftSync, axis=0)
        SyncInd = np.argsort(max_vals)
        sync = np.sort(SyncInd[-2:])
        sync = sync[-1] + 1
        NPreamb = sync - 5
    else:
        NPreamb = n_preamble
    dChirpsDemod = loramod(np.zeros(NPreamb), SF, Bandwidth, Bandwidth, -1)
    min_len2 = min(len(signal), len(dChirpsDemod))
    pream_signal = signal[:min_len2] * dChirpsDemod[:min_len2]
    symbols_pream = FSKDetection(pream_signal, SF, Coherece)
    symbol_offset = (np.bincount(symbols_pream).argmax() + 1) % M
    MessageStartInd = int((NPreamb + 4.25) * M)
    if MessageStartInd >= len(signal):
        return None, None, None
    Nmessage = (len(signal) - MessageStartInd) // M
    if Nmessage <= 0:
        return None, None, None
    MessageEndInd = Nmessage * M + MessageStartInd
    MessageSignal = signal[MessageStartInd:MessageEndInd] * loramod(np.zeros(Nmessage), SF, Bandwidth, Bandwidth, -1)
    SymbolsDemod = FSKDetection(MessageSignal, SF, Coherece)
    SymbolsMessage = (SymbolsDemod - symbol_offset) % M
    return SymbolsMessage, SymbolsDemod, NPreamb


# Вспомогательная функция добавления шума
def awgn(signal, snr_db):
    """Add white Gaussian noise to signal."""
    if snr_db == np.inf:
        return signal.copy()
    signal_power = np.mean(np.abs(signal)**2)
    snr_linear = 10**(snr_db/10)
    noise_power = signal_power / snr_linear
    noise = np.sqrt(noise_power/2) * (np.random.randn(len(signal)) + 1j*np.random.randn(len(signal)))
    return signal + noise


# Основная функция приёмника
def LoRa_Rx(signal, Bandwidth, SF, Coherece, Fs, df, *args):
    """Emulate LoRa receiver."""
    nargs = len(args)
    if nargs == 0:
        SNR = np.inf
        n_preamble = 8
    elif nargs == 1:
        SNR = args[0]
        n_preamble = 8
    elif nargs >= 2:
        SNR = args[0]
        n_preamble = args[1]
    else:
        SNR, n_preamble = np.inf, 8

    if Fs == Bandwidth:
        signal_demod = awgn(signal, SNR)
    else:
        t = np.arange(len(signal))
        signal_freq_demod = signal * np.exp(1j * 2 * np.pi * df / Fs * t)
        nyquist = Fs / 2
        Wn = Bandwidth / nyquist
        if Wn >= 1.0:
            Wn = 0.999
        sos = scipy_signal.butter(10, Wn, btype='low', output='sos')
        signal_filter = scipy_signal.sosfiltfilt(sos, signal_freq_demod)
        num_out = int(len(signal_filter) * Bandwidth / Fs)
        signal_resampled = scipy_signal.resample(signal_filter, num_out)
        signal_demod = awgn(signal_resampled, SNR)

    try:
        symbols_message, _, _ = LoRa_Demodulate_Full(signal_demod, SF, Bandwidth, Coherece, n_preamble)
        if symbols_message is None:
            return np.nan
        message_full, _, _, _ = LoRa_Decode_Full(symbols_message, SF)
        if message_full is None:
            return np.nan
        start = 7
        end_idx = message_full[0] + 2
        if end_idx > len(message_full):
            end_idx = len(message_full)
        message_bytes = message_full[7:end_idx]
        message = ''.join(chr(b) for b in message_bytes if b != 0)
        return message
    except Exception:
        return np.nan