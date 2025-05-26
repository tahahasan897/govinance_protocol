// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract TranscriptToken is ERC20 {
    /// @notice Address allowed to call adjustSupply()
    address public aiController;

    /// @dev Only allow calls from the AI controller
    modifier onlyAI() {
        require(msg.sender == aiController, "Transcript: caller is not AI");
        _;
    }

    /// @param initialSupply  Initial number of tokens (in whole units; decimals = 18)
    /// @param _aiController  Address that will control supply adjustments
    constructor(uint256 initialSupply, address _aiController)
        ERC20("Transcript", "TCRIPT")
    {
        require(_aiController != address(0), "Transcript: zero-address AI");
        aiController = _aiController;

        // Mint to deployer
        _mint(msg.sender, initialSupply);
    }

    /// @notice Increase or decrease totalSupply by a % (signed) amount,
    ///         routing newly minted tokens or burns through the AI controller.
    /// @param percent  The percent change, e.g. +10 for +10%, -5 for –5%.
    function adjustSupply(int256 percent) external onlyAI {
        if (percent > 0) {
            // Mint `percent`% of current supply to the AI controller
            uint256 delta = (totalSupply() * uint256(percent)) / 100;
            _mint(aiController, delta);
        } else if (percent < 0) {
            // Burn `|percent|`% from the AI controller’s balance
            uint256 delta = (totalSupply() * uint256(-percent)) / 100;
            require(
                balanceOf(aiController) >= delta,
                "Transcript: AI has insufficient balance to burn"
            );
            _burn(aiController, delta);
        }
        // percent == 0 → no change
    }

    /// @notice If you want to transfer the AI‐control, allow
    ///         the current controller to assign a new one.
    function updateAIController(address newAI) external onlyAI {
        require(newAI != address(0), "Transcript: zero-address AI");
        aiController = newAI;
    }
}
