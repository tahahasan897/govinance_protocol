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


def get_token_volume():
    """Fetch the latest daily transfer volume from The Graph."""
    url = "https://api.thegraph.com/subgraphs/name/tahatxt/transcript-tcript"
    query = """
    {
      dailyVolumes(first: 1, orderBy: id, orderDirection: desc) {
        id
        volume
      }
    }
    """
    try:
        resp = requests.post(url, json={"query": query}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        latest = data["data"]["dailyVolumes"][0]
        vol_tokens = int(latest["volume"]) / 10**18
        print(f"Daily volume for id {latest['id']}: {vol_tokens} tokens")
        return vol_tokens
    except Exception as exc:
        print(f"Error fetching token volume: {exc}")
        return 0.0
    

# AI Logic (Simple Rule)
def get_decision():
        """Return an integer supply adjustment decision based on token volume."""
        volume = get_token_volume()
        if volume > 100_000:
            return 2
        elif volume < 5_000:
            return -1
        else:
            return 0

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
