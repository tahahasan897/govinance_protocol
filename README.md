<h1 align="center">Govinance Protocol</h1>

<p align="center">
  <img src="images/logo2.png" alt="Govinance" width="300"/>
</p>



The Govinance Protocol is a decentralized, AI-based token economic algorithm presented for the $Grand token economy. It features an ERC-20 token with a unique supply management mechanism based on a mathematical algorithm. Where backend is automated, and it can propose and execute supply adjustments based on on-chain metrics (As well as off-chain metrics in the future). The project includes a Flask web dashboard for basic interactions, a backend logic, both of the contracts, database, etc... 

## Features

- **ERC-20 Token (GBI):**  
  - 1,000,000 initial supply  
  - 25% minted to deployer (liquidity), 75% to AI-controlled treasury  
  - AI can mint/burn, or do nothing to the tokens based on daily metrics that are being fetched

- **AI Backend:**  
  - Proposes supply changes based on demand index. Which gathers volume transfers, holder count, unique senders, and active wallets
  - Can only adjust supply once per week (Saturday)
  - Integrates Chainlink price feeds for on-chain ETH/USD funding valuation

- **Web Dashboard:**
  - Flask-based frontend  
  - Displays some unnecessary taabls. Only focusing on is the "interact" tab, which takes you to the interaction functions

## How This Project Works:

The purpose of this project is to set the data to be ready in order to train an AI model to start taking control over the governance policy. The project is yet experiemental, but it can set to go on it's own
as a regular token for trading, staking, and so on. Let's go through the main folders/files, starting with the top and work our way down:

- **`gbi`**:
  - `ai_controller.py`:
    This file, is an AI-driven supply controller for your Grand token ecosystem. Here’s what it does:

    - Purpose:
    
      It uses configurations to connect towards the contracts, MetaMask wallet, node, database, etc.
      It uses algorithmic logic (from `functions.py`) to decide whether to increase, decrease, or hold the token supply.
      Then it sends the transaction by using a configured private key.
      
    - How it works
      1. Environment & Config Loading
      
        Loads environment variables (RPC URL, contract address, ABI path, private key, etc.) from `necessities.env`.
        Loads the contract ABI from the path specified in the environment.
      
      2. Blockchain Connection
      
        Connects to the blockchain using Web3 and the provided RPC URL.
        Instantiates a contract object for interacting with the SmartAIWallet.
      
      3. Supply Fetching
      
        Reads the current total supply from the contract and converts it from wei to tokens.
      
      4. AI Logic
      
        Calls functions from your functions.py (like demand_index, adaptive_threshold, heat_gap, percent_rule) to analyze metrics and decide on a supply adjustment percentage.
        Scales this percentage to a fixed-point integer (for on-chain compatibility).
      
      5. Transaction Sending
      
        If the AI decision is nonzero, it builds and (optionally) sends a transaction to the contract’s adjustSupply function       with the computed adjustment factor.
  
      6. Execution
      
        When run as a script, it prints the AI’s decision and either sends the transaction or holds steady automatically.
    
    - Summary
      This script is an automated, data-driven supply manager for your token, using on-chain data and AI logic to decide and execute supply adjustments on your smart contract.
      

So, how can it determine whether to mint/burn or doesn't do any change? Well, you can checkout `functions.py` to see how it works. But here is a brief explanation:

  - **Demand Index Function:**
  
    The demand index is defined as:
    
    f(D) = w_v(v_t) + w_h(h_t) + w_c(c_t)
    
    
    Where:
    
    v_t, h_t, and c_t are the weekly-summed values for volume %, holder-growth, and velocity/churn. Each calculated using their own formulas.
    
    w_v, w_h, and w_c are the weights that determine the importance of each factor.
    
    
  Currently, the volume weight w_v is set at 0.3, and the holder count weight is set highest at 0.5, because holder count is generally considered the most important metric and the most focused on towards a higher value. However, this can be deterministic.
    
  Understanding what each variable represents — and what outcome we're aiming for — is crucial when adjusting these weights.
    
  - **Adaptive Threshold:**

    Adaptive threshold that follows demand trends with enhanced scarcity mechanism.
    
    - Follows demand in both positive and negative territories
    - When demand falls below threshold, adjusts more aggressively (overshooting)
    - Creates temporary scarcity to increase token value during downturns
   
    To look forward in details, you can checkout the file.

  - **Heat Gap:**
    
    Heat gap is the difference between the demand and the threshold to figure out how much to either create/cut or do nothing to the supply.
    
  - **Percent Rule:**
    
    The formula inclues a "velocity-scaled linear" adjustment, (the equation is: k * (g_t / msct) / 40). where a constant k = 0.6, and g_t is the heat gap. This value controls sensitivity:
    
    A smaller k helps reduce excessive fluctuations in the output percentage. If the heat gap is negative. Meaning the difference between the demand and the threshold line is negative, that would consist a burning result, and by burning
    more aggressivley to introduce a double scarcity factor, there is a contraction bias variable, which is as default set to 2.0 that will make the burning capability more aggressive. 
  
  The key ideas are:
    - A weighted demand index that considers volume %, holder-growth, and velocity/churn.
    - An adaptive threshold that reacts to demand shifts.
    - A sensitivity scaling mechanism to keep changes a bit stable as the market matures.


