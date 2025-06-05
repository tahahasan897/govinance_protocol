import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from eth_utils import event_abi_to_log_topic
from sqlalchemy import create_engine, text
from web3 import Web3

# Load configuration from .env file
SCRIPT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SCRIPT_DIR / 'necessities.env')

# Constants
TOKEN_DEPLOY_BLOCK = 8470000

INFURA_API_KEY = os.getenv('INFURA_API_KEY')
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')
if not INFURA_API_KEY or not CONTRACT_ADDRESS:
    raise SystemExit('INFURA_API_KEY and CONTRACT_ADDRESS must be set in .env')

STATE_PATH = SCRIPT_DIR / 'state.json'
ABI_PATH = SCRIPT_DIR / 'token_ai_tracker' / 'abis' / 'Transcript.json'
DB_URL = 'sqlite:///token_metrics.db'

# Load last processed block
def load_last_block(path: Path) -> int:
    try:
        with path.open() as f:
            data = json.load(f)
            return int(data.get('last_block', 0))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return 0


def save_last_block(path: Path, block: int) -> None:
    with path.open('w') as f:
        json.dump({'last_block': block}, f)


# Connect to web3 and contract
w3 = Web3(Web3.HTTPProvider(INFURA_API_KEY))
with open(ABI_PATH) as f:
    abi = json.load(f)
contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=abi)
TRANSFER_TOPIC = event_abi_to_log_topic(contract.events.Transfer().abi)

last_block = load_last_block(STATE_PATH)
start_block = max(last_block + 1, TOKEN_DEPLOY_BLOCK)
latest_block = w3.eth.block_number

if start_block > latest_block:
    print('Up-to-date. No new blocks.')
    raise SystemExit

print(f'🔄 Processing blocks {start_block:,} → {latest_block:,} …')
# Aggregation containers
daily_volume = defaultdict(int)
holders_by_day = defaultdict(set)
senders_by_day = defaultdict(set)
wallets_by_day = defaultdict(set)

span = 1000
block = start_block
raw_log_count = 0

while block <= latest_block:
    to_block = min(block + span - 1, latest_block)
    params = {
        'fromBlock': block,
        'toBlock': to_block,
        'address': contract.address,
        'topics': [TRANSFER_TOPIC],
    }
    retries = 0
    while True:
        try:
            logs = w3.eth.get_logs(params)
            break
        except Exception as exc:  # handle oversize or rate limit
            msg = str(exc).lower()
            if '429' in msg or 'rate limit' in msg:
                if retries >= 5:
                    raise
                delay = 2 ** retries
                time.sleep(delay)
                retries += 1
                continue
            if 'query returned more than' in msg or 'response size exceeded' in msg or 'too many results' in msg:
                if span == 1:
                    raise
                span = max(1, span // 2)
                to_block = min(block + span - 1, latest_block)
                params['toBlock'] = to_block
                continue
            raise

    for raw in logs:
        event = contract.events.Transfer().process_log(raw)
        from_addr = event['args']['from'].lower()
        to_addr = event['args']['to'].lower()
        value = int(event['args']['value']) // 10**18
        blk_ts = w3.eth.get_block(raw['blockNumber']).timestamp
        day = datetime.fromtimestamp(blk_ts, timezone.utc).strftime('%Y-%m-%d')

        daily_volume[day] += value
        holders_by_day[day].update([from_addr, to_addr])
        senders_by_day[day].add(from_addr)
        wallets_by_day[day].update([from_addr, to_addr])

    raw_log_count += len(logs)
    block = to_block + 1

engine = create_engine(DB_URL)
with engine.begin() as conn:
    for day in sorted(daily_volume.keys()):
        conn.execute(
            text(
                """
                INSERT INTO daily_metrics(day, volume, holder_count, unique_senders, active_wallets)
                VALUES (:day, :volume, :holder_count, :unique_senders, :active_wallets)
                ON CONFLICT(day) DO UPDATE SET
                    volume=excluded.volume,
                    holder_count=excluded.holder_count,
                    unique_senders=excluded.unique_senders,
                    active_wallets=excluded.active_wallets;
                """
            ),
            {
                'day': day,
                'volume': str(daily_volume[day]),
                'holder_count': len(holders_by_day[day]),
                'unique_senders': len(senders_by_day[day]),
                'active_wallets': len(wallets_by_day[day]),
            }
        )

save_last_block(STATE_PATH, latest_block)
print(f'➡️  Fetched {raw_log_count} raw Transfer logs.')
print(f'✅ Ingest complete – bookmark saved at block {latest_block:,}.')