import os
import sys
import json
import time
import datetime
from collections import defaultdict
from pathlib import Path

from web3 import Web3
from web3.exceptions import BlockNotFound, TransactionNotFound
from eth_utils import event_abi_to_log_topic
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

"""
Token‑AI Tracker  ·  Daily on‑chain metrics aggregator
-----------------------------------------------------
* Dynamically sizes each `eth_getLogs` request so you **never** blow the
  provider’s max‑logs limit, yet keep the request count tiny.
* Retries with exponential back‑off on rate‑limit (HTTP 429) or oversize
  errors.
* Stores last‑processed block in `state.json`, so each run fetches only
  new data.
"""

# ╭─────────────────────────────────────────────────────╮
# │ CONFIGURATION & STATE FILE                         │
# ╰─────────────────────────────────────────────────────╯

SCRIPT_DIR = Path(__file__).resolve().parent
STATE_FILE = SCRIPT_DIR / "state.json"

# These spans are tuned for Alchemy free tier (10 k log cap / 60 RPM)
START_SPAN = 10_000   # optimistic first try (blocks per call)
MIN_SPAN   = 50       # don’t go below this even on dense days
BACKOFF    = 2.0      # seconds, doubled each retry
MAX_RETRY  = 5        # max back‑off retries before bailing


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            print("⚠️  state.json corrupted – resetting bookmark.")
    return {"last_block": 0}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state))

# ╭─────────────────────────────────────────────────────╮
# │ ENV + WEB3 SETUP                                   │
# ╰─────────────────────────────────────────────────────╯

load_dotenv(SCRIPT_DIR.parent / "necessities.env")
INFURA_API_KEY          = os.getenv("INFURA_API_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
ABI_FILE         = os.getenv("ABI_FILE", "abis/Transcript.json")
DB_URL           = os.getenv("DB_URL", "sqlite:///token_metrics.db")

for var in ("INFURA_API_KEY", "CONTRACT_ADDRESS"):
    if not globals()[var]:
        sys.exit(f"❌ {var} missing in .env; aborting.")

w3 = Web3(Web3.HTTPProvider(INFURA_API_KEY))
if not w3.is_connected():
    sys.exit("❌ RPC endpoint unreachable.")

abi      = json.load(open(ABI_FILE))
contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=abi)

# Precompute the transfer event using the ABI for accuracy
transfer_abi = contract.events.Transfer().abi
TRANSFER_TOPIC = Web3.to_hex(event_abi_to_log_topic(transfer_abi))

# ╭─────────────────────────────────────────────────────╮
# │ HELPERS                                            │
# ╰─────────────────────────────────────────────────────╯

def adaptive_get_logs(from_block: int, to_block: int):
    """Yield logs in the range, shrinking span on oversize errors."""
    span = to_block - from_block + 1
    cur  = from_block
    while cur <= to_block:
        try_span = min(span, to_block - cur + 1)
        retries  = 0
        while True:
            try:
                logs = w3.eth.get_logs({
                    "fromBlock": Web3.to_hex(cur),
                    "toBlock":   Web3.to_hex(cur + try_span - 1),
                    "address":   Web3.to_checksum_address(str(contract.address)),
                    "topics":    [TRANSFER_TOPIC]
                })
                yield from logs
                cur += try_span
                break  # success, move to next slice
            except ValueError as e:
                msg = str(e)
                if "response size exceeded" in msg and try_span > MIN_SPAN:
                    try_span //= 2  # slice was too big; halve span and retry immediately
                    continue
                if "429" in msg or "rate limit" in msg:
                    if retries >= MAX_RETRY:
                        raise
                    sleep_time = BACKOFF * (2 ** retries)
                    time.sleep(sleep_time)
                    retries += 1
                    continue
                raise  # unexpected error – bubble up

# ╭─────────────────────────────────────────────────────╮
# │ MAIN INGEST FUNCTION                               │
# ╰─────────────────────────────────────────────────────╯

def fetch_and_store():
    engine = create_engine(DB_URL)

    state        = load_state()
    start_block  = state["last_block"] + 1
    latest_block = w3.eth.block_number

    if start_block > latest_block:
        print("✅ Up-to-date. No new blocks.")
        return

    print(f"🔄 Processing blocks {start_block:,} → {latest_block:,} …")

    daily_volume      = defaultdict(int)
    holders_by_day    = defaultdict(set)
    senders_by_day    = defaultdict(set)
    wallets_by_day    = defaultdict(set)

    # Stream logs adaptively
    for log in adaptive_get_logs(start_block, latest_block):
        blk_ts = w3.eth.get_block(log.blockNumber).timestamp
        day    = datetime.datetime.fromtimestamp(
            blk_ts, tz=datetime.timezone.utc
        ).date().isoformat()

        # ── Decode the raw log into a Transfer event ──────────────────────────────────
        event = contract.events.Transfer().processLog(log)
        frm   = event.args["from"].lower()
        to    = event.args["to"].lower()
        value = event.args["value"]

        daily_volume[day]   += value
        holders_by_day[day].update([frm, to])
        senders_by_day[day].add(frm)
        wallets_by_day[day].update([frm, to])

    with engine.begin() as conn:
        UPSERT = text("""
            INSERT INTO daily_metrics (day, volume, holder_count, unique_senders, active_wallets)
            VALUES (:day, :volume, :holder_count, :unique_senders, :active_wallets)
            ON CONFLICT(day) DO UPDATE SET
                volume          = EXCLUDED.volume,
                holder_count    = EXCLUDED.holder_count,
                unique_senders  = EXCLUDED.unique_senders,
                active_wallets  = EXCLUDED.active_wallets;""")
        for day in sorted(daily_volume):
            conn.execute(UPSERT, {
                "day":            day,
                "volume":         daily_volume[day],
                "holder_count":   len(holders_by_day[day]),
                "unique_senders": len(senders_by_day[day]),
                "active_wallets": len(wallets_by_day[day]),
            })

    state["last_block"] = latest_block
    save_state(state)
    print(f"✅ Ingest complete – bookmark saved at block {latest_block:,}.")