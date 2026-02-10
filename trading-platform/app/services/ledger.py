import json
import os
from pathlib import Path
from typing import Optional

from eth_account import Account
from web3 import Web3

from app.models.trade import Trade

ARTIFACT_PATH = Path("contracts/artifacts/TradeLedger.json")


def _price_to_cents(price: float) -> int:
    # avoid float weirdness
    return int(round(price * 100))


class TradeLedgerClient:
    def __init__(self) -> None:
        rpc = os.environ["CHAIN_RPC_URL"]
        pk = os.environ["CHAIN_SENDER_PRIVATE_KEY"]

        self.w3 = Web3(Web3.HTTPProvider(rpc))
        if not self.w3.is_connected():
            raise RuntimeError("Chain RPC not reachable")

        self.acct = Account.from_key(pk)

        artifact = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
        self.contract_address = artifact["address"]
        self.abi = artifact["abi"]

        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)

    def record_trade(self, trade: Trade) -> str:
        """
        Idempotent on app side:
        - if trade already has tx hash -> do nothing
        - on-chain also prevents duplicates by tradeId
        """
        if trade.blockchain_tx_hash:
            return trade.blockchain_tx_hash

        nonce = self.w3.eth.get_transaction_count(self.acct.address)

        tx = self.contract.functions.recordTrade(
            int(trade.id),
            str(trade.symbol),
            _price_to_cents(float(trade.price)),
            int(trade.quantity),
            int(trade.buy_order_id),
            int(trade.sell_order_id),
        ).build_transaction(
            {
                "from": self.acct.address,
                "nonce": nonce,
                "gas": 200_000,
                "gasPrice": self.w3.to_wei("1", "gwei"),
            }
        )

        signed = self.acct.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        # status 1 = success
        if receipt.get("status") != 1:
            raise RuntimeError("TradeLedger tx failed")

        return tx_hash.hex()


# singleton (simple for this phase)
ledger_client: Optional[TradeLedgerClient] = None


def get_ledger_client() -> TradeLedgerClient:
    global ledger_client
    if ledger_client is None:
        ledger_client = TradeLedgerClient()
    return ledger_client
