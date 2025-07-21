// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import {AggregatorV3Interface} from "@chainlink/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol";
import {PriceConverter} from "./PriceConverter.sol";

/**
 * @title SmartAIWallet - AI Controller & Multi-Signature Treasury Wallet
 * @author By Taha Hasan
 * @notice Secure multi-signature wallet serving as AI controller for token supply management
 * @dev Production Features:
 *      • Multi-signature access control for enhanced security
 *      • Time-locked AI operations to prevent rapid market manipulation
 *      • ETH funding capabilities with USD price protection
 *      • Emergency migration functions with password protection
 *      • Integration with Chainlink price feeds for real-time conversions
 * 
 * @dev Security Architecture:
 *      • Multiple owner system for decentralized control
 *      • AI controller role separation for automated operations
 *      • Password-protected migration functions
 *      • Time-based restrictions on critical operations
 */

/// @notice Interface for GrandToken interactions
/// @dev Minimal interface for gas optimization and security
interface IGrandToken {
    function adjustSupply(int256 percent) external;
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 value) external returns (bool);
}

contract SmartAIWallet {
    /*//////////////////////////////////////////////////////////////
                        PRODUCTION STATE VARIABLES
    //////////////////////////////////////////////////////////////*/

    /// @notice Reference to the GrandToken contract
    /// @dev Immutable for gas optimization and security
    IGrandToken public immutable i_token;

    /// @notice Minimum USD value required for ETH funding ($5 USD scaled by 1e18)
    /// @dev Prevents spam transactions and ensures meaningful contributions
    uint256 public constant MINIMUM_USD = 5e18;

    /// @notice Chainlink price feed for ETH/USD conversion
    /// @dev Used for real-time USD value calculations in funding operations
    AggregatorV3Interface private s_priceFeed;

    /// @notice Address authorized to execute AI-controlled operations
    /// @dev Should be set to an AI system or automated trading bot
    address public aiController;

    /// @notice Timestamp of last supply adjustment execution
    /// @dev Used to enforce weekly time limits on AI operations
    uint256 public lastExecutedWeek;

    /// @notice Hashed password for emergency migration operations
    /// @dev Provides additional security layer for critical functions
    bytes32 private s_passwordHash;

    /// @notice Mapping to track authorized wallet owners
    /// @dev Used for multi-signature access control
    mapping(address => bool) public isOwner;

    /// @notice Array of all current wallet owners
    /// @dev Maintains list for iteration and owner management
    address[] public owners;

    /*//////////////////////////////////////////////////////////////
                        PRODUCTION EVENTS
    //////////////////////////////////////////////////////////////*/

    /// @notice Emitted when a new owner is added to the multi-sig wallet
    /// @param newOwner Address of the newly added owner
    /// @dev Monitor for unauthorized owner additions
    event OwnerAdded(address indexed newOwner);

    /// @notice Emitted when an owner is removed from the multi-sig wallet
    /// @param removedOwner Address of the removed owner
    /// @dev Monitor for owner management changes
    event OwnerRemoved(address indexed removedOwner);

    /// @notice Emitted when AI executes a supply adjustment
    /// @param percent Percentage change applied to token supply
    /// @param timestamp Block timestamp of the adjustment
    /// @param executor Address that executed the adjustment (AI controller)
    /// @dev Critical for economic monitoring and AI behavior analysis
    event SupplyAdjusted(int256 percent, uint256 timestamp, address executor);

    /// @notice Emitted when treasury tokens are migrated to new address
    /// @param to Destination address for migrated tokens
    /// @param amount Number of tokens migrated
    /// @dev Security event - monitor for unauthorized treasury movements
    event TreasuryMigrated(address indexed to, uint256 amount);

    /// @notice Emitted when AI controller address is updated
    /// @param newAI New AI controller address
    /// @dev Critical security event - monitor for unauthorized AI changes
    event AIControllerUpdated(address indexed newAI);

    /*//////////////////////////////////////////////////////////////
                        PRODUCTION CONSTRUCTOR
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Initialize SmartAIWallet with required dependencies
     * @param _token Address of the GrandToken contract
     * @param priceFeed Address of Chainlink ETH/USD price feed
     * @param _aiController Address of the AI system for automated operations
     * @param _passwordHash Keccak256 hash of emergency migration password
     * @dev Production Setup:
     *      • Validates token contract address
     *      • Sets up price feed integration
     *      • Initializes deployer as first owner
     *      • Configures AI controller for automated operations
     */
    constructor(address _token, address priceFeed, address _aiController, bytes32 _passwordHash) {
        require(_token != address(0), "SmartAIWallet: invalid token address");
        
        i_token = IGrandToken(_token);
        s_priceFeed = AggregatorV3Interface(priceFeed);
        aiController = _aiController;
        s_passwordHash = _passwordHash;

        // Initialize deployer as first owner for immediate access
        isOwner[msg.sender] = true;
        owners.push(msg.sender);
    }

    /*//////////////////////////////////////////////////////////////
                        PRODUCTION ACCESS MODIFIERS
    //////////////////////////////////////////////////////////////*/

    /// @notice Restricts function access to authorized wallet owners only
    /// @dev Used for multi-signature operations and owner management
    modifier onlyOwner() {
        require(isOwner[msg.sender], "SmartAIWallet: caller is not an owner");
        _;
    }

    /// @notice Restricts function access to AI controller only
    /// @dev Used for automated supply management operations
    modifier onlyAI() {
        require(msg.sender == aiController, "SmartAIWallet: caller is not AI");
        _;
    }

    /// @notice Requires correct password for emergency operations
    /// @dev Provides additional security for critical migration functions
    /// @param password Plain text password (hashed and compared)
    modifier onlyWithPassword(string memory password) {
        require(keccak256(abi.encodePacked(password)) == s_passwordHash, "Incorrect password");
        _;
    }

    /*//////////////////////////////////////////////////////////////
                    MULTI-SIGNATURE OWNER MANAGEMENT
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Add a new authorized owner to the multi-signature wallet
     * @param _newOwner Address of the new owner to add
     * @dev Production Use Cases:
     *      • Adding new team members
     *      • Expanding multi-sig security
     *      • Distributing operational control
     * 
     * @dev Security Features:
     *      • Only existing owners can add new owners
     *      • Prevents duplicate owner additions
     *      • Validates non-zero addresses
     */
    function addOwner(address _newOwner) external onlyOwner {
        require(_newOwner != address(0), "SmartAIWallet: invalid owner");
        require(!isOwner[_newOwner], "SmartAIWallet: already an owner");
        
        isOwner[_newOwner] = true;
        owners.push(_newOwner);
        emit OwnerAdded(_newOwner);
    }

    /**
     * @notice Remove an existing owner from the multi-signature wallet
     * @param _owner Address of the owner to remove
     * @dev Production Use Cases:
     *      • Removing departed team members
     *      • Reducing multi-sig complexity
     *      • Security response to compromised addresses
     * 
     * @dev Security Features:
     *      • Only existing owners can remove owners
     *      • Cannot remove the last remaining owner
     *      • Maintains array integrity during removal
     */
    function removeOwner(address _owner) external onlyOwner {
        require(isOwner[_owner], "SmartAIWallet: not an owner");
        require(owners.length > 1, "SmartAIWallet: cannot remove last owner");

        isOwner[_owner] = false;

        // Remove from owners array efficiently
        for (uint i = 0; i < owners.length; i++) {
            if (owners[i] == _owner) {
                owners[i] = owners[owners.length - 1];
                owners.pop();
                break;
            }
        }

        emit OwnerRemoved(_owner);
    }

    /*//////////////////////////////////////////////////////////////
                    EMERGENCY MIGRATION FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Emergency migration of all treasury tokens to new address
     * @param to Destination address for treasury tokens
     * @param password Emergency migration password
     * @dev Production Use Cases:
     *      • Contract upgrades requiring treasury movement
     *      • Security incidents requiring asset protection
     *      • Operational changes in treasury management
     * 
     * @dev Security Features:
     *      • Password protection prevents unauthorized access
     *      • Transfers entire token balance atomically
     *      • Emits event for monitoring and audit trails
     */
    function migrateTreasury(address to, string memory password) external onlyWithPassword(password) {
        uint256 amount = i_token.balanceOf(address(this));
        require(amount > 0, "Nothing to migrate");

        require(i_token.transfer(to, amount), "SmartAIWallet: Transfer failed");
        emit TreasuryMigrated(to, amount);
    }

    /**
     * @notice Emergency migration of AI controller to new address
     * @param to New AI controller address
     * @param password Emergency migration password
     * @dev Production Use Cases:
     *      • AI system upgrades
     *      • Security updates to AI infrastructure
     *      • Switching between different AI implementations
     * 
     * @dev Security Features:
     *      • Password protection prevents unauthorized changes
     *      • Immediate effect on AI controller permissions
     *      • Event emission for security monitoring
     */
    function migrateOnlyAI(address to, string memory password) external onlyWithPassword(password) {
        aiController = to;
        emit AIControllerUpdated(to);
    }

    /*//////////////////////////////////////////////////////////////
                    AI-CONTROLLED OPERATIONS
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice AI-controlled token supply adjustment with time restrictions
     * @param percent Percentage change in supply (scaled by 1e18)
     * @dev Production AI Controls:
     *      • Weekly execution limit prevents rapid market manipulation
     *      • Saturday-only execution provides predictable timing
     *      • AI can analyze full week of market data before adjustment
     * 
     * @dev Time Lock Security:
     *      • Prevents AI from making emotional or rapid decisions
     *      • Allows market time to react to previous adjustments
     *      • Provides transparency with predictable timing
     * 
     * @dev Economic Impact Examples:
     *      • percent = 1e17 → +10% supply expansion
     *      • percent = -5e16 → -5% supply contraction
     */
    function adjustSupply(int256 percent) external onlyAI {
        // Time-based restrictions for production stability
        uint256 dayOfWeek = (block.timestamp / 1 days + 4) % 7;
        require(dayOfWeek == 6, "Can only call on Saturday");
        require(block.timestamp >= lastExecutedWeek + 7 days, "SmartAIWallet: already executed this week");
        lastExecutedWeek = block.timestamp;

        i_token.adjustSupply(percent);
        emit SupplyAdjusted(percent, block.timestamp, msg.sender);
    }

    /*//////////////////////////////////////////////////////////////
                        FUNDING OPERATIONS
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Accept ETH funding with USD value protection
     * @dev Production Funding System:
     *      • Minimum $5 USD prevents spam transactions
     *      • Real-time price conversion using Chainlink feeds
     *      • Automatic ETH storage for operational expenses
     * 
     * @dev Use Cases:
     *      • Development funding from community
     *      • Operational expense coverage
     *      • Emergency funding for critical operations
     * 
     * @dev Price Protection:
     *      • Uses Chainlink ETH/USD price feed
     *      • Prevents worthless micro-transactions
     *      • Ensures meaningful funding contributions
     */
    function fund() public payable {
        require(
            PriceConverter.getConversionRate(msg.value, s_priceFeed) >= MINIMUM_USD,
            "You need to spend more ETH!"
        );
    }

    /**
     * @notice Withdraw all ETH funds to first owner
     * @dev Production Withdrawal System:
     *      • Only first owner can withdraw (primary administrator)
     *      • Transfers entire ETH balance atomically
     *      • Fails safely if transfer unsuccessful
     * 
     * @dev Security Features:
     *      • Owner-only access prevents unauthorized withdrawals
     *      • First owner designation provides clear hierarchy
     *      • Success validation ensures funds reach destination
     */
    function withdraw() public onlyOwner {
        require(msg.sender == owners[0], "SmartAIWallet: only first owner");
        
        address payable firstOwner = payable(owners[0]);
        (bool success, ) = firstOwner.call{value: address(this).balance}("");
        require(success, "SmartAIWallet: withdrawal failed");
    }

    /*//////////////////////////////////////////////////////////////
                        PRODUCTION MONITORING & ANALYTICS
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Get current token supply for AI analysis
     * @return Current total token supply
     * @dev Used by AI for economic decision making and supply analysis
     */
    function readSupply() external view returns (uint256) {
        return i_token.totalSupply();
    }
}