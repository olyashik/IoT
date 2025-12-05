import numpy as np
import warnings

def rotl(bits, count, size):
    """Modulo rotation"""
    len_mask = (1 << size) - 1
    count = count % size
    bits = bits & len_mask
    return ((bits << count) & len_mask) | (bits >> (size - count))

def selectbits_encode(symbol):
    """Select specific bits and add zeros (from 8-bit to 4-bit)"""
    symbol_binary = [(symbol >> i) & 1 for i in range(7, -1, -1)]
    symbol_binary_rot = [0, symbol_binary[0], symbol_binary[1], symbol_binary[2],
                         0, symbol_binary[3], 0, 0]
    symbol_rot = 0
    for i, bit in enumerate(symbol_binary_rot[::-1]):
        if bit:
            symbol_rot |= (1 << i)
    return symbol_rot

def bitand(a, b):
    """Bitwise AND"""
    return a & b

def bitor(a, b):
    """Bitwise OR"""
    return a | b

def bitsll(a, n):
    """Bitwise shift left logical"""
    return a << n

def bitsra(a, n):
    """Bitwise shift right arithmetic (preserves sign)"""
    # In Python, >> is arithmetic for signed integers
    return a >> n

def de2bi(x, n):
    """Decimal to binary vector (LSB first)"""
    return [(x >> i) & 1 for i in range(n)]

def bi2de(bits):
    """Binary vector to decimal (LSB first)"""
    result = 0
    for i, bit in enumerate(bits):
        if bit:
            result |= (1 << i)
    return result

def convert_strings_to_chars(message):
    """Convert string to char array"""
    return list(message)

def hex2dec(hex_str):
    """Convert hex string to decimal"""
    return int(hex_str, 16)