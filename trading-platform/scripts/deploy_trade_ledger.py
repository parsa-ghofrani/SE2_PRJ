import json
import os
from pathlib import Path

from eth_account import Account
from solcx import compile_standard, install_solc, get_installed_solc_versions
from web3 import Web3

SOLC_VERSION = "0.8.19"
ARTIFACT_PATH = Path("contracts/artifacts/TradeLedger.json")


def main():
    # Use environment variables with defaults
    rpc = os.environ.get("CHAIN_RPC_URL", "http://chain:8545")
    pk = os.environ.get("CHAIN_SENDER_PRIVATE_KEY", "")

    print(f"🔗 Connecting to blockchain at {rpc}...")
    w3 = Web3(Web3.HTTPProvider(rpc))
    assert w3.is_connected(), "❌ Chain RPC not reachable"
    print(f"✅ Connected! Block number: {w3.eth.block_number}")

    # Use Geth dev account if available (it has pre-funded balance)
    if len(w3.eth.accounts) > 0:
        sender_address = w3.eth.accounts[0]
        print(f"🔑 Using Geth dev account: {sender_address}")
        balance = w3.eth.get_balance(sender_address)
        print(f"💰 Balance: {w3.from_wei(balance, 'ether')} ETH")
        use_geth_account = True
    else:
        # Fallback to private key
        print("🔑 Using private key from environment...")
        acct = Account.from_key(pk)
        sender_address = acct.address
        balance = w3.eth.get_balance(sender_address)
        print(f"💰 Account: {sender_address}")
        print(f"💰 Balance: {w3.from_wei(balance, 'ether')} ETH")
        use_geth_account = False
        
        if balance == 0:
            print("❌ Account has no balance! Cannot deploy.")
            return

    # Install solc if missing
    print("🔨 Checking Solidity compiler...")
    installed = {str(v) for v in get_installed_solc_versions()}
    if SOLC_VERSION not in installed:
        print(f"📥 Installing solc {SOLC_VERSION}...")
        install_solc(SOLC_VERSION)
        print("✅ Solc installed")

    print("📜 Compiling contract...")
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
    print("✅ Contract compiled")

    print("🚀 Deploying contract...")
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    if use_geth_account:
        # Use Geth account (simpler, no signing needed)
        tx_hash = Contract.constructor().transact({'from': sender_address})
        print(f"📤 Transaction sent: {tx_hash.hex()}")
    else:
        # Use private key (requires signing)
        nonce = w3.eth.get_transaction_count(sender_address)
        tx = Contract.constructor().build_transaction(
            {
                "from": sender_address,
                "nonce": nonce,
                "gas": 2_000_000,
                "gasPrice": w3.to_wei("1", "gwei"),
            }
        )

        signed = acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        print(f"📤 Transaction sent: {tx_hash.hex()}")

    print("⏳ Waiting for confirmation...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    if receipt['status'] == 0:
        print("❌ Deployment failed!")
        return

    address = receipt.contractAddress
    print(f"\n{'='*60}")
    print(f"✅ CONTRACT DEPLOYED SUCCESSFULLY!")
    print(f"{'='*60}")
    print(f"📍 Address: {address}")
    print(f"🔗 Block: {receipt['blockNumber']}")
    print(f"⛽ Gas Used: {receipt['gasUsed']}")
    print(f"{'='*60}\n")

    # Save artifact (ABI + address)
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(
        json.dumps({"address": address, "abi": abi}, indent=2),
        encoding="utf-8",
    )
    print(f"💾 Saved artifact -> {ARTIFACT_PATH}")
    print(f"\n✅ Add this to your .env file:")
    print(f"TRADE_LEDGER_ADDRESS={address}\n")


if __name__ == "__main__":
    main()