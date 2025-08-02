"""Unit tests for address validation utilities."""

import pytest
from src.core.utils.address_validators import is_valid_solana_address, is_valid_evm_address


class TestSolanaAddressValidation:
    """Test suite for Solana address validation."""
    
    def test_valid_solana_addresses(self):
        """Test valid Solana addresses of various lengths."""
        valid_addresses = [
            # Standard 44-character Solana addresses (known valid ones)
            "11111111111111111111111111111112",  # System program (decodes to 32 bytes)
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",  # Token program
            "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",  # Common wallet
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC token
        ]
        
        for address in valid_addresses:
            assert is_valid_solana_address(address), f"Address should be valid: {address}"
    
    def test_invalid_type_inputs(self):
        """Test that non-string inputs return False."""
        invalid_inputs = [
            None,
            123,
            [],
            {},
            True,
            False,
            12.34,
        ]
        
        for invalid_input in invalid_inputs:
            assert not is_valid_solana_address(invalid_input), f"Should reject non-string input: {invalid_input}"
    
    def test_invalid_length_addresses(self):
        """Test addresses with invalid lengths."""
        # Too short (< 32 characters)
        short_addresses = [
            "",
            "1",
            "123456789",
            "1234567890123456789012345678901",  # 31 chars
        ]
        
        for address in short_addresses:
            assert not is_valid_solana_address(address), f"Should reject short address: {address}"
        
        # Too long (> 44 characters)
        long_addresses = [
            "123456789012345678901234567890123456789012345",  # 45 chars
            "1234567890123456789012345678901234567890123456789012345678901234567890",  # 70 chars
        ]
        
        for address in long_addresses:
            assert not is_valid_solana_address(address), f"Should reject long address: {address}"
    
    def test_invalid_base58_characters(self):
        """Test addresses containing invalid base58 characters."""
        # Base58 excludes: 0, O, I, l
        invalid_addresses = [
            "11111111111111111111111111111110",  # Contains '0'
            "1111111111111111111111111111111O",  # Contains 'O'
            "1111111111111111111111111111111I",  # Contains 'I'
            "1111111111111111111111111111111l",  # Contains 'l'
            "11111111111111111111111111111100",  # Multiple invalid chars
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5D0",  # Valid format but contains '0'
        ]
        
        for address in invalid_addresses:
            assert not is_valid_solana_address(address), f"Should reject address with invalid base58 chars: {address}"
    
    def test_malformed_base58_addresses(self):
        """Test addresses that fail base58 decoding."""
        malformed_addresses = [
            "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!",  # Invalid characters
            "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~",  # Invalid characters
            "                                            ",  # Spaces (invalid base58)
        ]
        
        for address in malformed_addresses:
            assert not is_valid_solana_address(address), f"Should reject malformed address: {address}"
    
    def test_edge_case_empty_string(self):
        """Test empty string specifically."""
        assert not is_valid_solana_address("")
    
    def test_valid_base58_wrong_decoded_length(self):
        """Test addresses that are valid base58 but decode to wrong byte length."""
        # These are valid base58 strings but don't decode to exactly 32 bytes
        wrong_length_addresses = [
            "1",  # Decodes to 1 byte
            "11",  # Decodes to 1 byte
            "111",  # Decodes to 1 byte
            "1111",  # Decodes to ~2 bytes
            "22222222222222222222222222222222",  # 32 chars but decodes to 23 bytes
            "1111111111111111111111111111111111",  # 34 chars, decodes to 34 bytes
        ]
        
        for address in wrong_length_addresses:
            assert not is_valid_solana_address(address), f"Should reject address with wrong decoded length: {address}"
    
    def test_specific_exception_handling(self):
        """Test specific exception cases in base58 decoding."""
        # Create addresses that will cause specific exceptions during base58 decoding
        exception_addresses = [
            # This will cause an exception in base58.b58decode
            "11111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111",  # Very long string
        ]
        
        for address in exception_addresses:
            assert not is_valid_solana_address(address), f"Should handle exception gracefully: {address}"


