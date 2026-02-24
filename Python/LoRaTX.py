import numpy as np
import scipy.integrate as integrate


# Вспомогательные битовые функции (аналог de2bi / bi2de MATLAB)
def de2bi(num, width):
    """Convert integer to list of bits (LSB first) of given width."""
    return [(num >> i) & 1 for i in range(width)]

def bi2de(bits):
    """Convert list of bits (LSB first) to integer."""
    num = 0
    for i, b in enumerate(bits):
        num |= (b << i)
    return num


# Функции кодирования LoRa
def LoRa_encode_swap(symbols):
    """Swap nibbles in each symbol."""
    symbols_swp = np.zeros_like(symbols)
    for i, s in enumerate(symbols):
        low = (s & 0x0F) << 4
        high = (s & 0xF0) >> 4
        symbols_swp[i] = low | high
    return symbols_swp

def LoRa_encode_hamming(symbols, CR):
    """Hamming encode symbols based on CR."""
    if CR > 2 and CR <= 4:  # detection and correction
        n = len(symbols) * (4 + 4) // 4
        H = [0,210,85,135,153,75,204,30,225,51,180,102,120,170,45,255]
        encoded = np.zeros(n, dtype=int)
        idx = 0
        for s in symbols:
            s0 = (s >> 4) & 0x0F
            s1 = s & 0x0F
            encoded[idx] = H[s0]
            encoded[idx+1] = H[s1]
            idx += 2
        return encoded
    elif CR > 0 and CR <= 2:  # detection only
        def selectbits_encode(sym):
            bits = de2bi(sym, 8)
            new_bits = [0, bits[0], bits[1], bits[2], 0, bits[3], 0, 0]
            return bi2de(new_bits)
        encoded = []
        for s in symbols:
            s0 = (s >> 4) & 0xFF
            s1 = s & 0xFF
            encoded.append(selectbits_encode(s0))
            encoded.append(selectbits_encode(s1))
        return np.array(encoded)
    else:
        return symbols

def LoRa_encode_white(symbols, CR, DE):
    """Whitening by XOR with known sequence."""
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

def LoRa_encode_shuffle(symbols):
    """Shuffle bits according to specific pattern."""
    pat = [1,2,3,5,4,0,6,7]   # derived from MATLAB [2 3 4 6 5 1 7 8] (1-based)
    shuffled = np.zeros_like(symbols)
    for i, s in enumerate(symbols):
        bits = de2bi(s, 8)
        new_bits = [bits[p] for p in pat]
        shuffled[i] = bi2de(new_bits)
    return shuffled

def rotl(bits, count, size):
    """Rotate left modulo size."""
    mask = (1 << size) - 1
    count %= size
    bits &= mask
    return ((bits << count) & mask) | (bits >> (size - count))

def LoRa_encode_interleave(symbols, ppm, rdd):
    """Interleave symbols."""
    interleaved = []
    num_blocks = len(symbols) // ppm
    for block in range(num_blocks):
        x = symbols[block*ppm : (block+1)*ppm]
        bin_mat = np.array([de2bi(val, 4+rdd) for val in x])  # (ppm, 4+rdd)
        bin_mat_t = bin_mat.T  # (4+rdd, ppm)
        sym_rotated = [bi2de(row) for row in bin_mat_t]
        mask = ppm
        sym_int = []
        for c in range(4+rdd):
            sym_int.append(rotl(sym_rotated[c], mask, ppm))
            mask -= 1
        interleaved.extend(sym_int)
    return np.array(interleaved)

def LoRa_encode_gray(symbols):
    """Apply Gray coding."""
    gray = np.zeros_like(symbols)
    for i, s in enumerate(symbols):
        g = s
        g ^= (g >> 16)
        g ^= (g >> 8)
        g ^= (g >> 4)
        g ^= (g >> 2)
        g ^= (g >> 1)
        gray[i] = g
    return gray

