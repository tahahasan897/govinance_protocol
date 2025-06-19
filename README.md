# ΤΡΑΝΣΚΡΙΠΤ Project

The Transcript Project is a decentralized, AI-based token governance platform. It features an ERC-20 token (TCRIPT) with a unique supply management mechanism based on a mathematical algorithm. Where an automated AI backend can propose and execute supply adjustments based on on-chain metrics (As well as off-chain metrics in the future). The project includes a Flask web dashboard for transparency and community engagement, a backend logic, both of the contracts, database, etc... 

## Features

- **ERC-20 Token (TCRIPT):**  
  - 1,000,000 initial supply  
  - 25% minted to deployer (liquidity), 75% to AI-controlled treasury  
  - AI can mint/burn tokens based on daily metrics that are being fetched.

- **AI Backend:**  
  - Proposes supply changes based on demand index. Which gathers volume, holder count, unique senders, and active wallets.
  - Can only adjust supply once per week (Saturday)
  - Integrates Chainlink price feeds for on-chain ETH/USD valuation

- **Web Dashboard (STILL IN PROGRESS)**
  - Flask-based frontend  
  - Displays token info, supply history, and project documentation  
  - Community call-to-action and funding links

## How This Project Works:

The purpose of this project is to set the data to be ready in order to train an AI model to start taking control over the governance policy. The project is yet experiemental, but it can set to go on it's own
as a regular token for trading, staking, and so on. So, how can it determine whether to mint/burn or doesn't do any change? Well, you can checkout `functions.py` to see how it works. But here is a brief explanation:

- **Demand Index Function:**

  The demand index is defined as:
  
  f(D) = w_v(v_t) + w_h(h_t) + w_c(c_t)
  
  
  Where:
  
  v_t, h_t, and c_t are the weekly-summed values for volume %, holder-growth, and velocity/churn. Each calculated using       their own formulas.
  
  w_v, w_h, and w_c are the weights that determine the importance of each factor.
  
  
Currently, the volume weight w_v is set highest at 0.5, because volume is generally considered the most important metric. However, this can be adjusted depending on the goal. A more balanced setup might be:
  
  w_v = 0.4
  
  
  w_h = 0.4
  
  
  w_c = 0.2
  
  
  Understanding what each variable represents — and what outcome we're aiming for — is crucial when adjusting these weights.
  
- **Adaptive Threshold:**
    
  The adaptive threshold determines when a token is considered "HOT" or not:
  
  If the demand index is greater than the threshold, the token is HOT. But, if the demand index is below the threshold, demand is considered low — it may be a signal to burn the token.
  
  
  The adaptive threshold is calculated using the function:
  f(msct) = msct × (1 + ga × (D − msct))
  
  
  Where:
  
  msct (initially set to 0.5) represents half of the token supply.
  
  
  ga is the learning rate, defaulted to 0.2.
  
  
  This function adjusts the threshold over time. If the demand doesn't exceed 0.5 (i.e., half the supply), the function remains inactive. But once demand surpasses that point, it reacts accordingly.
  You can think of ga like a bumper or resistance:
  "If demand exceeds the threshold, the line (threshold) creeps upward by 20% of the difference — and it moves downward similarly if demand drops."
  
- **Velocity-Scaled Linear Adjustment:**
  
  The model also includes a "velocity-scaled linear" adjustment, (the equation is: K * g_t/msct). where a constant k = 0.6, and g_t is the difference between the demand index, and the adaptive threshold. This value controls sensitivity:
  
  A smaller k helps reduce excessive fluctuations in the output percentage.
  
  
  This is especially useful because a +1 point increase in demand is huge when the threshold is 0.8 (early stage), but minimal when the threshold is at 8 (in a mature market).
  
  
  That’s why this particular approach — with scaling and damping — was chosen.

The key ideas are:
  - A weighted demand index that considers volume %, holder-growth, and velocity/churn.
  - An adaptive threshold that reacts to demand shifts.
  - A sensitivity scaling mechanism to keep changes stable as the market matures.

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