class TestEVMAddressValidation:
    """Test suite for EVM address validation."""
    
    def test_valid_evm_addresses(self):
        """Test valid EVM addresses."""
        valid_addresses = [
            "0x742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e",  # Mixed case
            "0x742d35cc6765c0532575f5a2c0a078df8a2d4e5e",  # Lowercase
            "0x742D35CC6765C0532575F5A2C0A078DF8A2D4E5E",  # Uppercase
            "0x0000000000000000000000000000000000000000",  # Zero address
            "0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",  # Max address
            "0x1234567890abcdef1234567890abcdef12345678",  # Mixed hex
            "0xA0b86991c31e123f0d5b8E1E0fB01E6E0c9A3f50",  # USDC contract
        ]
        
        for address in valid_addresses:
            assert is_valid_evm_address(address), f"Address should be valid: {address}"
    
    def test_invalid_type_inputs(self):
        """Test that non-string inputs return False."""
        invalid_inputs = [
            None,
            123,
            [],
            {},
            True,
            False,
            12.34,
        ]
        
        for invalid_input in invalid_inputs:
            assert not is_valid_evm_address(invalid_input), f"Should reject non-string input: {invalid_input}"
    
    def test_missing_0x_prefix(self):
        """Test addresses missing the 0x prefix."""
        addresses_without_prefix = [
            "742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e",  # Valid hex but no 0x
            "742d35cc6765c0532575f5a2c0a078df8a2d4e5e",  # Lowercase no 0x
            "742D35CC6765C0532575F5A2C0A078DF8A2D4E5E",  # Uppercase no 0x
        ]
        
        for address in addresses_without_prefix:
            assert not is_valid_evm_address(address), f"Should reject address without 0x prefix: {address}"
    
    def test_wrong_length_addresses(self):
        """Test addresses with incorrect lengths."""
        # Too short (< 40 hex characters after 0x)
        short_addresses = [
            "0x",  # No hex digits
            "0x1",  # 1 hex digit
            "0x123",  # 3 hex digits
            "0x742d35Cc6765C0532575f5A2c0a078Df8a2D4e5",  # 39 hex digits
        ]
        
        for address in short_addresses:
            assert not is_valid_evm_address(address), f"Should reject short address: {address}"
        
        # Too long (> 40 hex characters after 0x)
        long_addresses = [
            "0x742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e1",  # 41 hex digits
            "0x742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e123",  # 43 hex digits
        ]
        
        for address in long_addresses:
            assert not is_valid_evm_address(address), f"Should reject long address: {address}"
    
    def test_invalid_hexadecimal_characters(self):
        """Test addresses with non-hexadecimal characters."""
        invalid_hex_addresses = [
            "0x742d35Cc6765C0532575f5A2c0a078Df8a2D4eGH",  # Contains G, H
            "0x742d35Cc6765C0532575f5A2c0a078Df8a2D4eZZ",  # Contains Z
            "0x742d35Cc6765C0532575f5A2c0a078Df8a2D4e!@",  # Special chars
            "0x742d35Cc6765C0532575f5A2c0a078Df8a2D4e  ",  # Spaces
            "0x742d35Cc6765C0532575f5A2c0a078Df8a2D4e-+",  # Dash and plus
        ]
        
        for address in invalid_hex_addresses:
            assert not is_valid_evm_address(address), f"Should reject address with invalid hex chars: {address}"
    
    def test_case_sensitivity(self):
        """Test that both upper and lower case hex characters are accepted."""
        mixed_case_addresses = [
            "0xAbCdEf1234567890AbCdEf1234567890AbCdEf12",
            "0xabcdef1234567890abcdef1234567890abcdef12",
            "0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
        ]
        
        for address in mixed_case_addresses:
            assert is_valid_evm_address(address), f"Should accept mixed case address: {address}"
    
    def test_edge_cases(self):
        """Test edge cases and special scenarios."""
        edge_cases = [
            ("", False),  # Empty string
            ("0x", False),  # Just prefix
            ("0X742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e", False),  # Wrong prefix case
            ("742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e0x", False),  # Suffix instead of prefix
        ]
        
        for address, expected in edge_cases:
            result = is_valid_evm_address(address)
            assert result == expected, f"Address '{address}' should return {expected}, got {result}"
    
    def test_boundary_conditions(self):
        """Test exact length boundaries."""
        # Exactly 40 hex characters (valid)
        exactly_40_chars = "0x" + "a" * 40
        assert is_valid_evm_address(exactly_40_chars), "Should accept exactly 40 hex chars"
        
        # 39 hex characters (invalid)
        exactly_39_chars = "0x" + "a" * 39
        assert not is_valid_evm_address(exactly_39_chars), "Should reject 39 hex chars"
        
        # 41 hex characters (invalid)
        exactly_41_chars = "0x" + "a" * 41
        assert not is_valid_evm_address(exactly_41_chars), "Should reject 41 hex chars"


class TestAddressValidatorsIntegration:
    """Integration tests for address validation functions."""
    
    def test_distinct_validation_logic(self):
        """Test that Solana and EVM validators reject each other's formats."""
        # Valid EVM address should be rejected by Solana validator
        evm_address = "0x742d35Cc6765C0532575f5A2c0a078Df8a2D4e5e"
        assert not is_valid_solana_address(evm_address), "Solana validator should reject EVM address"
        
        # Valid Solana address should be rejected by EVM validator
        solana_address = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
        assert not is_valid_evm_address(solana_address), "EVM validator should reject Solana address"
    
    def test_common_invalid_inputs(self):
        """Test that both validators handle common invalid inputs consistently."""
        common_invalid_inputs = [None, "", 123, [], {}]
        
        for invalid_input in common_invalid_inputs:
            assert not is_valid_solana_address(invalid_input), f"Solana validator should reject: {invalid_input}"
            assert not is_valid_evm_address(invalid_input), f"EVM validator should reject: {invalid_input}"