# Govinance Project

The Govinance Project is a decentralized, AI-based token governance platform. It features an ERC-20 token (GBI) with a unique supply management mechanism based on a mathematical algorithm. Where an automated AI backend can propose and execute supply adjustments based on on-chain metrics (As well as off-chain metrics in the future). The project includes a Flask web dashboard for transparency and community engagement, a backend logic, both of the contracts, database, etc... 

## Features

- **ERC-20 Token (GBI):**  
  - 1,000,000 initial supply  
  - 25% minted to deployer (liquidity), 75% to AI-controlled treasury  
  - AI can mint/burn tokens based on daily metrics that are being fetched.

- **AI Backend:**  
  - Proposes supply changes based on demand index. Which gathers volume, holder count, unique senders, and active wallets.
  - Can only adjust supply once per week (Saturday)
  - Integrates Chainlink price feeds for on-chain ETH/USD valuation

- **Web Dashboard (STILL IN PROGRESS):**
  - Flask-based frontend  
  - Displays token info, supply history, and project documentation  
  - Community call-to-action and funding links

## How This Project Works:

The purpose of this project is to set the data to be ready in order to train an AI model to start taking control over the governance policy. The project is yet experiemental, but it can set to go on it's own
as a regular token for trading, staking, and so on. Let's go through the main folders/files, starting with the top and work our way down:

- **`gbi`**:
  - `ai_controller.py`:
    This file, is an AI-driven supply controller for your GovinanceToken ecosystem. Here’s what it does:

    - Purpose:
    
      It connects to your deployed SmartAIWallet contract on-chain.
      It uses AI/algorithmic logic (from your functions module) to decide whether to increase, decrease, or hold the token        supply.
      It can send a transaction to the contract to adjust the supply based on this decision.
      
    - How it works
      1. Environment & Config Loading
      
        Loads environment variables (RPC URL, contract address, ABI path, private key, etc.) from necessities.env.
        Loads the contract ABI from the path specified in the environment.
      
      2. Blockchain Connection
      
        Connects to the blockchain using Web3 and the provided RPC URL.
        Instantiates a contract object for interacting with the SmartAIWallet.
      
      3. Supply Fetching
      
        Reads the current total supply from the contract and converts it from wei to tokens.
      
      4. AI Logic
      
        Calls functions from your functions.py (like demand_index, adaptive_threshold, heat_gap, percent_rule) to analyze           metrics and decide on a supply adjustment percentage.
        Scales this percentage to a fixed-point integer (for on-chain compatibility).
      
      5. Transaction Sending
      
        If the AI decision is nonzero, it builds and (optionally) sends a transaction to the contract’s adjustSupply function       with the computed adjustment factor.
  
      6. Execution
      
        When run as a script, it prints the AI’s decision and either sends the transaction or holds steady.
    
    - Summary
      This script is an automated, data-driven supply manager for your token, using on-chain data and AI logic to decide and execute supply adjustments on your smart contract.
      

So, how can it determine whether to mint/burn or doesn't do any change? Well, you can checkout `functions.py` to see how it works. But here is a brief explanation:

  - **Demand Index Function:**
  
    The demand index is defined as:
    
    f(D) = w_v(v_t) + w_h(h_t) + w_c(c_t)
    
    
    Where:
    
    v_t, h_t, and c_t are the weekly-summed values for volume %, holder-growth, and velocity/churn. Each calculated using       their own formulas.
    
    w_v, w_h, and w_c are the weights that determine the importance of each factor.
    
    
  Currently, the volume weight w_v is set highest at 0.5, because volume is generally considered the most important metric. However, this can be adjusted depending on the goal. A more balanced setup might be:
    - w_v = 0.4
    - w_h = 0.4
    - w_c = 0.2
    
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
    
    
    This is especially useful because a +1 point increase in demand is huge when the threshold is 0.8 (early stage), but minimal when the threshold is at 8 (in a mature market). Also, there is a hard clip just to be sure that not a big percentage gets dumped into the equation. Such that it is called "pmax", it is set at a hard limit. If the percent (whether negative or positive), goes beyond that limit. It is gonna be set at +-5%. 
    
    
    That’s why this particular approach — with scaling and damping — was chosen.
  
  The key ideas are:
    - A weighted demand index that considers volume %, holder-growth, and velocity/churn.
    - An adaptive threshold that reacts to demand shifts.
    - A sensitivity scaling mechanism to keep changes stable as the market matures.


