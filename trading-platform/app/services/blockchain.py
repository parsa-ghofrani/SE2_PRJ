from __future__ import annotations

import os
from web3 import Web3
from eth_account import Account


TRADE_LEDGER_ABI = [
    # Events
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "internalType": "uint256", "name": "tradeId", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "symbol", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "priceCents", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "quantity", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "buyOrderId", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "sellOrderId", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "name": "TradeRecorded",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "previousOwner", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "newOwner", "type": "address"},
        ],
        "name": "OwnershipTransferred",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "user", "type": "address"},
            {"indexed": False, "internalType": "uint8", "name": "level", "type": "uint8"},
        ],
        "name": "AccessLevelChanged",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "description", "type": "string"},
            {"indexed": True, "internalType": "address", "name": "reporter", "type": "address"},
        ],
        "name": "IncidentLogged",
        "type": "event",
    },
    # Functions
    {
        "inputs": [
            {"internalType": "uint256", "name": "tradeId", "type": "uint256"},
            {"internalType": "string", "name": "symbol", "type": "string"},
            {"internalType": "uint256", "name": "priceCents", "type": "uint256"},
            {"internalType": "uint256", "name": "quantity", "type": "uint256"},
            {"internalType": "uint256", "name": "buyOrderId", "type": "uint256"},
            {"internalType": "uint256", "name": "sellOrderId", "type": "uint256"},
        ],
        "name": "recordTrade",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "owner",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "getAccessLevel",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "user", "type": "address"},
            {"internalType": "uint8", "name": "level", "type": "uint8"},
        ],
        "name": "setAccessLevel",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "string", "name": "description", "type": "string"}],
        "name": "logIncident",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "count",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "index", "type": "uint256"}],
        "name": "getTrade",
        "outputs": [
            {"internalType": "uint256", "name": "tradeId", "type": "uint256"},
            {"internalType": "string", "name": "symbol", "type": "string"},
            {"internalType": "uint256", "name": "priceCents", "type": "uint256"},
            {"internalType": "uint256", "name": "quantity", "type": "uint256"},
            {"internalType": "uint256", "name": "buyOrderId", "type": "uint256"},
            {"internalType": "uint256", "name": "sellOrderId", "type": "uint256"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "uint256", "name": "tradeId", "type": "uint256"}],
        "name": "exists",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
]


class BlockchainAdapter:
    def __init__(self) -> None:
        rpc_url = os.environ["CHAIN_RPC_URL"]
        private_key = os.environ["CHAIN_SENDER_PRIVATE_KEY"]
        contract_address = os.environ["TRADE_LEDGER_ADDRESS"]

        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.w3.is_connected():
            raise RuntimeError("Chain RPC not reachable")

        self.acct = Account.from_key(private_key)
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=TRADE_LEDGER_ABI,
        )

    def get_owner(self) -> str:
        return self.contract.functions.owner().call()

    def get_access_level(self, address: str) -> int:
        """""
        0: NONE, 1: READER, 2: RECORDER, 3: ADMIN
        """
        checksum_addr = Web3.to_checksum_address(address)
        return self.contract.functions.getAccessLevel(checksum_addr).call()

    def set_access_level(self, user_address: str, level: int) -> str:
        checksum_addr = Web3.to_checksum_address(user_address)
        
        nonce = self.w3.eth.get_transaction_count(self.acct.address)
        tx = self.contract.functions.setAccessLevel(
            checksum_addr, level
        ).build_transaction({
            "from": self.acct.address,
            "nonce": nonce,
            "gas": 100_000,
            "gasPrice": self.w3.to_wei("1", "gwei"),
        })

        signed = self.acct.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    def log_incident(self, description: str) -> str:
        nonce = self.w3.eth.get_transaction_count(self.acct.address)
        tx = self.contract.functions.logIncident(description).build_transaction({
            "from": self.acct.address,
            "nonce": nonce,
            "gas": 150_000,
            "gasPrice": self.w3.to_wei("1", "gwei"),
        })

        signed = self.acct.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    def record_trade(
        self,
        trade_id: int,
        symbol: str,
        price: float,
        quantity: int,
        buy_order_id: int,
        sell_order_id: int,
    ) -> str:
        price_int = int(round(price * 100))

        nonce = self.w3.eth.get_transaction_count(self.acct.address)
        tx = self.contract.functions.recordTrade(
            trade_id,
            symbol,
            price_int,
            quantity,
            buy_order_id,
            sell_order_id,
        ).build_transaction({
            "from": self.acct.address,
            "nonce": nonce,
            "gas": 300_000,
            "gasPrice": self.w3.to_wei("1", "gwei"),
        })

        signed = self.acct.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()