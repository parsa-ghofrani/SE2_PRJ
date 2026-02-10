import pytest
from unittest.mock import Mock, patch, MagicMock
from web3 import Web3
from web3.exceptions import Web3Exception
from app.services.blockchain import BlockchainAdapter


@pytest.fixture
def mock_web3():
    """Create a mock Web3 instance"""
    mock = Mock(spec=Web3)
    mock.is_connected.return_value = True
    mock.eth.get_transaction_count.return_value = 0
    mock.to_wei.return_value = 1000000000  # 1 gwei
    return mock


@pytest.fixture
def mock_account():
    """Create a mock Ethereum account"""
    mock = Mock()
    mock.address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1"
    mock.sign_transaction.return_value = Mock(rawTransaction=b"signed_tx_data")
    return mock


@pytest.fixture
def mock_contract():
    """Create a mock smart contract"""
    mock = Mock()
    mock_function = Mock()
    mock_function.build_transaction.return_value = {
        'from': '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1',
        'nonce': 0,
        'gas': 300000,
        'gasPrice': 1000000000
    }
    mock.functions.recordTrade.return_value = mock_function
    return mock


class TestBlockchainAdapter:
    """Tests for the BlockchainAdapter class"""
    
    @patch('app.services.blockchain.Web3')
    @patch('app.services.blockchain.Account')
    @patch.dict('os.environ', {
        'CHAIN_RPC_URL': 'http://localhost:8545',
        'CHAIN_SENDER_PRIVATE_KEY': '0x' + '1' * 64,
        'TRADE_LEDGER_ADDRESS': '0x5FbDB2315678afecb367f032d93F642f64180aa3'
    })
    def test_adapter_connects_successfully(self, mock_account_class, mock_web3_class):
        """Test that BlockchainAdapter connects to blockchain correctly"""
        # Arrange
        mock_web3_instance = Mock()
        mock_web3_instance.is_connected.return_value = True
        mock_web3_class.return_value = mock_web3_instance
        mock_web3_class.HTTPProvider = Mock()
        mock_web3_class.to_checksum_address = lambda x: x
        
        mock_account_instance = Mock()
        mock_account_class.from_key.return_value = mock_account_instance
        
        # Act
        adapter = BlockchainAdapter()
        
        # Assert
        assert adapter.w3 == mock_web3_instance
        assert adapter.acct == mock_account_instance
        mock_web3_instance.is_connected.assert_called_once()
    
    @patch('app.services.blockchain.Web3')
    @patch('app.services.blockchain.Account')
    @patch.dict('os.environ', {
        'CHAIN_RPC_URL': 'http://localhost:8545',
        'CHAIN_SENDER_PRIVATE_KEY': '0x' + '1' * 64,
        'TRADE_LEDGER_ADDRESS': '0x5FbDB2315678afecb367f032d93F642f64180aa3'
    })
    def test_adapter_raises_error_on_connection_failure(self, mock_account_class, mock_web3_class):
        """Test that adapter raises error when blockchain connection fails"""
        # Arrange
        mock_web3_instance = Mock()
        mock_web3_instance.is_connected.return_value = False
        mock_web3_class.return_value = mock_web3_instance
        mock_web3_class.HTTPProvider = Mock()
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Chain RPC not reachable"):
            BlockchainAdapter()
    
    @patch('app.services.blockchain.Web3')
    @patch('app.services.blockchain.Account')
    @patch.dict('os.environ', {
        'CHAIN_RPC_URL': 'http://localhost:8545',
        'CHAIN_SENDER_PRIVATE_KEY': '0x' + '1' * 64,
        'TRADE_LEDGER_ADDRESS': '0x5FbDB2315678afecb367f032d93F642f64180aa3'
    })
    def test_record_trade_success(self, mock_account_class, mock_web3_class):
        """Test that record_trade successfully records a trade and returns tx hash"""
        # Arrange
        mock_web3_instance = Mock()
        mock_web3_instance.is_connected.return_value = True
        mock_web3_instance.eth.get_transaction_count.return_value = 5
        mock_web3_instance.to_wei.return_value = 1000000000
        
        tx_hash_bytes = b'\x12\x34\x56\x78' * 8
        mock_web3_instance.eth.send_raw_transaction.return_value = Mock(hex=lambda: tx_hash_bytes.hex())
        
        mock_web3_class.return_value = mock_web3_instance
        mock_web3_class.HTTPProvider = Mock()
        mock_web3_class.to_checksum_address = lambda x: x
        
        mock_account_instance = Mock()
        mock_account_instance.address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1"
        mock_signed_tx = Mock(rawTransaction=b"signed_data")
        mock_account_instance.sign_transaction.return_value = mock_signed_tx
        mock_account_class.from_key.return_value = mock_account_instance
        
        mock_contract = Mock()
        mock_function = Mock()
        mock_function.build_transaction.return_value = {'from': mock_account_instance.address}
        mock_contract.functions.recordTrade.return_value = mock_function
        mock_web3_instance.eth.contract.return_value = mock_contract
        
        adapter = BlockchainAdapter()
        
        # Act
        result = adapter.record_trade(
            trade_id=1,
            symbol="AAPL",
            price=150.50,
            quantity=10,
            buy_order_id=100,
            sell_order_id=200
        )
        
        # Assert
        assert result == tx_hash_bytes.hex()
        mock_contract.functions.recordTrade.assert_called_once_with(
            1, "AAPL", 15050, 10, 100, 200
        )
        mock_account_instance.sign_transaction.assert_called_once()
        mock_web3_instance.eth.send_raw_transaction.assert_called_once_with(b"signed_data")
    
    @patch('app.services.blockchain.Web3')
    @patch('app.services.blockchain.Account')
    @patch.dict('os.environ', {
        'CHAIN_RPC_URL': 'http://localhost:8545',
        'CHAIN_SENDER_PRIVATE_KEY': '0x' + '1' * 64,
        'TRADE_LEDGER_ADDRESS': '0x5FbDB2315678afecb367f032d93F642f64180aa3'
    })
    def test_price_converted_to_cents_correctly(self, mock_account_class, mock_web3_class):
        """Test that price is correctly converted to cents (integer)"""
        # Arrange
        mock_web3_instance = Mock()
        mock_web3_instance.is_connected.return_value = True
        mock_web3_instance.eth.get_transaction_count.return_value = 0
        mock_web3_instance.to_wei.return_value = 1000000000
        mock_web3_instance.eth.send_raw_transaction.return_value = Mock(hex=lambda: "0x123")
        
        mock_web3_class.return_value = mock_web3_instance
        mock_web3_class.HTTPProvider = Mock()
        mock_web3_class.to_checksum_address = lambda x: x
        
        mock_account_instance = Mock()
        mock_account_instance.sign_transaction.return_value = Mock(rawTransaction=b"data")
        mock_account_class.from_key.return_value = mock_account_instance
        
        mock_contract = Mock()
        mock_function = Mock()
        mock_function.build_transaction.return_value = {}
        mock_contract.functions.recordTrade.return_value = mock_function
        mock_web3_instance.eth.contract.return_value = mock_contract
        
        adapter = BlockchainAdapter()
        
        # Act
        adapter.record_trade(
            trade_id=1,
            symbol="TSLA",
            price=123.45,
            quantity=5,
            buy_order_id=10,
            sell_order_id=20
        )
        
        # Assert - price 123.45 should become 12345 cents
        mock_contract.functions.recordTrade.assert_called_once()
        call_args = mock_contract.functions.recordTrade.call_args[0]
        assert call_args[2] == 12345  # price in cents
    
    @patch('app.services.blockchain.Web3')
    @patch('app.services.blockchain.Account')
    @patch.dict('os.environ', {
        'CHAIN_RPC_URL': 'http://localhost:8545',
        'CHAIN_SENDER_PRIVATE_KEY': '0x' + '1' * 64,
        'TRADE_LEDGER_ADDRESS': '0x5FbDB2315678afecb367f032d93F642f64180aa3'
    })
    def test_record_trade_handles_web3_exception(self, mock_account_class, mock_web3_class):
        """Test that record_trade handles Web3 exceptions properly"""
        # Arrange
        mock_web3_instance = Mock()
        mock_web3_instance.is_connected.return_value = True
        mock_web3_instance.eth.get_transaction_count.return_value = 0
        mock_web3_instance.to_wei.return_value = 1000000000
        mock_web3_instance.eth.send_raw_transaction.side_effect = Web3Exception("Transaction failed")
        
        mock_web3_class.return_value = mock_web3_instance
        mock_web3_class.HTTPProvider = Mock()
        mock_web3_class.to_checksum_address = lambda x: x
        
        mock_account_instance = Mock()
        mock_account_instance.sign_transaction.return_value = Mock(rawTransaction=b"data")
        mock_account_class.from_key.return_value = mock_account_instance
        
        mock_contract = Mock()
        mock_function = Mock()
        mock_function.build_transaction.return_value = {}
        mock_contract.functions.recordTrade.return_value = mock_function
        mock_web3_instance.eth.contract.return_value = mock_contract
        
        adapter = BlockchainAdapter()
        
        # Act & Assert
        with pytest.raises(Web3Exception):
            adapter.record_trade(1, "AAPL", 100.0, 5, 1, 2)
    
    @patch('app.services.blockchain.Web3')
    @patch('app.services.blockchain.Account')
    @patch.dict('os.environ', {
        'CHAIN_RPC_URL': 'http://localhost:8545',
        'CHAIN_SENDER_PRIVATE_KEY': '0x' + '1' * 64,
        'TRADE_LEDGER_ADDRESS': '0x5FbDB2315678afecb367f032d93F642f64180aa3'
    })
    def test_nonce_increments_correctly(self, mock_account_class, mock_web3_class):
        """Test that nonce is fetched for each transaction"""
        # Arrange
        mock_web3_instance = Mock()
        mock_web3_instance.is_connected.return_value = True
        mock_web3_instance.eth.get_transaction_count.return_value = 42
        mock_web3_instance.to_wei.return_value = 1000000000
        mock_web3_instance.eth.send_raw_transaction.return_value = Mock(hex=lambda: "0xabc")
        
        mock_web3_class.return_value = mock_web3_instance
        mock_web3_class.HTTPProvider = Mock()
        mock_web3_class.to_checksum_address = lambda x: x
        
        mock_account_instance = Mock()
        mock_account_instance.address = "0x123"
        mock_account_instance.sign_transaction.return_value = Mock(rawTransaction=b"data")
        mock_account_class.from_key.return_value = mock_account_instance
        
        mock_contract = Mock()
        mock_function = Mock()
        mock_function.build_transaction.return_value = {}
        mock_contract.functions.recordTrade.return_value = mock_function
        mock_web3_instance.eth.contract.return_value = mock_contract
        
        adapter = BlockchainAdapter()
        
        # Act
        adapter.record_trade(1, "AAPL", 100.0, 5, 1, 2)
        
        # Assert
        mock_web3_instance.eth.get_transaction_count.assert_called_once_with("0x123")
        call_args = mock_function.build_transaction.call_args[0][0]
        assert call_args['nonce'] == 42