# src/data/onchain_client.py

"""
Module: Elite On-Chain Client (V7 - Stable Vault Path + Real Block Time)
Description:
- Parses native ETH and selected ERC-20 transfers
- Stores verified institutional volume in a local SQLite database
- Uses one stable project-level DB path
- Saves the real block timestamp, not the local scan time
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# GLOBAL PROJECT PATHS
# ==========================================
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[1]
DB_PATH = PROJECT_ROOT / "data" / "db" / "whale_data.db"

# ==========================================
# COMPONENT 1: THE DATABASE VAULT
# ==========================================
class WhaleVault:
    def __init__(self, db_name=DB_PATH):
        """
        Initializes the SQLite connection and creates schema if needed.
        Uses a stable project-level database path.
        """
        self.db_path = Path(db_name)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._build_schema()

    def _build_schema(self):
        """Creates the structural table for institutional transfers."""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS institutional_transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                block_number INTEGER,
                asset_type TEXT,
                amount REAL,
                sender_address TEXT,
                receiver_address TEXT,
                transaction_hash TEXT UNIQUE
            )
            """
        )
        self.conn.commit()

    def save_whale(
        self,
        block_timestamp: str,
        block_number: int,
        asset: str,
        amount: float,
        sender: str,
        receiver: str,
        tx_hash: str,
    ):
        """
        Saves a verified whale transaction to the database.
        """
        try:
            self.cursor.execute(
                """
                INSERT OR IGNORE INTO institutional_transfers
                (timestamp, block_number, asset_type, amount, sender_address, receiver_address, transaction_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (block_timestamp, block_number, asset, amount, sender, receiver, tx_hash),
            )
            self.conn.commit()
            print("      [VAULT] -> Transaction securely saved to Database.")
        except Exception as e:
            print(f"      [VAULT ERROR] -> Failed to save: {e}")

    def close(self):
        """Closes the database connection cleanly."""
        self.conn.close()


# ==========================================
# COMPONENT 2: THE ON-CHAIN ENGINE
# ==========================================
class EVMClient:
    def __init__(self):
        self.rpc_url = os.getenv("ETH_RPC_URL")
        if not self.rpc_url:
            raise ValueError("CRITICAL ERROR: ETH_RPC_URL missing in environment.")

        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

        if not self.w3.is_connected():
            raise ConnectionError("CRITICAL ERROR: Failed to connect to Ethereum RPC.")

        self.vault = WhaleVault()

        self.TOKEN_DIRECTORY = {
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48".lower(): ["USDC", 6],
            "0xdAC17F958D2ee523a2206206994597C13D831ec7".lower(): ["USDT", 6],
            "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599".lower(): ["WBTC", 8],
        }

        self.TRANSFER_METHOD_ID = "0xa9059cbb"

    def fetch_block_data(self, block_number: int):
        print(f"[*] Downloading Block {block_number}...")
        return self.w3.eth.get_block(block_number, full_transactions=True)

    def verify_success(self, tx_hash) -> bool:
        receipt = self.w3.eth.get_transaction_receipt(tx_hash)
        return receipt["status"] == 1

    def parse_erc20_transfer(self, tx_input_hex: str, decimals: int):
        """
        Parses calldata for a plain ERC-20 transfer(address,uint256).
        Returns token amount and receiver address.
        """
        if len(tx_input_hex) >= 138:
            raw_amount_hex = tx_input_hex[74:138]
            receiver_raw = tx_input_hex[34:74]
            receiver_address = "0x" + receiver_raw

            try:
                raw_amount_int = int(raw_amount_hex, 16)
                token_amount = raw_amount_int / (10 ** decimals)
                return token_amount, receiver_address
            except ValueError:
                return 0, None

        return 0, None

    def _format_block_timestamp(self, block_data) -> str:
        """
        Converts the real block timestamp into UTC string format.
        """
        return datetime.fromtimestamp(
            block_data["timestamp"], tz=timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S")

    def scan_for_whales(self, block_data, min_usd_value: float = 100000.0):
        """
        Scans one block for large native ETH and selected ERC-20 transfers.
        """
        print(f"[*] Commencing Deep Whale Scan (Threshold: ${min_usd_value:,.2f})...")

        whale_count = 0
        block_num = block_data.number
        block_timestamp = self._format_block_timestamp(block_data)

        for tx in block_data.transactions:
            # ------------------------------------------
            # 1. NATIVE ETH WHALES
            # ------------------------------------------
            eth_value = float(self.w3.from_wei(tx["value"], "ether"))

            if eth_value >= 30.0:
                if self.verify_success(tx["hash"]):
                    whale_count += 1
                    print(f"\n   🐳 [NATIVE WHALE]: {eth_value:.2f} ETH")

                    self.vault.save_whale(
                        block_timestamp=block_timestamp,
                        block_number=block_num,
                        asset="ETH",
                        amount=eth_value,
                        sender=tx["from"],
                        receiver=tx["to"],
                        tx_hash=tx["hash"].hex(),
                    )
                continue

            # ------------------------------------------
            # 2. SELECTED ERC-20 WHALES
            # ------------------------------------------
            if tx["to"]:
                contract_address = tx["to"].lower()

                if contract_address in self.TOKEN_DIRECTORY:
                    token_name, decimals = self.TOKEN_DIRECTORY[contract_address]
                    input_hex = self.w3.to_hex(tx["input"])

                    if input_hex.startswith(self.TRANSFER_METHOD_ID):
                        token_amount, true_receiver = self.parse_erc20_transfer(input_hex, decimals)

                        if token_amount >= min_usd_value:
                            if self.verify_success(tx["hash"]):
                                whale_count += 1
                                print(f"\n   🐋 [TRUE {token_name} WHALE]: {token_amount:,.2f} {token_name}")

                                self.vault.save_whale(
                                    block_timestamp=block_timestamp,
                                    block_number=block_num,
                                    asset=token_name,
                                    amount=token_amount,
                                    sender=tx["from"],
                                    receiver=true_receiver,
                                    tx_hash=tx["hash"].hex(),
                                )

        print(f"\n[*] Scan Complete. True Whales Saved to Vault: {whale_count}")


# ==========================================
# EXECUTION
# ==========================================
if __name__ == "__main__":
    client = EVMClient()
    latest = client.w3.eth.block_number

    if latest > 0:
        block = client.fetch_block_data(latest)
        client.scan_for_whales(block, min_usd_value=100000.0)
        client.vault.close()