- **`token_ai_tracker`**:
  - `abis`:
    Purpose: Stores contract ABI files in JSON format.
    What it does:
    Contains the ABI definitions for your smart contracts (e.g., SmartAIWallet.json, Grand.json).
    These files are loaded by Python scripts and the backend to interact with contracts on-chain.

  - `fetch_metrics.py`:
    Purpose: Fetches and aggregates on-chain token activity.
    What it does:
    Connects to the blockchain, fetches logs/events from the GovinanceToken contract.
    Aggregates daily metrics (volume, holders, senders, wallets, minted, burned, total supply, etc).
    Writes these metrics to a SQLite database for analytics and AI use.

- **`app.py`**:
  Purpose: Flask web server for your dApp.
  What it does:
  Serves web pages (index, whitepaper, fund).
  Loads contract ABI and connects to the blockchain.
  Passes config and wallet info to templates for frontend use.

- **`msct_state.json`**:
  Purpose: Persists the msct value between runs.
  What it does:
  Stores the current msct (moving supply control threshold) as JSON.
  Used by functions.py and ai_controller.py to maintain state across executions.

- **`PriceConverter.sol`**:
  Purpose: Solidity library for ETH/USD price conversion.
  What it does:
  Fetches ETH price from Chainlink oracles.
  Converts ETH amounts to USD for funding logic in SmartAIWallet.

- **`SmartAIWallet.sol`**:
  Purpose: Smart contract for AI-controlled treasury and supply management.
  What it does:
  Manages ownership, funding, and withdrawal.
  Calls adjustSupply on the GovinanceToken contract based on AI decisions.
  Restricts supply adjustment to once per week and only by the AI controller.

- **`state.json`**:
  Purpose: Tracks the last processed block for metrics fetching.
  What it does:
  Stores the last block number processed by fetch_metrics.py.
  Ensures the script only fetches new logs/events on subsequent runs.

- **`token_metrics.db`**:
  Purpose:
  Stores all aggregated daily token metrics for your project.
  What it does:
  Contains a table (likely daily_metrics) with columns such as day, volume, circ_to_user, user_to_user, user_to_circ, etc. 
  Populated by fetch_metrics.py and used by your AI controller and analytics to track token activity, supply changes, and user engagement over time.

- **`GrandToken.sol`**:
  Purpose:
  Implements the main ERC-20 token contract for your project, called Grand ($GBI).
  What it does:
  Mints an initial supply (1,000,000 tokens), splitting 25% to the deployer and 75% to the AI-controlled treasury.
  Allows the AI controller (SmartAIWallet) to adjust supply up or down via the adjustSupply function, which can mint, burn, or release tokens from the treasury.
  Emits events for minting and burning.
  Includes logic for rotating the AI controller wallet if needed.
  Enforces that only the AI controller can call supply adjustment functions.