def LoRa_Encode_Full(message, SF, CR):
    """Encode message into LoRa packet."""
    if isinstance(message, str):
        message_dbl = [ord(c) for c in message]
    else:
        message_dbl = message
    N_pld = {7:1, 8:2, 9:3, 10:4, 11:5, 12:6}.get(SF, 0)
    CRC_pld = 1
    imp = 0
    opt = 0
    numerator = 8*(len(message_dbl) + 5) - 4*SF + 28 + 16*CRC_pld - 20*imp
    denominator = 4*(SF - 2*opt)
    if denominator <= 0:
        n_packet = 8
    else:
        n_packet = 8 + int(np.ceil(numerator / denominator)) * (CR + 4)
    n_wht = SF * ((n_packet - 8) // (4 + CR)) + N_pld - 1
    add = {7:0, 8:1, 9:2, 10:3, 11:4, 12:5}.get(SF, 0)
    n_pld = int(np.ceil((n_wht + add) / 2))
    n_pad = n_pld - 5 - len(message_dbl) - CRC_pld*2
    if n_pad < 0:
        n_pad = 0
    CRC_dbl = [1, 1] if CRC_pld else []
    pad_dbl = [0] * (n_pad + N_pld - 1)
    pld_dbl = [255, 255, 0, 0] + message_dbl + [0] + CRC_dbl + pad_dbl
    pld_swp = LoRa_encode_swap(np.array(pld_dbl))
    pld_enc = LoRa_encode_hamming(pld_swp, CR)
    pld_enc = pld_enc[:n_wht]
    pld_wht = LoRa_encode_white(pld_enc, CR, 0)
    packet_hdr = [len(message_dbl)+5,
                  CRC_pld*16 + (CR==1)*32 + (CR==2)*64 + (CR==3)*96 + (CR==4)*128,
                  224]
    packet_hdr_enc_tmp = LoRa_encode_hamming(np.array(packet_hdr), 4)
    packet_hdr_enc = np.concatenate([packet_hdr_enc_tmp[:5], pld_wht[:N_pld-1]])
    packet_pld = pld_wht[N_pld-1:]
    packet_pld_shf = np.bitwise_and(LoRa_encode_shuffle(packet_pld), (1 << (4+CR)) - 1)
    packet_hdr_shf = LoRa_encode_shuffle(packet_hdr_enc)
    packet_pld_int = LoRa_encode_interleave(packet_pld_shf, SF, CR)
    packet_hdr_int = LoRa_encode_interleave(packet_hdr_shf, SF-2, 4)
    packet_pld_gray = LoRa_encode_gray(packet_pld_int)
    packet_hdr_gray = LoRa_encode_gray(packet_hdr_int)
    packet = np.concatenate([4*packet_hdr_gray, packet_pld_gray])
    return packet


# Модуляция LoRa
def loramod(x, SF, BW, fs, polarity=1):
    """Generate LoRa modulated signal for symbols x."""
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

def LoRa_Modulate_Full(packet, SF, Bandwidth, n_preamble, SyncKey, Fs):
    """Construct full LoRa packet (preamble + sync + payload)."""
    signal_prmb = loramod((SyncKey-1) * np.ones(n_preamble), SF, Bandwidth, Fs, 1)
    signal_sync_u = loramod([0, 0], SF, Bandwidth, Fs, 1)
    signal_sync_d1 = loramod(0, SF, Bandwidth, Fs, -1)
    signal_sync_d = np.concatenate([signal_sync_d1, signal_sync_d1, signal_sync_d1[:len(signal_sync_d1)//4]])
    signal_mesg = loramod((packet + SyncKey) % (2**SF), SF, Bandwidth, Fs, 1)
    signal = np.concatenate([signal_prmb, signal_sync_u, signal_sync_d, signal_mesg])
    return signal


# Основная функция передатчика
def LoRa_Tx(message, Bandwidth, SF, Pt, Fs, df, *args):
    """Emulate LoRa transmission."""
    nargs = len(args)
    if nargs == 0:
        CR = 1
        n_preamble = 8
        SyncKey = 5
    elif nargs == 1:
        CR = args[0]
        n_preamble = 8
        SyncKey = 5
    elif nargs == 2:
        CR = args[0]
        n_preamble = args[1]
        SyncKey = 5
    elif nargs >= 3:
        CR = args[0]
        n_preamble = args[1]
        SyncKey = args[2]
    else:
        CR, n_preamble, SyncKey = 1, 8, 5
    packet = LoRa_Encode_Full(message, SF, CR)
    signal = LoRa_Modulate_Full(packet, SF, Bandwidth, n_preamble, SyncKey, Fs)
    t = np.arange(len(signal))
    signal_mod = 10**(Pt/20) * signal * np.exp(-1j * 2 * np.pi * df / Fs * t)
    return signal_mod