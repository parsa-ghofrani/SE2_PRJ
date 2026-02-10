# app/services/siwe.py
from __future__ import annotations

import os
import re
import secrets
from dataclasses import dataclass
from typing import Optional

from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3


# Minimal EIP-4361 parser (enough for a course project)
# Message format example:
# <domain> wants you to sign in with your Ethereum account:
# <address>
#
# <statement?>
#
# URI: <uri>
# Version: 1
# Chain ID: <chain_id>
# Nonce: <nonce>
# Issued At: <iso8601>
#
SIWE_RE = re.compile(
    r"^(?P<domain>.+?) wants you to sign in with your Ethereum account:\n"
    r"(?P<address>0x[a-fA-F0-9]{40})\n\n"
    r"(?P<statement>.*?\n\n)?"
    r"URI: (?P<uri>.+)\n"
    r"Version: (?P<version>\d+)\n"
    r"Chain ID: (?P<chain_id>\d+)\n"
    r"Nonce: (?P<nonce>[A-Za-z0-9]{8,})\n"
    r"Issued At: (?P<issued_at>.+)$",
    re.DOTALL,
)


@dataclass
class SiweMessage:
    domain: str
    address: str
    uri: str
    version: int
    chain_id: int
    nonce: str
    issued_at: str
    statement: Optional[str] = None


def generate_nonce() -> str:
    # 16 chars base62-ish
    return secrets.token_urlsafe(12)[:16]


def parse_siwe_message(message: str) -> SiweMessage:
    m = SIWE_RE.match(message.strip())
    if not m:
        raise ValueError("Invalid SIWE message format")

    statement = m.group("statement")
    if statement:
        statement = statement.strip()

    return SiweMessage(
        domain=m.group("domain").strip(),
        address=Web3.to_checksum_address(m.group("address")),
        uri=m.group("uri").strip(),
        version=int(m.group("version")),
        chain_id=int(m.group("chain_id")),
        nonce=m.group("nonce").strip(),
        issued_at=m.group("issued_at").strip(),
        statement=statement,
    )


def recover_address(message: str, signature: str) -> str:
    # SIWE uses EIP-191 personal_sign style. In web3.py:
    # encode_defunct(text=message) matches personal_sign.
    msg = encode_defunct(text=message)
    recovered = Account.recover_message(msg, signature=signature)
    return Web3.to_checksum_address(recovered)
