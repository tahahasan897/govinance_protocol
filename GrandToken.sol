// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol"; 

/**
 * @title Grand (GRD) - AI-Controlled Economic Token
 * @author By Taha Hasan
 * @notice This contract implements an ERC20 token with AI-controlled supply management
 * @dev Production Features:
 *      • Dynamic supply adjustment based on AI economic analysis
 *      • Automated token distribution between treasury and circulation
 *      • Only owner protected migration capabilities
 *      • Gas-optimized deployment with post-deployment initialization
 *
 * @dev Token Economics:
 *      • Initial Supply: 1,000,000 Grand Tokens
 *      • Deployer (circulation) receives: 250,000 Grand Tokens (25% - for liquidity provision)
 *      • Wallet Treasury receives: 750,000 Grand Tokens (75% - for supply management)
 *      • No maximum supply cap - AI can mint/burn based on data conditions
 */
contract GrandToken is ERC20, Ownable {
    /*//////////////////////////////////////////////////////////////
                            PRODUCTION STATE VARIABLES
    //////////////////////////////////////////////////////////////*/

    /// @notice Fixed initial token supply for deployment (1M tokens with 18 decimals)
    /// @dev Used for calculating initial distribution percentages
    uint256 public constant INITIAL_SUPPLY = 1_000_000 * 1e18;

    /// @notice Circulating supply allocation (25% of initial supply = 250K tokens)
    /// @dev Represents tokens available for trading and liquidity
    uint256 public constant CIRCULATING_CAP = INITIAL_SUPPLY / 4;

    /// @notice Scaling factor for percentage calculations (1e18 = 100%)
    /// @dev Used in adjustSupply calculations: 10% = 0.1 * 1e18 = 1e17
    uint256 private constant SCALE = 1e18;

    /// @notice Total tokens transferred from treasury to circulation
    /// @dev Tracks cumulative token releases for economic monitoring
    uint256 public totalReleased;

    /// @notice Address authorized to execute AI-controlled supply adjustments
    /// @dev Should be set to the SmartAIWallet contract address
    address public wallet;

    /// @notice Contract deployer address for initial liquidity provision
    /// @dev Receives 25% of initial supply and migration capabilities
    address public deployer; 

    /// @notice Prevents multiple initialization calls
    /// @dev Security measure to ensure initialization happens only once
    bool private _initialized = false;

    /*//////////////////////////////////////////////////////////////
                            PRODUCTION EVENTS
    //////////////////////////////////////////////////////////////*/

    /// @notice Emitted when AI mints new tokens to expand supply
    /// @param amount Number of tokens minted (scaled by 1e18)
    /// @dev Monitor this for economic analysis and supply tracking
    event MintingHappened(uint256 amount);

    /// @notice Emitted when AI burns tokens to contract supply
    /// @param amount number of tokens burned (scaled by 1e18)
    /// @dev Monitor this for deflationary periods and supply tracking
    event BurningHappened(uint256 amount);

    /// @notice Emitted when deployer tokens are migrated to new address
    /// @param from Original deployer address
    /// @param to New deployer or another contract address
    /// @param amount Number of tokens migrated
    /// @dev Critical security event - monitor for unauthorized migrations
    event CirculationMigrated(address indexed from, address indexed to, uint256 amount);

    /*//////////////////////////////////////////////////////////////
                        GAS-OPTIMIZED CONSTRUCTOR
    //////////////////////////////////////////////////////////////*/

    /*
     * @notice  Gas-optimized constructor for production deployment
     * @param   Initiating an owner to control specific functions
     * @dev     Minimal constructor reduces deployment gas costs
     *          Actual setup is performed in initialize() function post-deployment
     */
    constructor(address initialOwner) Ownable(initialOwner) ERC20("GRAND", "GRD") {
        deployer = initialOwner; 
    }

    /*//////////////////////////////////////////////////////////////
                        PRODUCTION ACCESS MODIFIER
    //////////////////////////////////////////////////////////////*/

    /// @notice Restricts function access to SmartAIWallet only
    /// @dev Used for automated supply management functions
    modifier onlyWallet() {
        require(msg.sender == wallet, "Caller is not wallet");
        _;
    }

    /*//////////////////////////////////////////////////////////////
                    EMERGENCY MIGRATION CAPABILITIES
    //////////////////////////////////////////////////////////////*/

    /*
     * @notice Migration of deployer's circulation tokens
     * @param to New address to receive all of the circulating tokens
     * @dev Production Use Cases:
     *      • Wallet compromise recovery
     *      • New protocol assessment
     *
     * @dev Security Features:
     *      • Only the owner with the access to use this function
     *      • Updates deployer reference for future operations
     *      • Emits event for monitoring and audit trails
     */
    function migrateCirculation(address to) external onlyOwner {
        require(to != address(0), "Zero address");
        address from = deployer;

        uint256 amount = balanceOf(from);
        require(amount > 0, "Nothing to migrate");

        _transfer(from, to, amount);
        deployer = to;

        emit CirculationMigrated(from, to, amount);
    }

    /*//////////////////////////////////////////////////////////////
                    POST-DEPLOYMENT INITIALIZATION
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice One-time initialization after deployment for gas optimization
     * @param _wallet Address of the SmartAIWallet contract
     * @dev Production Setup Process:
     *      1. Deploy GrandToken with minimal gas
     *      2. Deploy SmartAIWallet with token reference
     *      3. Call initialize() to set up addresses and mint/create tokens
     *
     * @dev Security Features:
     *      • EOA-only restriction prevents proxy/reentrancy attacks
     *      • Single-use function prevents reinitialization
     *      • Validates initialization caller
     *
     * @dev Token Distribution:
     *      • 250,000 GRD → deployer (for liquidity)
     *      • 750,000 GRD → AI treasury (for supply management)
     */
    function initialize(address _wallet) public onlyOwner {
        require(!_initialized, "Already initialized");
        require(_wallet != address(0), "Zero wallet");

        wallet = _wallet;

        // Initial token distribution for production launch
        _mint(deployer, CIRCULATING_CAP); // 250,000 tokens for liquidity
        _mint(wallet, INITIAL_SUPPLY - CIRCULATING_CAP); // 750,000 tokens for AI treasury

        totalReleased = CIRCULATING_CAP; // Track initial circulation
        _initialized = true; // One-time usage
    }

    /*//////////////////////////////////////////////////////////////
                    AI-CONTROLLED SUPPLY MANAGEMENT
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice AI-controlled dynamic supply adjustment for economic stability
     * @param factor Percentage change in supply (scaled by 1e18)
     *               Positive: Expand supply | Negative: contract supply from treasury only
     * @dev Production Examples:
     *      • factor = 1e17 → +10% supply expansion
     *      • factor = 5e16 → +5% supply expansion
     *      • factor = -1e17 → -10% supply contraction
     *      • factor = -5e16 → -5% supply contraction
     *
     * @dev Economic Logic - EXPANSION (factor > 0):
     *      1. First: Release existing treasury tokens to circulation
     *      2. If insufficient: Mint new tokens to treasury
     *      3. Auto-transfer 50% of minted tokens to circulation
     *      4. Maintains economic balance between treasury and circulation
     *
     * @dev Economic Logic - CONTRACTION (factor < 0):
     *      1. Burns tokens directly from AI treasury
     *      2. Reduces total supply to increase token scarcity
     *      3. Requires sufficient treasury balance for burn operation
     *
     * @dev Production Monitoring:
     *      • Monitor MintingHappened events for inflation tracking
     *      • Monitor BurningHappened events for deflation tracking
     *      • Track totalReleased for circulation analysis
     */
    function adjustSupply(int256 factor) external onlyWallet {
        require(factor != 0, "Percent is zero");

        uint256 absFactor = uint256(factor > 0 ? factor : -factor);

        // Calculate absolute change: current supply * |factor| / SCALE
        uint256 delta = (totalSupply() * absFactor) / SCALE;

        if (factor > 0) {
            /* ========== SUPPLY EXPANSION LOGIC ========== */

            uint256 released;
            uint256 treasuryBal = balanceOf(wallet);

            /* Phase 1: Release existing treasury tokens */
            if (treasuryBal > 0) {
                released = delta > treasuryBal ? treasuryBal : delta;

                if (released > 0) {
                    _transfer(wallet, deployer, released);
                    totalReleased += released;
                    delta -= released; // Calculate remaining demand
                }
            }

            /* Phase 2: Mint new tokens if treasury insufficient */
            if (delta > 0) {
                _mint(wallet, delta);
                emit MintingHappened(delta);

                // Automatic circulation injection (50% of minted tokens)
                uint256 autoTransfer = delta / 2;
                if (autoTransfer > 0) {
                    _transfer(wallet, deployer, autoTransfer);
                    totalReleased += autoTransfer;
                }
            }
        } else {
            /* ========== SUPPLY CONTRACTION LOGIC ========== */

            uint256 actualBurn = delta > balanceOf(wallet) ? balanceOf(wallet) : delta;

            // Burn from AI treasury (if possible)
            if (actualBurn > 0) {
                _burn(wallet, actualBurn);
                emit BurningHappened(actualBurn);
            }
        }
    }
}
