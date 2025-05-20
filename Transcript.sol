// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TranscriptToken {
    string public name = "Transcript";
    string public symbol = "TCRIPT";
    uint8 public decimals = 18;
    uint256 public totalSupply;
    address public aiController;
    mapping(address => uint256) public balanceOf;

    event Transfer(address indexed from, address indexed to, uint256 value);

    constructor(uint256 _initialSupply, address _aiController) {
        totalSupply = _initialSupply;
        balanceOf[msg.sender] = _initialSupply;
        aiController = _aiController;
    }

    modifier onlyAI() {
        require(msg.sender == aiController, "Not authorized");
        _;
    }

    function transfer(address _to, uint256 _value) external returns (bool) {
        require(balanceOf[msg.sender] >= _value, "Insufficient balance");
        balanceOf[msg.sender] -= _value;
        balanceOf[_to] += _value;
        emit Transfer(msg.sender, _to, _value);
        return true;
    }

    function adjustSupply(int256 percent) external onlyAI {
        if (percent > 0) {
            uint256 amount = (totalSupply * uint256(percent)) / 100;
            balanceOf[aiController] += amount;
            totalSupply += amount;
        } else {
            uint256 amount = (totalSupply * uint256(-percent)) / 100;
            require(balanceOf[aiController] >= amount, "Not enough to burn");
            balanceOf[aiController] -= amount;
            totalSupply -= amount;
        }
    }
}
