import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
import secrets

from app.services.siwe import generate_nonce, parse_siwe_message, recover_address, SiweMessage
from app.services.siwe_nonce_store import put_nonce, consume_nonce
from app.api.v1.auth import siwe_nonce, siwe_login
from app.schemas.siwe import SiweLoginRequest
from app.models.user import User
from web3 import Web3


class TestSIWEServices:
    """Tests for SIWE service functions"""
    
    def test_generate_nonce_returns_valid_string(self):
        """Test that generate_nonce returns a valid nonce string"""
        # Act
        nonce = generate_nonce()
        
        # Assert
        assert isinstance(nonce, str)
        assert len(nonce) == 16
        assert nonce.replace('-', '').replace('_', '').isalnum()
    
    def test_generate_nonce_is_unique(self):
        """Test that generate_nonce returns unique values"""
        # Act
        nonce1 = generate_nonce()
        nonce2 = generate_nonce()
        
        # Assert
        assert nonce1 != nonce2
    
    def test_parse_siwe_message_valid(self):
        """Test parsing a valid SIWE message"""
    message = """localhost wants you to sign in with your Ethereum account:
0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1

Sign in to Trading Platform

URI: http://localhost:8000
Version: 1
Chain ID: 1
Nonce: testNonce123
Issued At: 2024-01-01T00:00:00Z"""
    
    result = parse_siwe_message(message)
    
    # مقایسه با checksum address
    expected_address = Web3.to_checksum_address("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1")
    actual_address = Web3.to_checksum_address(result.address)
    
    assert actual_address == expected_address
    assert result.domain == "localhost"
    assert result.nonce == "testNonce123"
    assert result.chain_id == 1
    
    def test_parse_siwe_message_invalid_format(self):
        """Test that parse_siwe_message raises error for invalid format"""
        # Arrange
        invalid_message = "This is not a valid SIWE message"
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid SIWE message format"):
            parse_siwe_message(invalid_message)
    
    def test_recover_address_valid_signature(self):
        """Test recovering Ethereum address from a valid signature"""
        # Arrange
        private_key = "0x4c0883a69102937d6231471b5dbb6204fe512961708279f8d5e7f5e8b2e4e8b7"
        account = Account.from_key(private_key)
        
        message = "Test message"
        encoded_message = encode_defunct(text=message)
        signed = account.sign_message(encoded_message)
        
        # Act
        recovered_address = recover_address(message, signed.signature.hex())
        
        # Assert
        assert recovered_address.lower() == account.address.lower()
    
    def test_recover_address_wrong_signature(self):
        """Test that wrong signature recovers different address"""
        # Arrange
        account1 = Account.from_key("0x4c0883a69102937d6231471b5dbb6204fe512961708279f8d5e7f5e8b2e4e8b7")
        account2 = Account.from_key("0x5c0883a69102937d6231471b5dbb6204fe512961708279f8d5e7f5e8b2e4e8b8")
        
        message = "Test message"
        encoded_message = encode_defunct(text=message)
        signed = account2.sign_message(encoded_message)
        
        # Act
        recovered_address = recover_address(message, signed.signature.hex())
        
        # Assert
        assert recovered_address.lower() != account1.address.lower()
        assert recovered_address.lower() == account2.address.lower()


class TestSIWENonceStore:
    """Tests for SIWE nonce store using Redis"""
    
    @patch('app.services.siwe_nonce_store.r')
    def test_put_nonce_stores_in_redis(self, mock_redis):
        """Test that put_nonce stores nonce in Redis with TTL"""
        # Arrange
        nonce = "test_nonce_123"
        
        # Act
        put_nonce(nonce)
        
        # Assert
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert "siwe:nonce:test_nonce_123" in call_args[0]
        assert call_args[2] == "1"
    
    @patch('app.services.siwe_nonce_store.r')
    def test_consume_nonce_valid(self, mock_redis):
        """Test consuming a valid nonce"""
        # Arrange
        nonce = "valid_nonce"
        mock_redis.get.return_value = "1"
        mock_redis.delete.return_value = 1
        
        # Act
        result = consume_nonce(nonce)
        
        # Assert
        assert result is True
        mock_redis.get.assert_called_once()
        mock_redis.delete.assert_called_once()
    
    @patch('app.services.siwe_nonce_store.r')
    def test_consume_nonce_invalid(self, mock_redis):
        """Test consuming an invalid/expired nonce"""
        # Arrange
        nonce = "invalid_nonce"
        mock_redis.get.return_value = None
        
        # Act
        result = consume_nonce(nonce)
        
        # Assert
        assert result is False
        mock_redis.get.assert_called_once()
        mock_redis.delete.assert_not_called()
    
    @patch('app.services.siwe_nonce_store.r')
    def test_consume_nonce_prevents_replay(self, mock_redis):
        """Test that same nonce cannot be consumed twice"""
        # Arrange
        nonce = "replay_nonce"
        mock_redis.get.side_effect = ["1", None]  # First call returns "1", second returns None
        
        # Act
        result1 = consume_nonce(nonce)
        result2 = consume_nonce(nonce)
        
        # Assert
        assert result1 is True
        assert result2 is False


