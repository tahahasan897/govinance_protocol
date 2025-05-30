import os
import json
import datetime
from collections import defaultdict
from pathlib import Path

from web3 import Web3
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# ────────────────────────────────────────────────────────
#  CONFIGURATION & STATE FILE
# ────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
STATE_FILE = SCRIPT_DIR / "state.json"

def load_state():
    if STATE_FILE.exists():
        try:
            data = STATE_FILE.read_text().strip()
            if data:
                return json.loads(data)
        except json.JSONDecodeError:
            # corrupted or empty state file
            pass
    # first run or unreadable state file
    return {"last_block": 0}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state))

# ────────────────────────────────────────────────────────
#  LOAD ENV
# ────────────────────────────────────────────────────────
# necessities.env is one level up from token_ai_tracker/
env_path = SCRIPT_DIR.parent / "necessities.env"
load_dotenv(dotenv_path=env_path)

RPC_URL = os.getenv("RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
ABI_FILE = os.getenv("ABI_FILE", "abis/Transcript.json")
DB_URL = os.getenv("DB_URL", "sqlite:///token_metrics.db")

# ────────────────────────────────────────────────────────
#  SET UP WEB3 & CONTRACT
# ────────────────────────────────────────────────────────
w3 = Web3(Web3.HTTPProvider(RPC_URL))
abi = json.load(open(ABI_FILE))
contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=abi
)

# ────────────────────────────────────────────────────────
def fetch_and_store():
    # 1) DB & Table setup
    engine = create_engine(DB_URL)

    # 2) Determine block range from state
    state = load_state()
    start_block = state["last_block"] + 1
    latest = w3.eth.block_number
    if start_block > latest:
        print("✅ No new blocks to process.")
        return

    # 3) Fetch only new Transfer events
    event_filter = contract.events.Transfer.create_filter(
        fromBlock=start_block,
        toBlock=latest
    )
    events = event_filter.get_all_entries()

    # 4) Aggregate by day
    daily_volume   = defaultdict(int)
    holders_by_day = defaultdict(set)

    for e in events:
        blk = w3.eth.get_block(e.blockNumber)
        ts = blk.timestamp
        day = datetime.date.fromtimestamp(ts).isoformat()

        daily_volume[day] += int(e.args.value)
        holders_by_day[day].add(e.args.to)
        if hasattr(e.args, "_from"):
            holders_by_day[day].add(e.args._from)

    # 5) Upsert into SQLite
    with engine.begin() as conn:
        for day, vol in daily_volume.items():
            conn.execute(text("""
                INSERT INTO daily_metrics (day, volume, holder_count)
                VALUES (:day, :volume, :holder_count)
                ON CONFLICT(day) DO UPDATE SET
                  volume = EXCLUDED.volume,
                  holder_count = EXCLUDED.holder_count
            """), {
                "day": day,
                "volume": str(vol),
                "holder_count": len(holders_by_day[day])
            })

    # 6) Update and save state
    state["last_block"] = latest
    save_state(state)
    print(f"✅ Processed blocks {start_block} → {latest}, saved state.json")

# ────────────────────────────────────────────────────────
if __name__ == "__main__":
    fetch_and_store()