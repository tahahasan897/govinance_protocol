from flask import Flask, render_template_string
from web3 import Web3
import json
import os
from dotenv import load_dotenv

# Always load environment variables from the repository root
# Determine the repository root relative to this file so the
# application works regardless of the current working directory.
REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
ENV_PATH = os.path.join(REPO_ROOT, "necessities.env")
load_dotenv(ENV_PATH)

# Configuration
RPC_URL = os.getenv("RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

app = Flask(__name__)
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Load the ABI relative to this file so running from other directories works
ABI_PATH = os.path.join(os.path.dirname(__file__), "abi.json")
with open(ABI_PATH) as f:
    abi = json.load(f)

if not CONTRACT_ADDRESS:
    raise EnvironmentError("CONTRACT_ADDRESS is not set in environment")

contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=abi)

@app.route("/")
def index():
    try:
        total_supply = contract.functions.totalSupply().call()
        supply = w3.from_wei(total_supply, "ether")
    except Exception as exc:  # handle RPC or contract failures gracefully
        app.logger.error("Failed to fetch totalSupply: %s", exc)
        supply = "Unavailable"

    return render_template_string(
        """
    <h1>AI-Controlled Crypto Supply</h1>
    <p>Total Supply: {{ supply }}</p>
    """,
        supply=supply,
    )

if __name__ == "__main__":
    app.run(debug=True)