class TestSIWEEndpoints:
    """Tests for SIWE authentication endpoints"""
    
    @patch('app.api.v1.auth.generate_nonce')
    @patch('app.api.v1.auth.put_nonce')
    def test_siwe_nonce_endpoint(self, mock_put_nonce, mock_generate_nonce):
        """Test GET /auth/siwe/nonce endpoint"""
        # Arrange
        mock_generate_nonce.return_value = "generated_nonce_123"
        
        # Act
        response = siwe_nonce()
        
        # Assert
        assert response.nonce == "generated_nonce_123"
        mock_generate_nonce.assert_called_once()
        mock_put_nonce.assert_called_once_with("generated_nonce_123")
    
    @patch('app.api.v1.auth.parse_siwe_message')
    @patch('app.api.v1.auth.consume_nonce')
    @patch('app.api.v1.auth.recover_address')
    @patch('app.api.v1.auth.create_access_token')
    @patch.dict('os.environ', {'APP_DOMAIN': 'localhost', 'APP_ORIGIN': 'http://localhost:8000'})
    def test_siwe_login_success_existing_user(
        self, mock_create_token, mock_recover, mock_consume, mock_parse
    ):
        """Test successful SIWE login with existing user"""
        # Arrange
        mock_db = Mock()
        wallet_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1"
        
        mock_message = SiweMessage(
            domain="localhost",
            address=wallet_address,
            uri="http://localhost:8000",
            version=1,
            chain_id=1,
            nonce="valid_nonce",
            issued_at="2026-02-10T10:00:00Z"
        )
        mock_parse.return_value = mock_message
        mock_consume.return_value = True
        mock_recover.return_value = wallet_address
        
        existing_user = User(
            id=1,
            username="wallet_0x742d35",
            password_hash="DISABLED",
            wallet_address=wallet_address
        )
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user
        mock_create_token.return_value = "jwt_token_123"
        
        payload = SiweLoginRequest(
            message="SIWE message",
            signature="0xsignature"
        )
        
        # Act
        response = siwe_login(payload, mock_db)
        
        # Assert
        assert response.access_token == "jwt_token_123"
        mock_parse.assert_called_once_with("SIWE message")
        mock_consume.assert_called_once_with("valid_nonce")
        mock_recover.assert_called_once_with("SIWE message", "0xsignature")
        mock_create_token.assert_called_once_with(subject="1")
    
    @patch('app.api.v1.auth.parse_siwe_message')
    @patch('app.api.v1.auth.consume_nonce')
    @patch('app.api.v1.auth.recover_address')
    @patch('app.api.v1.auth.create_access_token')
    @patch.dict('os.environ', {'APP_DOMAIN': 'localhost', 'APP_ORIGIN': 'http://localhost:8000'})
    def test_siwe_login_creates_new_user(
        self, mock_create_token, mock_recover, mock_consume, mock_parse
    ):
        """Test SIWE login creates new user if wallet not found"""
        # Arrange
        mock_db = Mock()
        wallet_address = "0x9999999999999999999999999999999999999999"
        
        mock_message = SiweMessage(
            domain="localhost",
            address=wallet_address,
            uri="http://localhost:8000",
            version=1,
            chain_id=1,
            nonce="valid_nonce",
            issued_at="2026-02-10T10:00:00Z"
        )
        mock_parse.return_value = mock_message
        mock_consume.return_value = True
        mock_recover.return_value = wallet_address
        
        # First query returns None (user doesn't exist)
        # Second query also returns None (username available)
        mock_db.query.return_value.filter.return_value.first.side_effect = [None, None]
        mock_create_token.return_value = "new_user_token"
        
        payload = SiweLoginRequest(
            message="SIWE message",
            signature="0xsignature"
        )
        
        # Act
        response = siwe_login(payload, mock_db)
        
        # Assert
        assert response.access_token == "new_user_token"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # Check that user was created with correct wallet address
        created_user = mock_db.add.call_args[0][0]
        assert created_user.wallet_address == wallet_address
        assert created_user.password_hash == "DISABLED"
        assert "wallet_" in created_user.username
    
    @patch('app.api.v1.auth.parse_siwe_message')
    def test_siwe_login_invalid_message_format(self, mock_parse):
        """Test SIWE login rejects invalid message format"""
        # Arrange
        mock_db = Mock()
        mock_parse.side_effect = ValueError("Invalid format")
        
        payload = SiweLoginRequest(
            message="Invalid SIWE message",
            signature="0xsignature"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            siwe_login(payload, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Invalid SIWE message" in exc_info.value.detail
    
    @patch('app.api.v1.auth.parse_siwe_message')
    @patch('app.api.v1.auth.consume_nonce')
    def test_siwe_login_invalid_nonce(self, mock_consume, mock_parse):
        """Test SIWE login rejects invalid/expired nonce"""
        # Arrange
        mock_db = Mock()
        mock_message = SiweMessage(
            domain="localhost",
            address="0x123",
            uri="http://localhost:8000",
            version=1,
            chain_id=1,
            nonce="expired_nonce",
            issued_at="2026-02-10T10:00:00Z"
        )
        mock_parse.return_value = mock_message
        mock_consume.return_value = False  # Nonce invalid/expired
        
        payload = SiweLoginRequest(
            message="SIWE message",
            signature="0xsignature"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            siwe_login(payload, mock_db)
        
        assert exc_info.value.status_code == 401
        assert "Invalid or expired nonce" in exc_info.value.detail
    
    @patch('app.api.v1.auth.parse_siwe_message')
    @patch('app.api.v1.auth.consume_nonce')
    @patch.dict('os.environ', {'APP_DOMAIN': 'trustedsite.com', 'APP_ORIGIN': 'http://localhost:8000'})
    def test_siwe_login_wrong_domain(self, mock_consume, mock_parse):
        """Test SIWE login rejects wrong domain"""
        # Arrange
        mock_db = Mock()
        mock_message = SiweMessage(
            domain="malicious.com",  # Wrong domain
            address="0x123",
            uri="http://localhost:8000",
            version=1,
            chain_id=1,
            nonce="valid_nonce",
            issued_at="2026-02-10T10:00:00Z"
        )
        mock_parse.return_value = mock_message
        mock_consume.return_value = True
        
        payload = SiweLoginRequest(
            message="SIWE message",
            signature="0xsignature"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            siwe_login(payload, mock_db)
        
        assert exc_info.value.status_code == 401
        assert "Invalid SIWE domain" in exc_info.value.detail
    
    @patch('app.api.v1.auth.parse_siwe_message')
    @patch('app.api.v1.auth.consume_nonce')
    @patch('app.api.v1.auth.recover_address')
    @patch.dict('os.environ', {'APP_DOMAIN': 'localhost', 'APP_ORIGIN': 'http://localhost:8000'})
    def test_siwe_login_signature_mismatch(self, mock_recover, mock_consume, mock_parse):
        """Test SIWE login rejects mismatched signature"""
        # Arrange
        mock_db = Mock()
        mock_message = SiweMessage(
            domain="localhost",
            address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1",
            uri="http://localhost:8000",
            version=1,
            chain_id=1,
            nonce="valid_nonce",
            issued_at="2026-02-10T10:00:00Z"
        )
        mock_parse.return_value = mock_message
        mock_consume.return_value = True
        mock_recover.return_value = "0x9999999999999999999999999999999999999999"  # Different address
        
        payload = SiweLoginRequest(
            message="SIWE message",
            signature="0xwrong_signature"
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            siwe_login(payload, mock_db)
        
        assert exc_info.value.status_code == 401
        assert "Invalid signature" in exc_info.value.detail