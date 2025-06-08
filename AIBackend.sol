// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {AggregatorV3Interface} from "@chainlink/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol";
import {PriceConverter} from "./PriceConverter.sol";

/**
 * @title AIBackend logic
 * @dev • Make sure that the only functions that can call and 
 *        transact from the AI wallet. 
 *      • It can transact the adjustSupply() function once every 
 *        Saturday. 
 *      • Rotating the AI wallet from the backend hasn't yet implement. 
 *        In the future, it will be discussed whether to rotate to another
 *        wallet. 
 */

interface ITranscriptToken {
    function adjustSupply(int256 percent) external;
    function updateAIController(address newAI) external;
}

contract AIAgent {
    /// @notice off-chain logic bot / EOA
    address public immutable logicBackend;
    /// @notice TranscriptToken contract to control
    address public transcriptToken;

    /// @notice minimum eth allowed to get into the account
    uint256 public constant MINIMUM_USD = 5e18; 

    /// @notice Getting the price feed from chainlink API in order to get the dollar value in ETH
    AggregatorV3Interface private s_priceFeed; 

    /// @notice tracking the week number when adjust() was last run
    uint256 public lastExecutedWeek; 

    event SupplyAdjusted(int256 indexed percentChange, uint256 timestamp, address executor); 
    event SupplyAdjustmentSkipped(int256 indexed percentChange, uint256 timestamp, address executor); 

    /*//////////////////////////////////////////////////////////////
                              CONSTRUCTOR
    //////////////////////////////////////////////////////////////*/

    constructor(address _logicBackend, address _transcriptToken, address priceFeed) {
        logicBackend = _logicBackend;
        transcriptToken = _transcriptToken;
        s_priceFeed = AggregatorV3Interface(priceFeed); 
    }

    /*//////////////////////////////////////////////////////////////
                                MODIFIER
    //////////////////////////////////////////////////////////////*/

    modifier onlyLogicBackend() {
        require(msg.sender == logicBackend, "Not authorized AI backend");
        _;
    }

    /*//////////////////////////////////////////////////////////////
                            INTERACTION LOGIC
    //////////////////////////////////////////////////////////////*/

    ///@notice Ajust supply once per week, only on Saturday
    function adjust(int256 percent) external onlyLogicBackend {
        require(_isSaturday(), "AIBackend: only Saturday");

        // compute current week number (weeks since unix epoch)
        uint256 currentWeek = block.timestamp / 1 weeks;
        require(currentWeek > lastExecutedWeek, "AIBackend: Already executed this week"); 

        lastExecutedWeek = currentWeek;

        if (percent == 0) {
            emit SupplyAdjustmentSkipped(percent, block.timestamp, msg.sender);
            return; 
        }

        ITranscriptToken(transcriptToken).adjustSupply(percent);
        emit SupplyAdjusted(percent, block.timestamp, msg.sender); 
    }

    /// @notice Rotate AI controller in TranscriptToken (unchanged)
    function rotateAI(address newAI) external onlyLogicBackend {
        ITranscriptToken(transcriptToken).updateAIController(newAI);
    }

    /*//////////////////////////////////////////////////////////////
                              TODO
    //////////////////////////////////////////////////////////////*/
    /// @notice Accept ETH no less than 5 dollars
    receive() external payable {
        uint256 usdValue = PriceConverter.getConversionRate(msg.value, s_priceFeed);
        require(usdValue >= MINIMUM_USD, "You need to spend more than 5 dollars!");
    }

    /// @notice Returns true if current UTC day is Saturday
    function _isSaturday() internal view returns (bool) {
        // 0 = Sunday, ..., 6 = Saturday
        uint8 dayOfWeek = uint8((block.timestamp / 86400 + 4) % 7);
        return dayOfWeek == 6; 
    }
}
