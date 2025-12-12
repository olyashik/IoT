import numpy as np
from lora_encode import *
from lora_modulate import LoRa_Modulate_Full


def LoRa_Tx(message, Bandwidth, SF, Pt, Fs, df, *varargin):
    """
    LoRa Transmitter Function

    Parameters:
        message: String message to transmit
        Bandwidth: Signal bandwidth (Hz)
        SF: Spreading Factor (7-12)
        Pt: Transmit power in dB
        Fs: Sampling frequency (Hz)
        df: Frequency offset (Hz)
        *varargin: Optional parameters:
            varargin[0]: code rate (CR, 1-4)
            varargin[1]: symbols in preamble
            varargin[2]: sync key

    Returns:
        signal_mod: LoRa IQ waveform
    """

    # Handle variable number of arguments
    if len(varargin) == 0:
        CR = 1
        n_preamble = 8
        SyncKey = 5
    elif len(varargin) == 1:
        CR = varargin[0]
        n_preamble = 8
        SyncKey = 5
    elif len(varargin) == 2:
        CR = varargin[0]
        n_preamble = varargin[1]
        SyncKey = 5
    elif len(varargin) == 3:
        CR = varargin[0]
        n_preamble = varargin[1]
        SyncKey = varargin[2]
    else:
        raise ValueError("Too many arguments")

    # Encode message to LoRa packet
    packet = LoRa_Encode_Full(message, SF, CR)

    # Modulate packet to LoRa signal
    signal = LoRa_Modulate_Full(packet, SF, Bandwidth, n_preamble, SyncKey, Fs)

    # Apply frequency shift and convert to power
    t_vector = np.arange(len(signal)) / Fs
    signal_mod = (10 ** (Pt / 20)) * signal * np.exp(-1j * 2 * np.pi * df * t_vector)

    return signal_mod, packet


def LoRa_Encode_Full(message, SF, CR):
    """Encode message to LoRa packet"""
    # Encoding parameters
    CRC_pld = 1
    imp = 0
    opt = 0

    # String to Decimal
    message_chr = list(message)
    message_dbl = np.array([ord(c) for c in message_chr], dtype=np.uint8)

    # Packet Length Calculations
    N_pld_values = {7: 1, 8: 2, 9: 3, 10: 4, 11: 5, 12: 6}
    N_pld = N_pld_values.get(SF, 1)

    # Calculate number of symbols in packet
    n_packet = 8 + max([
        np.ceil((8 * (len(message_dbl) + 5) - 4 * SF + 28 + 16 * CRC_pld - 20 * imp) /
                (4 * (SF - 2 * opt))) * (CR + 4),
        0
    ])

    # Calculate number of symbols after interleaving
    n_wht = SF * np.floor((n_packet - 8) / (4 + CR)) + N_pld - 1

    # Calculate payload length
    n_pld = np.ceil((n_wht + N_pld - 1) / 2)

    # Calculate padding bytes
    n_pad = n_pld - 5 - len(message_dbl) - CRC_pld * 2

    # Create payload message
    CRC_dbl = CRC_pld * np.array([1, 1])
    pad_dbl = np.zeros(int(n_pad + N_pld - 1), dtype=int)
    pld_dbl = np.concatenate([[255, 255, 0, 0], message_dbl, [0], CRC_dbl, pad_dbl])

    # Swap Nibbles
    pld_swp = LoRa_encode_swap(pld_dbl)

    # Payload Encoding
    pld_enc = LoRa_encode_hamming(pld_swp, CR)
    pld_enc = pld_enc[:int(n_wht)]

    # Payload Whitening
    pld_wht = LoRa_encode_white(pld_enc, CR, 0)

    # Header Encoding
    packet_hdr = np.array([
        len(message_dbl) + 5,
        CRC_pld * 16 + (CR == 1) * 32 + (CR == 2) * 64 + (CR == 3) * 96 + (CR == 4) * 128,
        224
    ])

    packet_hdr_enc_tmp = LoRa_encode_hamming(packet_hdr, 4)
    packet_hdr_enc = np.concatenate([packet_hdr_enc_tmp[:5], pld_wht[:N_pld - 1]])

    # Packet Creation
    packet_pld = pld_wht[N_pld - 1:]
    packet_pld_shf = np.bitwise_and(LoRa_encode_shuffle(packet_pld), (1 << (4 + CR)) - 1)
    packet_hdr_shf = LoRa_encode_shuffle(packet_hdr_enc)

    # Interleaving
    packet_pld_int = LoRa_encode_interleave(packet_pld_shf, SF, CR)
    packet_hdr_int = LoRa_encode_interleave(packet_hdr_shf, SF - 2, 4)

    # Graying
    packet_pld_gray = LoRa_encode_gray(packet_pld_int)
    packet_hdr_gray = LoRa_encode_gray(packet_hdr_int)

    # Final packet
    packet = np.concatenate([4 * packet_hdr_gray, packet_pld_gray])

    return packet