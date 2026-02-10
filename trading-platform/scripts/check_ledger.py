import json
import os
from pathlib import Path

from web3 import Web3

ARTIFACT_PATH = Path("contracts/artifacts/TradeLedger.json")


def main():
    rpc = os.environ["CHAIN_RPC_URL"]
    w3 = Web3(Web3.HTTPProvider(rpc))
    assert w3.is_connected(), "Chain RPC not reachable"

    artifact = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    address = artifact["address"]
    abi = artifact["abi"]

    c = w3.eth.contract(address=address, abi=abi)

    n = c.functions.count().call()
    print("ledger.count() =", n)

    # print last up to 10 trades
    start = max(0, n - 10)
    for i in range(start, n):
        t = c.functions.getTrade(i).call()
        tradeId, symbol, priceCents, qty, buyId, sellId, ts = t
        print(
            f"[{i}] tradeId={tradeId} symbol={symbol} price=${priceCents/100:.2f} "
            f"qty={qty} buy={buyId} sell={sellId} ts={ts}"
        )


if __name__ == "__main__":
    main()