Once we've gotten through how the mathematics work. The project needs to fetch data points, that's where `token_ai_tracker/fetch_metrics.py` comes into play. The file get's to run everyday in order to fetch for the data, so that it can store it in a SQL database
called `token_metrics.db`. Then when it comes Saturday (end of the Week). `gbi/ai_controller.py` gets ran in order to set a decision on whether to create/destroy or do nothing towards the total supply. Now, at the beginning. It is not going to start by minting
the tokens. Once inititally, `GrandToken.sol` gets deployed, and a function `initialize()` gets called. 25% of the tokens is gonna be sent towards the deployer (See the "Compile and deploy the smart contracts" section down below). And the rest is gonna be sent towards the AI wallet (which is 75%). So, once the backend is done finishing with the decision. that percent factor is gonna go towards the `SmartAIWallet.sol`, and it is gonna determine how much to transfer depending if the percent is greater or less than 0. If it is 0, it will do nothing. Now, that is gonna depend on 
if there is enough tokens in the treasury. If not, there is such thing as "delta" (Checkout `GrandToken.sol` to know more about the `adjustSupply()` function). And if delta is not 0, meaning that the amount is not enough to release. Then it will mint the rest to the treasury, and transfer half of that into the deployer's account. 

The matter of relying on the deployer to distribute the tokens into whether it be a liquidity, DEX, airdrop, rewards, etc. You would start to know that it is not considered to be a point of satisfaction. And in order for that to accomplish, it is gonna require something as a "distributor contract". Or to be bought from an exchange. That way, when the tokens gets to be taken out. It is gonna distribute to all of its people. But that is gonna be costy, and at the beginning. We gonna start to experiement the project, until it is gonna be gone on its own and be fully decentralized. 

## Getting Started

### Compile and deploy the smart contracts

