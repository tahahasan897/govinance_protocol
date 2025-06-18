# ΤΡΑΝΣΚΡΙΠΤ Project

The Transcript Project is a decentralized, AI-based token governance platform. It features an ERC-20 token (TCRIPT) with a unique supply management mechanism, where an AI backend can propose and execute supply adjustments based on on-chain metrics. The project includes a Flask web dashboard for transparency and community engagement.

## Features

- **ERC-20 Token (TCRIPT):**  
  - 1,000,000 initial supply  
  - 25% minted to deployer (liquidity), 75% to AI-controlled treasury  
  - AI can mint/burn tokens based on daily metrics that are being fetched.

- **AI Backend:**  
  - Proposes supply changes based on demand index. Which gathers volume, holder count, unique senders, and active wallets.
  - Can only adjust supply once per week (Saturday)
  - Integrates Chainlink price feeds for on-chain ETH/USD valuation

- **Web Dashboard:**  
  - Flask-based frontend  
  - Displays token info, supply history, and project documentation  
  - Community call-to-action and funding links

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js & npm (for Solidity contract dependencies)
- [Infura](https://infura.io/) or other Ethereum RPC endpoint

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/transcript_project.git
   cd transcript_project
   ```

2. **Install Python dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Install Solidity dependencies:**
   ```bash
   npm install
   npm install @openzeppelin/contracts @chainlink/contracts
   ```

4. **Set up environment variables:**  
   Create a `.env` or `necessities.env` file in the project root with:
   ```
   PRIVATE_KEY=
   WALLET_ADDRESS=
   DEPLOYER=
    
   RPC_URL=
    
   WALLET_CONTRACT_ADDRESS=
   TOKEN_CONTRACT_ADDRESS=
    
   TOKEN_ABI_FILE=token_ai_tracker/abis/Transcript.json
   WALLET_ABI_FILE=token_ai_tracker/abis/SmartAIWallet.json
    
   DB_URL=sqlite:///token_metrics.db
   ```

5. **Compile and deploy the smart contracts:**  
   - Use your preferred Solidity tool (Hardhat, Foundry, Remix, etc.) to deploy `Transcript.sol` and `SmartAIWallet.sol`.
   - But for sanity purposes. It is a better for a quick practice to use remix and test out the functionality quicker. Here is a quick rundown on how it works:
     1. Create two MetaMask EOA accounts, one is for the deployer (msg.sender), and the other for the AI.
     2. Put the two files into one file, you can name it whatever. But the preferred name is `TranscriptSystem.sol`.
     3. Use injected web3 for MetaMask as the deployer. Then deploy `TranscriptToken` contract with the constructor as the addresses of both the deployer and the AI wallets.
     4. Take the address of `TranscriptToken` contract, then switch to the other contract `SmartAIWallet` and fill out the constructor with the
        `TranscriptToken` contract address, a price feed for that you can find in this link: [Chainlink](https://docs.chain.link/data-feeds/price-feeds/addresses?page=1&testnetPage=1).
        And pick any testnet address. So far, It's been tested with only ETH/zkSync sepolia addresses. And the same for the address of the AI wallet.
     5. Take the address of the smartAIWallet contract. And find the "updateAIController" function, which will update the AI wallet to be no longer the
        funds are gonna sit in the AI's EOA. But in a "smart Wallet contract", which is what the name for it is as `SmartAIWallet`.

### Running the Web Dashboard

```bash
flask run
```
Visit [http://localhost:5000](http://localhost:5000) in your browser.

### Fetching and Updating Metrics

To fetch on-chain metrics and update the database, run:
```bash
python token_ai_tracker/fetch_metrics.py
```

### AI Controller

To run the AI backend logic (for supply adjustment proposals), run:
```bash
python Tcript/ai_controller.py
```

## Project Structure

```
transcript_project/
│
├── Tcript/                  # AI controller and logic
├── token_ai_tracker/        # Metrics fetcher and database updater
├── templates/               # Flask HTML templates
├── static/                  # CSS and JS files
├── Transcript.sol           # ERC-20 token contract
├── AIBackend.sol            # AI backend contract
├── requirements.txt         # Python dependencies
├── package.json             # Node/npm dependencies
└── README.md
```

## How to Interact

- **Web Dashboard:**  
  View token stats, supply history, and project info at the homepage.

- **Funding:**  
  Use the "Fund" button on the dashboard to participate in the ecosystem.

- **Developers:**  
  - Extend the AI backend logic in `Tcript/ai_controller.py`.
  - Update metrics collection in `token_ai_tracker/fetch_metrics.py`.
  - Customize the frontend in `templates/` and `static/`.

## License

MIT

---

*For more details, see the whitepaper or contact the project maintainers.*
