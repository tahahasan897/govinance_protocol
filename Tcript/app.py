from flask import Flask, render_template_string
from web3 import Web3
import json
import os
from dotenv import load_dotenv

load_dotenv("necessities.env")
# Config
# RPC_URL = os.getenv("RPC_URL")

app = Flask(__name__)
w3 = Web3(Web3.HTTPProvider("https://eth-sepolia.g.alchemy.com/v2/ZZ0o3ElccCRecnfKBeD4sFZY6hN4haL0"))

with open('abi.json') as f:
    abi = json.load(f)

contract = w3.eth.contract(address="0x543CF24b644695BEd037BaACF93f6c04159BAC38", abi=abi)

@app.route("/")
def index():
    total_supply = contract.functions.totalSupply().call()
    return render_template_string("""
    <h1>AI-Controlled Crypto Supply</h1>
    <p>Total Supply: {{ supply }}</p>
    """, supply=w3.from_wei(total_supply, 'ether'))

if __name__ == "__main__":
    app.run(debug=True)
