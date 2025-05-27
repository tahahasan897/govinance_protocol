import os
import json
import datetime
from collections import defaultdict
from pathlib import Path
from web3 import Web3
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load env from project root
env_path = Path(__file__).resolve().parent.parent / "necessities.env"
load_dotenv(dotenv_path=env_path)

# Environment variables
every_rpc = os.getenv("RPC_URL")
contract_address = os.getenv("CONTRACT_ADDRESS")
abi_file = os.getenv("ABI_FILE", "abis/Transcript.json")
db_url = os.getenv("DB_URL", "sqlite:///" + str(Path(__file__).resolve().parent / "token_metrics.db"))

# Setup Web3 and contract
w3 = Web3(Web3.HTTPProvider(every_rpc))
abi = json.load(open(abi_file))
contract = w3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)

def fetch_and_store():
    # Initialize database and table
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS daily_metrics (
                day TEXT PRIMARY KEY,
                volume TEXT,
                holder_count INTEGER
            )
        """))

    # Determine block range
    latest = w3.eth.block_number
    start_block = max(latest - 1000, 0)

    # Fetch events using correct create_filter
    event_filter = contract.events.Transfer.create_filter(
        fromBlock=start_block,
        toBlock=latest
    )
    events = event_filter.get_all_entries()

    # Aggregate daily metrics
    daily_volume = defaultdict(int)
    holders = set()
    for e in events:
        block = w3.eth.get_block(e.blockNumber)
        timestamp = block.timestamp
        day = datetime.date.fromtimestamp(timestamp).isoformat()
        daily_volume[day] += int(e.args.value)
        holders.add(e.args.to)

    # Store metrics
    with engine.begin() as conn:
        for day, volume in daily_volume.items():
            conn.execute(text("""
                INSERT INTO daily_metrics (day, volume, holder_count)
                VALUES (:day, :volume, :holder_count)
                ON CONFLICT(day) DO UPDATE SET
                  volume = EXCLUDED.volume,
                  holder_count = EXCLUDED.holder_count
            """), {
                "day": day,
                "volume": str(volume),
                "holder_count": len(holders)
            })

if __name__ == "__main__":
    fetch_and_store()
    print("✅ Fetched and saved daily metrics.")