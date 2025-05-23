# ai_controller.py
import requests
from web3 import Web3
import json
import os
from dotenv import load_dotenv

# Load environment variables from repository root so the script works regardless
# of the current working directory.
REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
ENV_PATH = os.path.join(REPO_ROOT, "necessities.env")
load_dotenv(dotenv_path=ENV_PATH)

# Config
RPC_URL = os.getenv("RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")

# Connect
web3 = Web3(Web3.HTTPProvider(RPC_URL))

# Load ABI relative to this file so path works regardless of CWD
ABI_PATH = os.path.join(os.path.dirname(__file__), "abi.json")
with open(ABI_PATH) as f:
    abi = json.load(f)

if not CONTRACT_ADDRESS:
    raise EnvironmentError("CONTRACT_ADDRESS is not set in environment")

contract = web3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=abi,
)


# AI Logic (Simple Rule)
def get_decision():
    """Return an integer supply adjustment decision based on ETH price."""
    try:
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
            timeout=10,
        )
        response.raise_for_status()
        eth_price = response.json()["ethereum"]["usd"]
    except Exception as exc:
        print(f"Failed to fetch price data: {exc}")
        return 0

    # Fake volatility logic
    if eth_price > 3000:
        return 2  # Mint 2%
    elif eth_price < 1500:
        return -1  # Burn 1%
    else:
        return 0  # No change


def send_transaction(percent):
    nonce = web3.eth.get_transaction_count(WALLET_ADDRESS)
    txn = contract.functions.adjustSupply(percent).build_transaction(
        {
            "chainId": 11155111,  # Sepolia chain ID
            "gas": 200000,
            "gasPrice": web3.to_wei("20", "gwei"),
            "nonce": nonce,
        }
    )

    signed_txn = web3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"Sent transaction: {web3.to_hex(tx_hash)}")


if __name__ == "__main__":
    decision = get_decision()
    print(f"[AI DECISION] Returned: {decision}%")

    if decision != 0:
        print("[ACTION] Sending transaction to adjust supply...")
        send_transaction(decision)
    else:
        print("[ACTION] No change — holding supply steady.")
