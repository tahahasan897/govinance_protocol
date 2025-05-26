import os
import json
import requests
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables from necessities.env at repo root
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(REPO_ROOT, "necessities.env")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)

RPC_URL = os.getenv("RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

# Initialize web3 and contract if possible
web3 = None
contract = None
try:
    if RPC_URL and CONTRACT_ADDRESS:
        web3 = Web3(Web3.HTTPProvider(RPC_URL))
        ABI_PATH = os.path.join(REPO_ROOT, "Tcript", "abi.json")
        with open(ABI_PATH) as f:
            abi = json.load(f)
        contract = web3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=abi,
        )
except Exception as exc:
    print(f"Failed to configure Web3 contract: {exc}")

SUBGRAPH_URL = "https://api.thegraph.com/subgraphs/name/tahatxt/transcript-tcript"
SUBGRAPH_QUERY = """
{\n  dailyVolumes(first: 1, orderBy: id, orderDirection: desc) {\n    id\n    volume\n    holderCount\n  }\n}\n"""

def _fetch_subgraph_data():
    """Return the latest daily volume entry from the subgraph."""
    try:
        response = requests.post(SUBGRAPH_URL, json={"query": SUBGRAPH_QUERY}, timeout=10)
        response.raise_for_status()
        data = response.json()

        # safely handle the case where no dailyVolumes have been indexed yet
        volumes = data.get("data", {}).get("dailyVolumes", [])
        if not volumes:
           return {"holderCount": 0, "volume": "0"}

        # Now we know there's at least one entry
        return volumes[0]
    except Exception as exc:
        print(f"Error fetching subgraph data: {exc}")
        return {"holderCount": 0, "volume": "0"}

def get_unique_holder_count():
    """Return current unique holder count as integer."""
    data = _fetch_subgraph_data()
    try:
        return int(data.get("holderCount", 0))
    except Exception as exc:
        print(f"Error parsing holder count: {exc}")
        return 0

def get_daily_volume():
    """Return daily transferred volume as float in token units."""
    data = _fetch_subgraph_data()
    try:
        volume_int = int(data.get("volume", 0))
        return volume_int / 10**18
    except Exception as exc:
        print(f"Error parsing daily volume: {exc}")
        return 0.0

def get_volume_percentage():
    """Return daily volume relative to total supply as percentage."""
    try:
        daily_volume = get_daily_volume()
        if not contract:
            raise ValueError("Contract not configured")
        supply = contract.functions.totalSupply().call() / 10**18
        if supply == 0:
            return 0.0
        return (daily_volume / supply) * 100
    except Exception as exc:
        print(f"Error calculating volume percentage: {exc}")
        return 0.0

def main():
    holders = get_unique_holder_count()
    daily_vol = get_daily_volume()
    percent = get_volume_percentage()
    print(f"Unique Holders: {holders}")
    print(f"Daily Volume: {daily_vol} tokens")
    print(f"Volume Percentage: {percent: .2f}%")

if __name__ == "__main__":
    main()