import json
import os
import time
import sys
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
# Closest block to start from recent - 50 blocks.
START_DEPLOY_BLOCK = (w3.eth.block_number) - 1000

# ─────── Load last processed block ───────
def load_last_block(path: Path) -> int:
    try:
        with path.open() as f:
            return int(json.load(f).get('last_block', 0))
    except:
        return 0

def save_last_block(path: Path, block: int) -> None:
    with path.open('w') as f:
        json.dump({'last_block': block}, f, indent=2)

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
CIRCULATION_CONTRACTION_TOPIC = event_abi_to_log_topic({
    "anonymous": False,
    "inputs": [{"indexed": False, "internalType": "uint256", "name": "amount", "type": "uint256"}],
    "name": "CirculationContraction",
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
daily_volume           = defaultdict(float)  # day -> total volume
daily_deployer_to_user = defaultdict(float)
daily_user_to_user     = defaultdict(float) 
daily_user_to_deployer = defaultdict(float)
daily_deployer_to_tres = defaultdict(float)  # deployer -> treasury
daily_user_to_tres     = defaultdict(float)  # user -> treasury
daily_circ_contraction = defaultdict(float)  # circulation contraction events

senders_by_day         = defaultdict(set)
wallets_by_day         = defaultdict(set)
daily_minted           = defaultdict(float)
daily_burned           = defaultdict(float)

# ─────── Persisted balances for cumulative holder tracking ───────
BALANCES_PATH = SCRIPT_DIR / 'balances.json'

def load_balances(path: Path) -> dict:
    try:
        with path.open() as f:
            return json.load(f)
    except:
        return {}

def save_balances(path: Path, balances: dict) -> None:
    with path.open('w') as f:
        json.dump(balances, f, indent=2)

# Track balances for true holder count
balances_initial = load_balances(BALANCES_PATH)
balances_by_address = defaultdict(float, {k: v for k, v in balances_initial.items()})
true_holders_by_day    = defaultdict(set)    # day -> set(addresses with balance > 0)

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

    for raw in logs:
        topic = raw['topics'][0]
        ts = w3.eth.get_block(raw['blockNumber']).timestamp
        day = datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d')

        if topic == TRANSFER_TOPIC:
            evt = token_contract.events.Transfer().process_log(raw)
            frm = evt['args']['from'].lower()
            to = evt['args']['to'].lower()
            val = int(evt['args']['value']) / 1e18

            # Skip mints (from zero address)
            if frm == '0x0000000000000000000000000000000000000000':
                continue
            # Skip burns (to zero address)
            if to == '0x0000000000000000000000000000000000000000':
                continue
            # Skip transfers from treasury to deployer only
            if frm == WALLET_CONTRACT_ADDRESS.lower() and to == DEPLOYER.lower():
                continue

            daily_volume[day] += val

            # Categorize transfers
            if frm == DEPLOYER.lower() and to == WALLET_CONTRACT_ADDRESS.lower():
                daily_deployer_to_tres[day] += val
            elif frm == DEPLOYER.lower() and to != DEPLOYER.lower():
                daily_deployer_to_user[day] += val
            elif frm != DEPLOYER.lower() and to == DEPLOYER.lower():
                daily_user_to_deployer[day] += val
            elif frm != DEPLOYER.lower() and to == WALLET_CONTRACT_ADDRESS.lower():
                daily_user_to_tres[day] += val
            elif frm != DEPLOYER.lower() and to != DEPLOYER.lower():
                daily_user_to_user[day] += val

            # Update balances from true holder count
            balances_by_address[frm] -= val
            balances_by_address[to] += val

            # Add non-deployer, non-treasury addresses to senders and active wallets
            if frm not in {DEPLOYER.lower(), WALLET_CONTRACT_ADDRESS.lower()}:
                senders_by_day[day].add(frm)
                wallets_by_day[day].add(frm)
            if to not in {DEPLOYER.lower(), WALLET_CONTRACT_ADDRESS.lower()}:
                wallets_by_day[day].add(to)

        elif topic == MINTING_HAPPENED_TOPIC:
            amount = int.from_bytes(raw['data'], byteorder='big') / 1e18
            daily_minted[day] += amount

        elif topic == BURNING_HAPPENED_TOPIC:
            amount = int.from_bytes(raw['data'], byteorder='big') / 1e18
            daily_burned[day] += amount

        elif topic == CIRCULATION_CONTRACTION_TOPIC:
            amount = int.from_bytes(raw['data'], byteorder='big') / 1e18
            daily_circ_contraction[day] += amount

    # After processing all logs for this block range, update holder counts for each day
    if logs:
        # Get all unique days from the processed logs
        processed_days = set()
        for raw in logs:
            ts = w3.eth.get_block(raw['blockNumber']).timestamp
            day = datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d')
            processed_days.add(day)
        
        # Update true holders for each day that had activity
        for day in processed_days:
            true_holders = {
                addr for addr, bal in balances_by_address.items()
                if bal > 0
                and addr != DEPLOYER.lower()
                and addr != WALLET_CONTRACT_ADDRESS.lower()
            }
            true_holders_by_day[day] = true_holders

    raw_log_count += len(logs)
    block = to_block + 1

# Seed today's holder set if no activity days were processed
if not true_holders_by_day:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    true_holders_by_day[today] = {
        addr for addr, bal in balances_by_address.items()
        if bal > 0 and addr not in {DEPLOYER.lower(), WALLET_CONTRACT_ADDRESS.lower()}
    }

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

# ─────── Calculate holder count for all days ───────
# For days with no activity, we still need to calculate the holder count

def get_current_holder_count():
    """Get current holder count by checking all historical transfer recipients"""
    print("🔍 Getting current holder count from blockchain...")
    try:
        # Get all Transfer events from recent blocks to get addresses that might hold tokens
        current_block = w3.eth.block_number
        # Look back a reasonable amount of blocks to find potential holders
        from_block = max(0, current_block - 100000)  # Look back ~100k blocks
        
        all_logs = w3.eth.get_logs({
            'fromBlock': from_block,
            'toBlock': 'latest',
            'address': token_contract.address,
            'topics': [TRANSFER_TOPIC]
        })
        
        # Get all unique addresses that received tokens in recent history
        all_addresses = set()
        for log in all_logs:
            evt = token_contract.events.Transfer().process_log(log)
            frm = evt['args']['from'].lower()
            to = evt['args']['to'].lower()
            
            # Add both sender and receiver (we'll check balances for all)
            if frm != '0x0000000000000000000000000000000000000000':
                all_addresses.add(frm)
            if to != '0x0000000000000000000000000000000000000000':
                all_addresses.add(to)
        
        # Check current balance for each address
        current_holders = 0
        for addr in all_addresses:
            try:
                if (addr != DEPLOYER.lower() and 
                    addr != WALLET_CONTRACT_ADDRESS.lower()):
                    balance = token_contract.functions.balanceOf(Web3.to_checksum_address(addr)).call()
                    if balance > 0:
                        current_holders += 1
            except Exception as e:
                continue
                
        print(f"📊 Found {current_holders} current holders")
        return current_holders
        
    except Exception as e:
        print(f"Error getting current holder count: {e}")
        return 0

# First, try to get holder count from the most recent day with transactions
latest_holder_count = 0
if true_holders_by_day:
    # Get the holder count from the most recent day with activity
    latest_day = max(true_holders_by_day.keys())
    latest_holder_count = len(true_holders_by_day[latest_day])
    print(f"Using holder count {latest_holder_count} from most recent active day: {latest_day}")
else:
    # If no recent activity, get actual current holder count from blockchain
    latest_holder_count = get_current_holder_count()
    
    if latest_holder_count == 0:
        # Fall back to database as last resort
        print("No holders found from blockchain, checking database for last known holder count...")
        try:
            engine = create_engine(DB_PATH)
            with engine.begin() as conn:
                result = conn.execute(
                    text("SELECT holder_count FROM daily_metrics ORDER BY day DESC LIMIT 1")
                ).fetchone()
                if result:
                    latest_holder_count = result[0]
                    print(f"Using last known holder count from database: {latest_holder_count}")
                else:
                    print("No historical data found in database")
        except Exception as e:
            print(f"Could not query database: {e}")

# Build cumulative holder counts
for day in day_list:
    # Ensure every day has at least an empty set
    true_holders_by_day.setdefault(day, set())

cumulative_holders = set()
for day in sorted(day_list):
    # Add today's holders to cumulative set
    cumulative_holders |= true_holders_by_day[day]
    # Overwrite with full cumulative set
    true_holders_by_day[day] = set(cumulative_holders)

print("Cumulative holders per day:", [(d, len(true_holders_by_day[d])) for d in sorted(day_list)])

# Fill missing days with previous day's holder set
previous_holders = set()
for day in sorted(day_list):
    if day in true_holders_by_day and true_holders_by_day[day]:
        previous_holders = true_holders_by_day[day]
    else:
        true_holders_by_day[day] = set(previous_holders)

# ─────── Write to SQLite ───────
engine = create_engine(DB_PATH)
with engine.begin() as conn:
    for day in day_list:
        # get supply snapshot from your SmartAIWallet
        raw_supply = wallet_contract.functions.readSupply().call()
        supply = raw_supply / 1e18

        try:
            circulating_balance = token_contract.functions.balanceOf(DEPLOYER).call()
            treasury_balance = token_contract.functions.balanceOf(WALLET_CONTRACT_ADDRESS).call()
            circulating_balance = circulating_balance / 1e18
            treasury_balance = treasury_balance / 1e18
        except Exception as e:
            print(f"Error fetching balances for {day}: {e}")
            sys.exit(1)

        # Use true holder count
        holder_count = len(true_holders_by_day.get(day, set()))
        senders = senders_by_day.get(day, set())
        wallets = wallets_by_day.get(day, set())

        conn.execute(
            text("""
                INSERT INTO daily_metrics(
                    day,
                    volume,
                    circ_to_user,
                    user_to_user,
                    user_to_circ,
                    circ_to_tres,
                    user_to_tres,
                    holder_count,
                    unique_senders,
                    active_wallets,
                    minted,
                    burned,
                    circulation_contraction,
                    total_supply,
                    circulating_balance,
                    treasury_balance
                ) VALUES (
                    :day,
                    :volume,
                    :circ_to_user,
                    :user_to_user,
                    :user_to_circ,
                    :circ_to_tres,
                    :user_to_tres,
                    :holder_count,
                    :unique_senders,
                    :active_wallets,
                    :minted,
                    :burned,
                    :circulation_contraction,
                    :total_supply,
                    :circulating_balance,
                    :treasury_balance
                )
                ON CONFLICT(day) DO UPDATE SET
                    volume                  = excluded.volume,
                    circ_to_user            = excluded.circ_to_user,
                    user_to_user            = excluded.user_to_user,
                    user_to_circ            = excluded.user_to_circ,
                    circ_to_tres            = excluded.circ_to_tres,
                    user_to_tres            = excluded.user_to_tres,
                    holder_count            = excluded.holder_count,
                    unique_senders          = excluded.unique_senders,
                    active_wallets          = excluded.active_wallets,
                    minted                  = excluded.minted,
                    burned                  = excluded.burned,
                    circulation_contraction = excluded.circulation_contraction,
                    total_supply            = excluded.total_supply,
                    circulating_balance     = excluded.circulating_balance,
                    treasury_balance        = excluded.treasury_balance;
            """),
            {
                'day':                      day,
                'volume':                   daily_volume.get(day, 0),
                'circ_to_user':             daily_deployer_to_user.get(day, 0),
                'user_to_user':             daily_user_to_user.get(day, 0),
                'user_to_circ':             daily_user_to_deployer.get(day, 0),
                'circ_to_tres':             daily_deployer_to_tres.get(day, 0),
                'user_to_tres':             daily_user_to_tres.get(day, 0),
                'holder_count':             holder_count,
                'unique_senders':           len(senders),
                'active_wallets':           len(wallets),
                'minted':                   daily_minted.get(day, 0),
                'burned':                   daily_burned.get(day, 0),
                'circulation_contraction':  daily_circ_contraction.get(day, 0),
                'total_supply':             supply,
                'circulating_balance':      circulating_balance,
                'treasury_balance':         treasury_balance
            }
        )

save_last_block(STATE_PATH, latest_block)
# Save updated balances for next run
save_balances(BALANCES_PATH, balances_by_address)

print(f'➡️  Fetched {raw_log_count} raw logs.')
print(f'✅  Ingest complete – bookmark saved at block {latest_block:,}.')