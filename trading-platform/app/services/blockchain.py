from __future__ import annotations

import os
from web3 import Web3
from eth_account import Account


TRADE_LEDGER_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": False, "internalType": "uint256", "name": "tradeId", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "symbol", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "price", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "quantity", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "buyOrderId", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "sellOrderId", "type": "uint256"},
        ],
        "name": "TradeRecorded",
        "type": "event",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "tradeId", "type": "uint256"},
            {"internalType": "string", "name": "symbol", "type": "string"},
            {"internalType": "uint256", "name": "price", "type": "uint256"},
            {"internalType": "uint256", "name": "quantity", "type": "uint256"},
            {"internalType": "uint256", "name": "buyOrderId", "type": "uint256"},
            {"internalType": "uint256", "name": "sellOrderId", "type": "uint256"},
        ],
        "name": "recordTrade",
        "outputs": [],
        "stateMutability": "nonpayable",
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

    def record_trade(
        self,
        trade_id: int,
        symbol: str,
        price: float,
        quantity: int,
        buy_order_id: int,
        sell_order_id: int,
    ) -> str:
        # store price as integer "cents" on chain
        price_int = int(round(price * 100))

        nonce = self.w3.eth.get_transaction_count(self.acct.address)
        tx = self.contract.functions.recordTrade(
            trade_id,
            symbol,
            price_int,
            quantity,
            buy_order_id,
            sell_order_id,
        ).build_transaction(
            {
                "from": self.acct.address,
                "nonce": nonce,
                "gas": 300_000,
                "gasPrice": self.w3.to_wei("1", "gwei"),
            }
        )

        signed = self.acct.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()


blockchain_adapter = BlockchainAdapter()