- **`token_ai_tracker`**:
  - `abis`:
    Purpose: Stores contract ABI files in JSON format.
    What it does:
    Contains the ABI definitions for your smart contracts (e.g., SmartAIWallet.json, Govinance.json).
    These files are loaded by Python scripts and the backend to interact with contracts on-chain.

  - `fetch_metrics.py`:
    Purpose: Fetches and aggregates on-chain token activity.
    What it does:
    Connects to the blockchain, fetches logs/events from the GovinanceToken contract.
    Aggregates daily metrics (volume, holders, senders, wallets, minted, burned, total supply).
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
  Contains a table (likely daily_metrics) with columns such as day, volume, holder_count, unique_senders, active_wallets, minted, burned, and total_supply.
  Populated by fetch_metrics.py and used by your AI controller and analytics to track token activity, supply changes, and user engagement over time.

- **`Govinance.sol`**:
  Purpose:
  Implements the main ERC-20 token contract for your project, called GovinanceToken (GBI).
  What it does:
  Mints an initial supply (1,000,000 tokens), splitting 25% to the deployer and 75% to the AI-controlled treasury.
  Allows the AI controller (SmartAIWallet) to adjust supply up or down via the adjustSupply function, which can mint, burn, or release tokens from the treasury.
  Emits events for minting and burning.
  Includes logic for rotating the AI controller wallet if needed.
  Enforces that only the AI controller can call supply adjustment functions.

Once we've gotten through how the mathematics work. The project needs to fetch data points, that's where `token_ai_tracker/fetch_metrics.py` comes into play. The file get's to run everyday in order to fetch for the data, so that it can store it in a SQL database
called `token_metrics.db`. Then when it comes Saturday (end of the Week). `gbi/ai_controller.py` gets ran in order to set a decision on whether to create/destroy or do nothing towards the total supply. Now, at the beginning. It is not going to start by minting
the tokens. Once inititally, `Govinance.sol` gets deployed, 25% of the tokens is gonna be sent towards the deployer (See the "Compile and deploy the smart contracts" section down below). And the rest is gonna be sent towards the AI wallet (which is 75%). So, once the backend is done finishing with the decision. that percent factor is gonna go towards the AI treasury wallet, and it is gonna determine how much to transfer depending if the percent is greater or less than 0. If it is 0, it will do nothing. Now, that is gonna depend on 
if there is enough tokens in the treasury. If not, there is such thing as "delta" (Checkout `Govinance.sol` to know more about the `adjustSupply()` function). And if delta is not 0, meaning that the percent that it should release. Then it will mint the rest to the treasury, and transfer half of that into the deployer's account. 

