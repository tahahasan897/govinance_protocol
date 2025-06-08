from flask import Flask, send_from_directory
from web3 import Web3
import json
import os
from dotenv import load_dotenv
import requests

# Always load environment variables from the repository root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(REPO_ROOT, "necessities.env")
load_dotenv(ENV_PATH)

# Configuration
RPC_URL = os.getenv("RPC_URL")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

app = Flask(__name__)
w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 5}))

# Load the ABI relative to this file so running from other directories works
ABI_PATH = os.getenv("ABI_FILE")
with open(ABI_PATH) as f:
    abi = json.load(f)

if not CONTRACT_ADDRESS:
    raise EnvironmentError("CONTRACT_ADDRESS is not set in environment")

contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=abi
)

@app.route("/")
def index():
    # TODO:
    return send_from_directory(os.path.join(REPO_ROOT, "templates"), "index.html")

if __name__ == "__main__":
    # Print out all registered routes to confirm /supply-data is active
    print("URL map:", app.url_map)
    app.run(debug=True)
