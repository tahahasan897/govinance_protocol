// SPDX-License-Identifier: MIT

pragma solidity ^0.8.19; 

import {AggregatorV3Interface} from "@chainlink/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol";
import {PriceConverter} from "./PriceConverter.sol";

interface IGovinanceToken {
    function adjustSupply(int256 percent) external;
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256); 
    function transfer(address to, uint256 value) external returns (bool);
}

contract SmartAIWallet {

    // Address of the GovinanceToken contract
    IGovinanceToken public immutable i_token;

    /// Minimum eth allowed to get into the account
    uint256 public constant MINIMUM_USD = 5e18; 

    /// Getting the price feed from chainlink API in order to get the dollar value in ETH
    AggregatorV3Interface private s_priceFeed; 

    /// @notice wallet allowed to call adjustSupply()
    address public aiController;

    // Track last week adjustSupply was executed
    uint256 public lastExecutedWeek;

    /// @notice password applied before the change
    bytes32 private passwordHash; 

    // Owners management
    mapping(address => bool) public isOwner;
    address[] public owners;


    // Events
    event OwnerAdded(address indexed newOwner);
    event OwnerRemoved(address indexed removedOwner);
    event SupplyAdjusted(int256 percent, uint256 timestamp, address executor);
    event TreasuryMigrated(address indexed to, uint256 amount);
    event AIControllerUpdated(address indexed newAI);


    constructor(address _token, address priceFeed, address _aiController, bytes32 _passwordHash ) {
        require(_token != address(0), "SmartAIWallet: invalid token address");
        i_token = IGovinanceToken(_token);
        s_priceFeed = AggregatorV3Interface(priceFeed);
        aiController = _aiController; 
        passwordHash = _passwordHash;

        // Initialize deployer as first owner
        isOwner[msg.sender] = true;
        owners.push(msg.sender);
    }


    modifier onlyOwner() {
        require(isOwner[msg.sender], "SmartAIWallet: caller is not an owner");
        _;
    }


    modifier onlyAI() {
        require(msg.sender == aiController, "SmartAIWallet: caller is not AI"); 
        _; 
    }

    modifier onlyWithPassword(string memory password) {
        require(keccak256(abi.encodePacked(password)) == passwordHash, "Incorrect password"); 
        _; 
    }


    /**
     * @notice Add a new owner. Can only be called by an existing owner.
     */
    function addOwner(address _newOwner) external onlyOwner {
        require(_newOwner != address(0), "SmartAIWallet: invalid owner");
        require(!isOwner[_newOwner], "SmartAIWallet: already an owner");
        isOwner[_newOwner] = true;
        owners.push(_newOwner);
        emit OwnerAdded(_newOwner);
    }


    /**
     * @notice Remove an existing owner. Can only be called by an existing owner.
     *         Cannot remove the last remaining owner.
     */
    function removeOwner(address _owner) external onlyOwner {
        require(isOwner[_owner], "SmartAIWallet: not an owner");
        require(owners.length > 1, "SmartAIWallet: cannot remove last owner");

        isOwner[_owner] = false;

        // Remove from owners array
        for (uint i = 0; i < owners.length; i++) {
            if (owners[i] == _owner) {
                owners[i] = owners[owners.length - 1];
                owners.pop();
                break;
            }
        }

        emit OwnerRemoved(_owner);
    }

    function migrateTreasury(address to, string memory password) external onlyWithPassword(password) {
        uint256 amount = i_token.balanceOf(address(this));
        require(amount > 0, "Nothing to migrate");

        require(i_token.transfer(to, amount), "SmartAIWallet: Transfer failed");
        emit TreasuryMigrated(to, amount);
    }

    function migrateOnlyAI(address to, string memory password) external onlyWithPassword(password) {
        aiController = to; 
        emit AIControllerUpdated(to);
    }

    /**
     * @notice Call totalSupply() from GovinanceToken
     */
    function readSupply() external view returns (uint256) {
        return i_token.totalSupply();
    } 

    /**
     * @notice Adjust token supply by a percent. Can be called once per week by any owner.
     */
    function adjustSupply(int256 percent) external onlyAI {
        // // Make the call gets executed once per week and only on Saturday
        uint256 dayOfWeek = (block.timestamp / 1 days + 4) % 7;
        
        require(dayOfWeek == 6, "Can only call on Saturday"); 
        require(block.timestamp >= lastExecutedWeek + 7 days, "SmartAIWallet: already executed this week");
        lastExecutedWeek = block.timestamp;

        i_token.adjustSupply(percent);
        emit SupplyAdjusted(percent, block.timestamp, msg.sender);
    }

    /// @notice Funds our contract based on the ETH/USD price.
    function fund() public payable {
        require(PriceConverter.getConversionRate(msg.value, s_priceFeed) >= MINIMUM_USD, "You need to spend more ETH!");
    }

    /// @notice Funds can be withdrawn by the first owner. 
    function wthdraw() public onlyOwner {
        require(msg.sender == owners[0], "SmartAIWallet: only first owner");
        address payable firstOwner = payable(owners[0]);
        (bool success, ) = firstOwner.call{ value: address(this).balance }("");
        require(success, "SmartAIWallet: withdrawal failed");
    }
}