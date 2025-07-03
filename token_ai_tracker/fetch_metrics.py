import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv
from eth_utils import event_abi_to_log_topic
from sqlalchemy import create_engine, text
from web3 import Web3

# ─────── Load configuration from .env ───────
SCRIPT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SCRIPT_DIR / 'necessities.env')

DEPLOYER                = os.getenv('DEPLOYER')
RPC_URL                 = os.getenv('RPC_URL')
WALLET_ADDRESS          = os.getenv('WALLET_ADDRESS')
TOKEN_CONTRACT_ADDRESS  = os.getenv('TOKEN_CONTRACT_ADDRESS')
WALLET_CONTRACT_ADDRESS = os.getenv('WALLET_CONTRACT_ADDRESS')
TOKEN_ABI_FILE          = os.getenv('TOKEN_ABI_FILE')
WALLET_ABI_FILE         = os.getenv('WALLET_ABI_FILE')
DB_PATH                 = os.getenv('DB_URL', 'token_metrics.db')
STATE_PATH              = SCRIPT_DIR / 'state.json'

if not all([RPC_URL, TOKEN_CONTRACT_ADDRESS, WALLET_CONTRACT_ADDRESS, TOKEN_ABI_FILE, WALLET_ABI_FILE]):
    raise SystemExit('RPC_URL, TOKEN_CONTRACT_ADDRESS, WALLET_CONTRACT_ADDRESS, TOKEN_ABI_FILE, WALLET_ABI_FILE must be set in .env')

# ─────── Connect to web3 & contracts ───────
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# ─────── Constants ───────
# zkSync closest block to start from there (It needs to be adjusted in the future runtime). 
START_DEPLOY_BLOCK = (w3.eth.block_number) - 50

# ─────── Load last processed block ───────
def load_last_block(path: Path) -> int:
    try:
        with path.open() as f:
            return int(json.load(f).get('last_block', 0))
    except:
        return 0

def save_last_block(path: Path, block: int) -> None:
    with path.open('w') as f:
        json.dump({'last_block': block}, f)

with open(TOKEN_ABI_FILE) as f:
    token_abi = json.load(f)
with open(WALLET_ABI_FILE) as f:
    wallet_abi = json.load(f)

token_contract  = w3.eth.contract(address=Web3.to_checksum_address(TOKEN_CONTRACT_ADDRESS),  abi=token_abi)
wallet_contract = w3.eth.contract(address=Web3.to_checksum_address(WALLET_CONTRACT_ADDRESS), abi=wallet_abi)

TRANSFER_TOPIC = event_abi_to_log_topic(token_contract.events.Transfer().abi)
MINTING_HAPPENED_TOPIC = event_abi_to_log_topic({
    "anonymous": False,
    "inputs": [{"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"}],
    "name": "MintingHappened",
    "type": "event"
})
BURNING_HAPPENED_TOPIC = event_abi_to_log_topic({
    "anonymous": False,
    "inputs": [{"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"}],
    "name": "BurningHappened",
    "type": "event"
})

last_block   = load_last_block(STATE_PATH)
start_block  = max(last_block + 1, START_DEPLOY_BLOCK)
latest_block = w3.eth.block_number

if start_block > latest_block:
    print('Up-to-date. No new blocks.')
    raise SystemExit

print(f'🔄 Processing blocks {start_block:,} → {latest_block:,} …')

# ─────── Aggregation containers ───────
daily_volume     = defaultdict(float)
holders_by_day   = defaultdict(set)
senders_by_day   = defaultdict(set)
wallets_by_day   = defaultdict(set)
daily_minted     = defaultdict(float)
daily_burned     = defaultdict(float)

span  = 1_000
block = start_block
raw_log_count = 0

