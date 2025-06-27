// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title Govinance Token (GBI)
 * @dev • 25 % of the initial supply is minted to the deployer (for liquidity).
 *      • 75 % is minted to the AI-controlled treasury wallet.
 *      • No hard max-supply; the AI can mint/burn within the limits you set
 *        off-chain (e.g. per-call or per-time-window caps).
 */
contract GovinanceToken is ERC20 {
    /*//////////////////////////////////////////////////////////////
                               STATE
    //////////////////////////////////////////////////////////////*/

    /// @notice one-time fixed mint on deployment (1 000 000 GBI, 18 dec)
    uint256 public constant INITIAL_SUPPLY = 1_000_000 * 1e18;

    /// @notice 25 % of INITIAL_SUPPLY → 250 000 GBI
    uint256 public constant CIRCULATING_CAP = INITIAL_SUPPLY / 4;

    /// @notice `factor` values are scaled by 1e18 (so 10% ⇒ 0.10*1e18 = 1e17)
    uint256 private constant SCALE = 1e18; 

    /// @notice the AI gets updated for the smart-wallet-contract once
    bool private s_updatedAi = true; 

    /// @notice how many tokens have moved from treasury → circulation so far
    uint256 public totalReleased;

    /// @notice wallet allowed to call adjustSupply()
    address public aiController;

    /// @notice the deployer
    address public deployer; 

    /*//////////////////////////////////////////////////////////////
                                EVENTS
    //////////////////////////////////////////////////////////////*/

    /// @notice Emitted when new tokens are minted into the AI treasury
    event MintingHappened(uint256 amount);

    /// @notice Emitted when tokens are burned from the AI treasury
    event BurningHappened(uint256 amount);

    /*//////////////////////////////////////////////////////////////
                              CONSTRUCTOR
    //////////////////////////////////////////////////////////////*/

    /**
     * @param _aiController EOA or contract that will govern mint/burn.
     */
    constructor(address _aiController, address _deployer) ERC20("Govinance", "GBI") {
        deployer = _deployer; 
        aiController = _aiController;

        // 1) Mint circulating tranche to deployer
        _mint(deployer, CIRCULATING_CAP);

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
        require(msg.sender == aiController, "GBI: caller is not AI");
        _;
    }

    /*//////////////////////////////////////////////////////////////
                           SUPPLY MANAGEMENT
    //////////////////////////////////////////////////////////////*/

    /**
     * @notice Increase or decrease totalSupply by a non-fixed factor number.
     * @dev Positive `factor` releases first from treasury, then mints the
     *  shortfall (no hard cap). Negative burns from AI balance (If there are enough to burn).
     * @param factor as a non-fixed percent change (e.g. +10, −5, +0.053, -12.245, etc...). 0 does nothing.
     */
    function adjustSupply(int256 factor) external onlyAI {
        require(factor != 0, "GBI: percent is zero");

        uint256 current = totalSupply();
        uint256 absFactor = uint256(factor > 0 ? factor : -factor);

        // delta = currentSupply * |percent| / SCALE
        uint256 delta = (current * absFactor) / SCALE;
        
        if (factor > 0) {
            /* ---------- EXPAND SUPPLY ---------- */

            uint256 released;
            uint256 treasuryBal = balanceOf(aiController);

            /* 1) release up to `delta` from treasury */
            if (treasuryBal > 0) {
                released = delta > treasuryBal ? treasuryBal : delta;

                if (released > 0) {
                    _transfer(aiController, deployer, released);
                    totalReleased += released;
                    delta -= released; // unmet demand
                }
            }

            /* 2) if still not satisfied, mint the remainder to treasury */
            if (delta > 0) {
                _mint(aiController, delta);
                emit MintingHappened(delta); 

                // auto-transfer 50% of what was just minted
                uint256 autoTransfer = delta / 2;

                if (autoTransfer > 0) {
                    _transfer(aiController, deployer, autoTransfer);
                    totalReleased += autoTransfer;
                }
            }
        } else {
            /* ---------- CONTRACT SUPPLY ---------- */

            // Ensure treasury (AI wallet) holds enough to burn
            require(
                balanceOf(aiController) >= delta,
                "GBI: AI balance < burn amount"
            );

            _burn(aiController, delta);
            emit BurningHappened(delta);
        }
    }

    /*//////////////////////////////////////////////////////////////
                        GOVERNANCE (AI WALLET ROTATE)
    //////////////////////////////////////////////////////////////*/

    function updateAIController(address newAI) external {
        require(s_updatedAi == true, "AI wallet already updated"); 
        uint256 treasuryReserve = INITIAL_SUPPLY - CIRCULATING_CAP;
        _transfer(aiController, newAI, treasuryReserve);
        aiController = newAI;
        s_updatedAi = false; 
    }
}