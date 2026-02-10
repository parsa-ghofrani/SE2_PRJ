import json
import os
from pathlib import Path

from eth_account import Account
from solcx import compile_standard, install_solc, get_installed_solc_versions
from web3 import Web3

SOLC_VERSION = "0.8.19"
ARTIFACT_PATH = Path("contracts/artifacts/TradeLedger.json")


def main():
    rpc = os.environ["CHAIN_RPC_URL"]
    pk = os.environ["CHAIN_SENDER_PRIVATE_KEY"]

    w3 = Web3(Web3.HTTPProvider(rpc))
    assert w3.is_connected(), "Chain RPC not reachable"

    acct = Account.from_key(pk)

    # Install solc if missing
    installed = {str(v) for v in get_installed_solc_versions()}
    if SOLC_VERSION not in installed:
        install_solc(SOLC_VERSION)

    with open("contracts/TradeLedger.sol", "r", encoding="utf-8") as f:
        source = f.read()

    compiled = compile_standard(
        {
            "language": "Solidity",
            "sources": {"TradeLedger.sol": {"content": source}},
            "settings": {"outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}}},
        },
        solc_version=SOLC_VERSION,
    )

    data = compiled["contracts"]["TradeLedger.sol"]["TradeLedger"]
    abi = data["abi"]
    bytecode = data["evm"]["bytecode"]["object"]

    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    nonce = w3.eth.get_transaction_count(acct.address)
    tx = Contract.constructor().build_transaction(
        {
            "from": acct.address,
            "nonce": nonce,
            "gas": 2_000_000,
            "gasPrice": w3.to_wei("1", "gwei"),
        }
    )

    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    address = receipt.contractAddress
    print("TRADE_LEDGER_ADDRESS=" + address)

    # Save artifact (ABI + address)
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(
        json.dumps({"address": address, "abi": abi}, indent=2),
        encoding="utf-8",
    )
    print(f"Saved artifact -> {ARTIFACT_PATH}")


if __name__ == "__main__":
    main()