**NOTICE: If you want to interact with ai_controller at any time. Go to `SmartAIWallet.sol`, scroll to the `adjustSupply()` function, and comment these lines of code in the SmartAIWallet.sol:
  ```bash
  uint256 dayOfWeek = (block.timestamp / 1 days + 4) % 7;
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                                                                                                                         
  require(dayOfWeek == 6, "Can only call on Saturday");
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  require(block.timestamp >= lastExecutedWeek + 7 days, "SmartAIWallet: already executed this week");
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  lastExecutedWeek = block.timestamp;
  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
  ```
  But, if you want to run it once per week and only on Saturday. Uncomment the lines.

   - Use your preferred Solidity tool (Hardhat, Foundry, Remix, etc.) for working with `GrandToken.sol` and `SmartAIWallet.sol`.
   - But for sanity purposes. It is a better for a quick practice to use remix and test out the functionality quicker. Here is a quick rundown on how it works:
     1. Create two MetaMask EOA accounts, one is for the deployer (msg.sender), and the other for transacting the AI's decision.
     2. Use injected web3 for MetaMask as the deployer. Ask a chatbot on how to get a bytes32 address using a keccak256 in order to insert it as a password for the constructor parameter in `GrandToken.sol`, then deploy the contract.
     4. Take the address of `GrandToken.sol` contract, then switch to the other contract `SmartAIWallet` and fill out the constructor with the
        `GrandToken` contract address, a price feed for that you can find in this link: [Chainlink](https://docs.chain.link/data-feeds/price-feeds/addresses?page=1&testnetPage=1).
        And pick any testnet address. Grab a testnet address and input it, get the MetaMask address for sending the transaction for the decision of the backend (for the AI backend). And a password hash that has been inputed into `GrandToken` constructor.
     5. Take the address of the smartAIWallet contract. And find the `initialize()` function in `GrandToken.sol`, then input the address of the deployer wallet (the address that you deployed `GrandToken.sol`), as well as the address of `SmartAIWallet.sol`, then transact. This will initialize the           circulation amount (250,000) towards the deployer (msg.sender) address, and the treasury amount (750 000) to the `SmartAIWallet.sol`. But in a "smart Wallet contract", which is what the name for it is as `SmartAIWallet`.

  Keep those contracts as it is without closing remix. That way, you can move on into the backend setup for testing! Starting with the prerequisites:

### Prerequisites

- VS code
- Python 3.8+
- Node.js & npm (for Solidity contract dependencies)
- [Infura](https://infura.io/) or other Ethereum RPC endpoint

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/tahahasan897/govinance_protocol.git
   cd govinance_protocol
   ```

2. **Install Python dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cd token_ai_tracker
   pip install -r requirements.txt
   ```

3. **Install Solidity dependencies (OPTIONAL):**
   ```bash
   npm install
   npm install @openzeppelin/contracts @chainlink/contracts
   ```

4. **Set up environment variables:**  
   Create a `necessities.env` file in the project root with:
   ```
   PRIVATE_KEY=
   WALLET_ADDRESS=
   DEPLOYER=
    
   RPC_URL=
    
   WALLET_CONTRACT_ADDRESS=
   TOKEN_CONTRACT_ADDRESS=
    
   TOKEN_ABI_FILE=token_ai_tracker/abis/Govinance.json
   WALLET_ABI_FILE=token_ai_tracker/abis/SmartAIWallet.json
    
   DB_URL=sqlite:///token_metrics.db
   ```
   Insert the AI wallet's private key, and the address. Deployer's account address, which is the msg.sender as you. RPC_URL from infura, you can try ethereum, zkSync sepolia or any testnets you like. And lastly, the addresses of both of the contracts.

### Fetching and Updating Metrics

To fetch on-chain metrics and update the database, you have to first need to go through these directions:

  1. You need to query into the database, run:
  ```bash
  sqlite3 token_metrics.db
  ```
  
  And create a table if it doesn't exist:
  ```bash
  CREATE TABLE IF NOT EXISTS daily_metrics (day TEXT PRIMARY KEY, volume REAL, circ_to_user REAL, user_to_user REAL, user_to_circ REAL, circ_to_tres REAL, user_to_tres REAL, holder_count INTEGER, unique_senders INTEGER, active_wallets INTEGER, mi
nted REAL, burned REAL, circulation_contraction REAL, total_supply REAL, circulating_balance REAL, treasury_balance REAL);
  ```
  This table has 8 columns (AS OF THIS TIME, IT WILL CHANGE LATTER ON). First column is the 'day', which captures today's date and formated in YEAR-MONTH-DAY. 'volume', is the sum of total transfers that happened during the day.
  'circ_to_user' is the amount that transferred from deployer account to a random user address. 'user_to_user' is the amount transferred from users to users. 'user_to_circ' is the amount transferred from users to deployer. 'circ_to_tres' is the amount transferred from deployer to treasury.
  'user_to_tres' is the amount transferred from users to treasury. 'holder_count' is the amount of accounts (other than the deployer and the treasury) who holds the tokens. 'unique_senders' are the accounts that were sending transfers during that day (other than deployer and treasury).
  'active_wallets' are the numbers of wallets that were active during that day. 'minted' is the amount that is minted during that day, same idea for 'burn'. 'circulation_contraction' is a double scarcity factor that applied in the `GrandToken.sol` `adjustSupply()` function. Tracking 'total_supply',
  'circulation', and 'treausury' amounts.
  
  once you did the interactions, run:
  ```bash
  python3 token_ai_tracker/fetch_metrics.py
  ```
  Once it gets ran, it'll print out:
  ```
  🔄 Processing blocks ... → ...
  ```
  This will go through the blocks and process which of these blocks obtain the event logs.

### AI Controller

Once you fetched the data (Which is probably not enough for one day process), you'll have to get a generated data from a chatbot that consists of 1 week worth of dummy data. And test out the file.
To run the AI backend logic (for supply adjustment proposals), run:
```bash
python3 gbi/ai_controller.py
```
And it will print out the decision, as well as sending the transaction towards the contract with the address of the transaction. 

## Project Structure

```
Govinance_project/
│
├── node_modules             # Downloaded dependencies
├── static/                  # CSS and JS files
├── gbi/                     # AI controller and logic
├── templates/               # Flask HTML templates
├── token_ai_tracker/        # CSS and JS files
├── ...
├── app.py                   # application for running a simple interaction web
├── msct_state.json          # Saves the new msct value after running python3 gbi/ai_controller.py
├── necessities.env          # .env resources
├── ...
├── PriceConverter.sol       # Converts the value of ETH/USD
├── README.md
├── requirements.txt         # Python dependencies
├── SmartAIWallet.sol        # Smart wallet contract
├── state.json               # Saves the latest block that has been explored into a new block to start reprocessing.
├── token_metrics.db         # SQL database
└── GrandToken.sol           # ERC20 token logic 
```

## How to Interact

- **Web Dashboard:**  
  View the website.

- **Funding:**  
  Use the "Fund" button on the dashboard to participate in the ecosystem.

## License

MIT

---

*For more details, see the whitepaper or contact the project maintainers.*
