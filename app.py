from flask import Flask, render_template, request, jsonify
from web3 import Web3
import json
import os
from dotenv import load_dotenv

# Always load environment variables from the repository root
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(REPO_ROOT, "necessities.env")
load_dotenv(ENV_PATH)

# Configuration
RPC_URL = os.getenv("RPC_URL")
CONTRACT_ADDRESS = os.getenv("TOKEN_CONTRACT_ADDRESS")
MY_WALLET_ADDRESS = os.getenv("MY_WALLET_ADDRESS")

app = Flask(__name__, static_folder='static', template_folder='templates')
w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 5}))

# Load the ABI relative to this file so running from other directories works
ABI_PATH = os.getenv("TOKEN_ABI_FILE")
with open(ABI_PATH) as f:
    abi = json.load(f)

if not CONTRACT_ADDRESS:
    raise EnvironmentError("CONTRACT_ADDRESS is not set in environment")

contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=abi
)

claimed_addresses = set() 

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/whitepaper", methods=["GET"])
def whitepaper():
    return render_template("whitepaper.html")

@app.route("/fund", methods=["GET"])
def fund():
    return render_template("fund.html", my_wallet_address=MY_WALLET_ADDRESS)

@app.route("/interact", methods=["GET", "POST"])
def interact():
    if request.method == "POST":
        address = request.json.get("address")
        if not address:
            return jsonify({"message": "Address is required"}), 400
        if not w3.is_address(address):
            return jsonify({"message": "Invalid Ethereum address."}), 400
        if address in claimed_addresses:
            return jsonify({"message": "Address already claimed"}), 400
        
        # Save the address for manual processing
        if os.path.exists("claimed_addresses.txt"):
            with open("claimed_addresses.txt", "a") as f: 
                f.write(address + "\n")
            claimed_addresses.add(address)
        return jsonify({"message": "Address submitted! Tokens will be sent soon."})
        
    return render_template("interact.html")

    

if __name__ == "__main__":
    app.run(debug=True)
