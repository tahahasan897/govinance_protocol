// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title Transcript Token (TCRIPT)
 * @dev • 25 % of the initial supply is minted to the deployer (for liquidity).
 *      • 75 % is minted to the AI-controlled treasury wallet.
 *      • No hard max-supply; the AI can mint/burn within the limits you set
 *        off-chain (e.g. per-call or per-time-window caps).
 */
contract TranscriptToken is ERC20 {
    /*//////////////////////////////////////////////////////////////
                               STATE
    //////////////////////////////////////////////////////////////*/

    /// @notice wallet allowed to call adjustSupply()
    address public aiController;

    /// @notice one-time fixed mint on deployment (1 000 000 TCRIPT, 18 dec)
    uint256 public constant INITIAL_SUPPLY = 1_000_000 * 1e18;

    /// @notice 25 % of INITIAL_SUPPLY → 250 000 TCRIPT
    uint256 public constant CIRCULATING_CAP = INITIAL_SUPPLY / 4;

    /// @notice how many tokens have moved from treasury → circulation so far
    uint256 public totalReleased;

    /*//////////////////////////////////////////////////////////////
                              CONSTRUCTOR
    //////////////////////////////////////////////////////////////*/

    /**
     * @param _aiController EOA or contract that will govern mint/burn.
     */
    constructor(address _aiController) ERC20("Transcript", "TCRIPT") {
        require(_aiController != address(0), "TCRIPT: zero-address AI");
        aiController = _aiController;

        // 1) Mint circulating tranche to deployer
        _mint(msg.sender, CIRCULATING_CAP);

        // 2) Mint treasury reserve to AI wallet
        uint256 treasuryReserve = INITIAL_SUPPLY - CIRCULATING_CAP; // 750 000
        _mint(aiController, treasuryReserve);

        // 3) Book-keep how much has left treasury so far (none yet)
        totalReleased = CIRCULATING_CAP;
    }

    /*//////////////////////////////////////////////////////////////
                              MODIFIERS
    //////////////////////////////////////////////////////////////*/

    modifier onlyAI() {
        require(msg.sender == aiController, "TCRIPT: caller is not AI");
        _;
    }

    /*//////////////////////////////////////////////////////////////
                           SUPPLY MANAGEMENT
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Increase or decrease totalSupply by an integer percentage.
     * @dev Positive `percent` releases first from treasury, then mints the
     *      shortfall (no hard cap). Negative burns from AI balance.
     * @param percent whole-percent change (e.g. +10, −5). 0 does nothing.
     */
    function adjustSupply(int256 percent) external onlyAI {
        require(percent != 0, "TCRIPT: percent is zero");

        uint256 current = totalSupply();
        uint256 absPercent = uint256(percent > 0 ? percent : -percent);

        // delta = currentSupply * |percent| / 100
        uint256 delta = (current * absPercent) / 100;
        // Emit a warning event
        if (delta == 0) return; // nothing to do
        
        if (percent > 0) {
            /* ---------- EXPAND SUPPLY ---------- */

            uint256 released;
            uint256 treasuryBal = balanceOf(aiController);

            /* 1) release up to `delta` from treasury */
            if (treasuryBal > 0) {
                released = delta > treasuryBal ? treasuryBal : delta;

                if (released > 0) {
                    _transfer(aiController, msg.sender, released);
                    totalReleased += released;
                    delta -= released; // unmet demand
                }
            }

            /* 2) if still not satisfied, mint the remainder to treasury */
            if (delta > 0) {
                _mint(aiController, delta);

                // auto-transfer some of this to circulation
                uint256 autoTransfer = delta / 2; // 50%
                if (autoTransfer > 0) {
                    _transfer(aiController, msg.sender, autoTransfer);
                    totalReleased += autoTransfer; 
                }
            }
        } else {
            /* ---------- CONTRACT SUPPLY ---------- */

            // Ensure treasury (AI wallet) holds enough to burn
            require(
                balanceOf(aiController) >= delta,
                "TCRIPT: AI balance < burn amount"
            );

            _burn(aiController, delta);
        }
    }

    /*//////////////////////////////////////////////////////////////
                        GOVERNANCE (AI WALLET ROTATE)
    //////////////////////////////////////////////////////////////*/

    function updateAIController(address newAI) external onlyAI {
        require(newAI != address(0), "TCRIPT: zero-address AI");
        aiController = newAI;
    }
}
