# Transcript Project

The Transcript Project is a decentralized, AI-based token governance platform. It features an ERC-20 token (TCRIPT) with a unique supply management mechanism, where an AI backend can propose and execute supply adjustments based on on-chain and off-chain metrics. The project includes a Flask web dashboard for transparency and community engagement.

## Features

- **ERC-20 Token (TCRIPT):**  
  - 1,000,000 initial supply  
  - 25% minted to deployer (liquidity), 75% to AI-controlled treasury  
  - AI can mint/burn tokens within off-chain defined limits

- **AI Backend:**  
  - Proposes supply changes based on demand, volume, and other metrics  
  - Can only adjust supply once per week (Saturday)  
  - Integrates Chainlink price feeds for on-chain USD/ETH valuation

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
   RPC_URL=https://sepolia.infura.io/v3/YOUR_INFURA_KEY
   CONTRACT_ADDRESS=0xYourDeployedContractAddress
   ```

5. **Compile and deploy the smart contracts:**  
   Use your preferred Solidity tool (Hardhat, Foundry, Remix, etc.) to deploy `Transcript.sol` and `AIBackend.sol`.

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