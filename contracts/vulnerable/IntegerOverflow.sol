// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

/// @title VulnerableToken — integer overflow (DO NOT DEPLOY, Solidity <0.8 only)
contract VulnerableToken {
    mapping(address => uint256) public balances;
    uint256 public totalSupply;

    constructor(uint256 initialSupply) {
        balances[msg.sender] = initialSupply;
        totalSupply = initialSupply;
    }

    /// @notice Vulnerable: no overflow check on transfer
    function transfer(address to, uint256 amount) external returns (bool) {
        // ❌ balances[msg.sender] - amount can underflow
        balances[msg.sender] -= amount;
        // ❌ balances[to] + amount can overflow
        balances[to] += amount;
        return true;
    }
}