The matter of relying on the deployer to distribute the tokens into whether it be a liquidity, DEX, airdrop, rewards, etc. You would start to know that it is not considered to be a point of satisfaction. And in order for that to accomplish, it is gonna require something as a "distributor contract". That way, when the tokens gets to be taken out. It is gonna distribute to all of its people. But that is gonna be costy, and at the beginning. We gonna start to experiement the project, until it is gonna be gone on its own and be fully decentralized. 

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

   - Use your preferred Solidity tool (Hardhat, Foundry, Remix, etc.) for working with `Govinance.sol` and `SmartAIWallet.sol`.
   - But for sanity purposes. It is a better for a quick practice to use remix and test out the functionality quicker. Here is a quick rundown on how it works:
     1. Create two MetaMask EOA accounts, one is for the deployer (msg.sender), and the other for the AI.
     2. Put the two files into one file, you can name it whatever. But the preferred name is `GovinanceSystem.sol`.
     3. Use injected web3 for MetaMask as the deployer. Then deploy `GovinanceToken` contract with the constructor as the addresses of both the deployer and the AI wallets.
     4. Take the address of `GovinanceToken` contract, then switch to the other contract `SmartAIWallet` and fill out the constructor with the
        `GovinanceToken` contract address, a price feed for that you can find in this link: [Chainlink](https://docs.chain.link/data-feeds/price-feeds/addresses?page=1&testnetPage=1).
        And pick any testnet address. So far, It's been tested with only ETH/zkSync sepolia addresses. And the same for the address of the AI wallet.
     5. Take the address of the smartAIWallet contract. And find the "updateAIController" function, which will update the AI wallet to be no longer the
        funds are gonna sit in the AI's EOA. But in a "smart Wallet contract", which is what the name for it is as `SmartAIWallet`.

     Keep those contracts as it is without closing remix. That way, you can move on into the backend setup for testing! Starting with the prerequisites:

### Prerequisites

- VS code
- Python 3.8+
- Node.js & npm (for Solidity contract dependencies)
- [Infura](https://infura.io/) or other Ethereum RPC endpoint

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/tahahasan897/Govinance-Token.git
   cd Govinance-Token
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
  CREATE TABLE IF NOT EXISTS daily_metrics (day TEXT PRIMARY KEY, volume REAL, holder_count INTEGER, unique_senders INTEGER, active_wallets INTEGER, minted REAL, burned REAL, total_supply REAL);
  ```
  This table has 8 columns (AS OF THIS TIME, IT WILL CHANGE LATTER ON). First column is the 'day', which captures today's date and formated in YEAR-MONTH-DAY. Second one is volume for token transfers,
  if a user or a deployer transfer tokens to a user. It get's counted into the database. For example, if a deployer sends 10,000 tokens into a user. The 10,000 tokens gets saved into the database as volume.
  Third column is the holder count, which is the individual users that own this token, if a user doesn't own it, it gets decremented. A deployer and the contract wallet do not count as the holder count. 
  Unique senders, which records every user who sends or transfer tokens to a user. A deployer and the smart wallet does not count as a unique senders. Active wallets, which shows how many active around the network. Such as
  transfering, trading, staking, etc. Minted and burned are recorded as how many tokens get's created or destroyed. These do not have a use case, just for recording events. And the total supply.
  
  once you did the interactions, run:
  ```bash
  python token_ai_tracker/fetch_metrics.py
  ```
  Once it gets ran, it'll print out:
  ```
  🔄 Processing blocks ... → ...
  ```
  This will go through the blocks and process which of these blocks obtain the event logs. If you are in case, trying to run a different chain. Checkout how many blocks are in the chain. And change this line of code:
```bash
START_DEPLOY_BLOCK = 
```
To a number that is fairly close to the amount of blocks that are in the chain. So the process can be done faster. And you won't have to process through unnecessary blocks in the past. 

### AI Controller

Once you fetched the data (Which is probably not enough for one day process), you'll have to get a generated data from a chatbot that consists of at least 2 weeks worth of dummy data. And test out the file.
To run the AI backend logic (for supply adjustment proposals), run:
```bash
python gbi/ai_controller.py
```
And it will print out the decision, as well as sending the transaction towards the contract with the address of the transaction. 

## Project Structure

```
Govinance_project/
│
├── node_modules             # Downloaded dependencies
├── static/                  # CSS and JS files
├── gbi/                  # AI controller and logic
├── templates/               # Flask HTML templates
├── token_ai_tracker/        # CSS and JS files
├── ...
├── app.py                   # application for running the web
├── msct_state.json          # Saves the new msct value after running python gbi/ai_controller.py
├── necessities.env          # .env resources
├── ...
├── PriceConverter.sol       # Converts the value of ETH/USD
├── README.md
├── requirements.txt         # Python dependencies
├── SmartAIWallet.sol        # Smart wallet contract
├── state.json               # Saves the latest block that has been explored into a new block to start reprocessing.
├── token_metrics.db         # SQL database
└── Govinance.sol           # ERC20 token logic 
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