while block <= latest_block:
    to_block = min(block + span - 1, latest_block)
    params = {
        'fromBlock': block,
        'toBlock': to_block,
        'address': token_contract.address,
        'topics': None,  # Fetch all topics for this address
    }
    retries = 0
    while True:
        try:
            logs = w3.eth.get_logs(params)
            break
        except Exception as exc:
            msg = str(exc).lower()
            # rate-limit
            if 'rate limit' in msg or '429' in msg:
                if retries >= 5: raise
                time.sleep(2 ** retries)
                retries += 1
                continue
            # too many results
            if 'too many results' in msg or 'response size exceeded' in msg:
                if span == 1: raise
                span = max(1, span // 2)
                to_block = min(block + span - 1, latest_block)
                params['toBlock'] = to_block
                continue
            raise

    ai_funding_skipped = False

    for raw in logs:
        topic = raw['topics'][0]
        ts = w3.eth.get_block(raw['blockNumber']).timestamp
        day = datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d')

        if topic == TRANSFER_TOPIC:
            evt = token_contract.events.Transfer().process_log(raw)
            frm = evt['args']['from'].lower()
            to = evt['args']['to'].lower()
            val = int(evt['args']['value']) / 1e18

            # Skip initial AI EOA -> SmartAIWallet funding transfer (first only)
            if not ai_funding_skipped and frm == WALLET_ADDRESS.lower() and to == WALLET_CONTRACT_ADDRESS.lower():
                ai_funding_skipped = True
                continue

            # Skip mints (from zero address)
            if frm == '0x0000000000000000000000000000000000000000':
                continue
            # Skip burns (to zero address)
            if to == '0x0000000000000000000000000000000000000000':
                continue
            # Skip wallet <-> deployer transfers (both directions)
            if (frm == WALLET_CONTRACT_ADDRESS.lower() and to == DEPLOYER.lower()) or (frm == DEPLOYER.lower() and to == WALLET_CONTRACT_ADDRESS.lower()):
                continue
            # Skip transfers involving treasury (except deployer → user)
            if frm == WALLET_CONTRACT_ADDRESS.lower() or to == WALLET_CONTRACT_ADDRESS.lower():
                continue

            daily_volume[day] += val

            # Add non-deployer addresses to holders, senders, wallets
            if frm != DEPLOYER.lower():
                holders_by_day[day].add(frm)
                senders_by_day[day].add(frm)
                wallets_by_day[day].add(frm)
            if to != DEPLOYER.lower():
                holders_by_day[day].add(to)
                wallets_by_day[day].add(to)

        elif topic == MINTING_HAPPENED_TOPIC:
            amount = int.from_bytes(raw['data'], byteorder='big') / 1e18
            daily_minted[day] += amount

        elif topic == BURNING_HAPPENED_TOPIC:
            amount = int.from_bytes(raw['data'], byteorder='big') / 1e18
            daily_burned[day] += amount

    raw_log_count += len(logs)
    block = to_block + 1

# ─────── Ensure every day in range is present ───────
# Find the earliest and latest day in the block range
all_days = set(list(daily_volume.keys()) + list(daily_minted.keys()) + list(daily_burned.keys()))
if all_days:
    min_day = min(all_days)
    max_day = max(all_days)
    d = datetime.strptime(min_day, "%Y-%m-%d")
    end = datetime.strptime(max_day, "%Y-%m-%d")
    day_list = []
    while d <= end:
        day_list.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
else:
    # If there are no logs at all, just use today's date
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day_list = [today]

# ─────── Write to SQLite ───────
engine = create_engine(DB_PATH)
with engine.begin() as conn:
    for day in sorted(set(list(daily_volume.keys()) + list(daily_minted.keys()) + list(daily_burned.keys()))):
        # get supply snapshot from your SmartAIWallet
        raw_supply = wallet_contract.functions.readSupply().call()
        supply = raw_supply / 1e18

        holders = holders_by_day[day]
        senders = senders_by_day[day]
        wallets = wallets_by_day[day]

        conn.execute(
            text("""
                INSERT INTO daily_metrics(
                    day, volume, holder_count, unique_senders, active_wallets, minted, burned, total_supply
                ) VALUES (
                    :day, :volume, :holder_count, :unique_senders, :active_wallets, :minted, :burned, :total_supply
                )
                ON CONFLICT(day) DO UPDATE SET
                    volume         = excluded.volume,
                    holder_count   = excluded.holder_count,
                    unique_senders = excluded.unique_senders,
                    active_wallets = excluded.active_wallets,
                    minted         = excluded.minted,
                    burned         = excluded.burned,
                    total_supply   = excluded.total_supply;
            """),
            {
                'day':             day,
                'volume':          daily_volume.get(day, 0),
                'holder_count':    len(holders),
                'unique_senders':  len(senders),
                'active_wallets':  len(wallets),
                'minted':          daily_minted.get(day, 0),
                'burned':          daily_burned.get(day, 0),
                'total_supply':    supply,
            }
        )

save_last_block(STATE_PATH, latest_block)

print(f'➡️  Fetched {raw_log_count} raw logs.')
print(f'✅  Ingest complete – bookmark saved at block {latest_block:,}.')