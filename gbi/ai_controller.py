# ai_controller.py
from decimal import Decimal, getcontext 
from web3 import Web3
import json
import os
from dotenv import load_dotenv
from functions import demand_index, adaptive_threshold, heat_gap, percent_rule, save_msct, load_msct

getcontext().prec = 36

# Load environment variables from repository root so the script works regardless
# of the current working directory.
REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
ENV_PATH = os.path.join(REPO_ROOT, "necessities.env")
load_dotenv(dotenv_path=ENV_PATH)

# Config
DB_PATH = os.getenv("DB_PATH", "token_metrics.db")
RPC_URL = os.getenv("RPC_URL")
DEPLOYER = os.getenv("DEPLOYER")
WALLET_CONTRACT_ADDRESS = os.getenv("WALLET_CONTRACT_ADDRESS")
TOKEN_CONTRACT_ADDRESS = os.getenv("TOKEN_CONTRACT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")
MSCT_STATE_PATH = os.getenv("MSCT_STATE_PATH", os.path.join(REPO_ROOT, "msct_state.json"))
BEGINNING_STATE_PATH = os.path.join(REPO_ROOT, "beginning_state.json")

# Connect
web3 = Web3(Web3.HTTPProvider(RPC_URL))

# Load ABI from necessities.env that leads to token_ai_tracker/abis/SmartAIWallet.json
WALLET_ABI_PATH = os.getenv("WALLET_ABI_FILE")
TOKEN_ABI_PATH = os.getenv("TOKEN_ABI_FILE")
with open(WALLET_ABI_PATH) as f:
    wallet_abi = json.load(f)
with open(TOKEN_ABI_PATH) as f:
    token_abi = json.load(f)

if not WALLET_CONTRACT_ADDRESS and not TOKEN_CONTRACT_ADDRESS:
    raise EnvironmentError("CONTRACT_ADDRESSES is not set in environment")

wallet_contract = web3.eth.contract(
    address=Web3.to_checksum_address(WALLET_CONTRACT_ADDRESS),
    abi=wallet_abi,
)

token_contract = web3.eth.contract(
    address=Web3.to_checksum_address(TOKEN_CONTRACT_ADDRESS),
    abi=token_abi # ABI for the token contract
)

# Fetch the balance of AI wallet and the balance of the deployer from token contract
try:
    balance_ai = token_contract.functions.balanceOf(WALLET_CONTRACT_ADDRESS).call()
    balance_deployer = token_contract.functions.balanceOf(DEPLOYER).call()
except Exception as e:
    print(f"Error calling balanceOf on {token_contract} or {TOKEN_CONTRACT_ADDRESS}")
    raise

total_supply = wallet_contract.functions.readSupply().call()
if not balance_ai or not balance_deployer:
    raise ValueError("Failed to fetch balances for AI wallet or deployer.")

circulating = balance_deployer

def load_beginning_state(path: str, default: bool = False) -> bool:
    """Load the saved beginning state from path or return default."""
    try:
        with open(path) as f:
            data = json.load(f)
            return bool(data.get("beginning", default))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return default

def save_beginning_state(path: str, value: bool) -> None:
    """Persist beginning state to path in JSON format."""
    with open(path, "w") as f:
        json.dump({"beginning": value}, f)

# AI Logic 
def get_decision():
    """Return an integer supply adjustment decision based on functions folder calculation."""
    

    beginning = load_beginning_state(BEGINNING_STATE_PATH)

    # Calculate demand index
    the_demand = demand_index(DB_PATH, circulating)
    if the_demand == None:
        return 0
    msct = load_msct(MSCT_STATE_PATH) or 0.5
    new_msct = adaptive_threshold(the_demand, msct)
    save_msct(MSCT_STATE_PATH, new_msct)
    # If the msct at the beginning is default, use the new_msct 
    if not beginning:
        percent = percent_rule(heat_gap(the_demand, new_msct), new_msct)
        save_beginning_state(BEGINNING_STATE_PATH, True)
    else:
        percent = percent_rule(heat_gap(the_demand, msct), msct)

    return percent

def send_transaction(percent):
    nonce = web3.eth.get_transaction_count(WALLET_ADDRESS)
    txn = wallet_contract.functions.adjustSupply(percent).build_transaction(
        {
            "chainId": 11155111,
            "gas": 200000,
            "gasPrice": web3.to_wei("20", "gwei"),
            "nonce": nonce,
        }
    )

    signed_txn = web3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"Sent transaction: {web3.to_hex(tx_hash)}")


if __name__ == "__main__":
    # Let get_decision() return something like Decimal('0.053245') for +5.3245%
    decision = Decimal(get_decision())

    # Scale it up by 1e18
    scale = Decimal(10) ** 18
    fixed_point = int(decision * scale)
    # → e.g. 53245000000000000

    print(f"[AI DECISION] Returned: {fixed_point}")

    if fixed_point != 0:
        print("[ACTION] Sending transaction to adjust supply...")
        send_transaction(fixed_point)
    else:
        print("[ACTION] No change — holding supply steady.")
