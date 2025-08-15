# ai_controller.py
from decimal import Decimal, getcontext 
from web3 import Web3
import json
import os
from dotenv import load_dotenv
from functions import demand_index, adaptive_threshold, heat_gap, percent_rule, save_msct, load_msct, log_run
from datetime import datetime
import time
from sys import exit

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
LOG_PATH = os.path.join(REPO_ROOT, "metrics_log.csv")

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

# AI Logic 
def get_decision():
    """Return an integer supply adjustment decision based on functions folder calculation."""

    # Calculate demand index
    the_demand = demand_index(DB_PATH, circulating)
    if the_demand == None:
        return 0
    msct = load_msct(MSCT_STATE_PATH) or 0.5
    new_msct = adaptive_threshold(the_demand, msct)

    heat_gap_value = heat_gap(the_demand, msct)
    percent = percent_rule(heat_gap_value, msct)
    threshold_used = msct
    
    save_msct(MSCT_STATE_PATH, new_msct)

    return percent, the_demand, threshold_used, heat_gap_value

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
    # Get decision and all intermediate values
    decision_result = get_decision()
    
    # Handle case where demand_index failed
    if decision_result == 0:
        print("[AI DECISION] Demand index calculation said to be 0, no action taken.")
        exit(0)
    
    percent, the_demand, threshold_used, heat_gap_value = decision_result
    decision = Decimal(percent)

    # Scale it up by 1e18
    scale = Decimal(10) ** 18
    fixed_point = int(decision * scale)
    # → e.g. 53245000000000000

    print(f"[AI DECISION] Returned: {fixed_point}")
    print("[ACTION] Sending transaction to adjust supply...")
    send_transaction(fixed_point)

    # Wait a little for the transaction to be mined, then log updated balances
    time.sleep(20.0)
    # Fetch updated balances
    try:
        ai_balance = token_contract.functions.balanceOf(WALLET_CONTRACT_ADDRESS).call() / 1e18
        deployer_balance = token_contract.functions.balanceOf(DEPLOYER).call() / 1e18
    except Exception:
        ai_balance = None
        deployer_balance = None
    
    # Log everything in one row
    timestamp = datetime.now().isoformat()
    log_run(
        timestamp,
        the_demand,
        threshold_used,
        heat_gap_value,
        percent,
        ai_balance,
        deployer_balance
    )
