# ai_controller.py
import requests
from web3 import Web3
import json
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="necessities.env")

# Config
RPC_URL = os.getenv("RPC_URL")
CONTRACT_ADDRESS = "0xa7662466353BC9543a9e3Dcc4128E8DC070BB999"
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")

# Connect
web3 = Web3(Web3.HTTPProvider(RPC_URL))

# Load ABI
with open('abi.json') as f:
    abi = json.load(f)

contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)

# AI Logic (Simple Rule)
def get_decision():
    response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")
    eth_price = response.json()["ethereum"]["usd"]

    # Fake volatility logic
    if eth_price > 3000:
        return 2  # Mint 2%
    elif eth_price < 1500:
        return -1  # Burn 1%
    else:
        return 0  # No change

def send_transaction(percent):
    nonce = web3.eth.get_transaction_count(WALLET_ADDRESS)
    txn = contract.functions.adjustSupply(percent).build_transaction({
        'chainId': 11155111,  # Sepolia chain ID
        'gas': 200000,
        'gasPrice': web3.to_wei('20', 'gwei'),
        'nonce': nonce
    })

    signed_txn = web3.eth.account.sign_transaction(txn, private_key=PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    print(f"Sent transaction: {web3.to_hex(tx_hash)}")

if __name__ == "__main__":
    decision = get_decision()
    if decision != 0:
        send_transaction(decision)
