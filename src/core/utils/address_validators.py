"""Address validation utilities for blockchain addresses."""

import re
import base58


def is_valid_solana_address(address: str) -> bool:
    """
    Verify if a string is a valid Solana address (token or otherwise).
    
    Args:
        address (str): The address string to validate
        
    Returns:
        bool: True if valid Solana address, False otherwise
    """
    if not isinstance(address, str):
        return False
    
    # Check length (Solana addresses are typically 32-44 characters)
    if len(address) < 32 or len(address) > 44:
        return False
    
    # Check if it contains only valid base58 characters
    # Base58 alphabet: 123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz
    base58_pattern = r'^[1-9A-HJ-NP-Za-km-z]+$'
    if not re.match(base58_pattern, address):
        return False
    
    try:
        # Attempt to decode the base58 string
        decoded = base58.b58decode(address)
        
        # Solana addresses should decode to exactly 32 bytes
        if len(decoded) != 32:
            return False
            
        return True
    except Exception:
        return False


def is_valid_evm_address(address: str) -> bool:
    """
    Validates if the given address is a valid EVM blockchain address.
    
    Args:
        address (str): The address string to validate
        
    Returns:
        bool: True if the address is valid, False otherwise
        
    Examples:
        >>> is_valid_evm_address("0x742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e")
        True
        >>> is_valid_evm_address("0xinvalid")
        False
        >>> is_valid_evm_address("742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e")
        False
    """
    if not isinstance(address, str):
        return False
    
    # EVM address pattern: 0x followed by exactly 40 hexadecimal characters
    pattern = r'^0x[a-fA-F0-9]{40}$'
    
    return bool(re.match(pattern, address))