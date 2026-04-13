// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

/// @title VulnerableBank — classic reentrancy example (DO NOT DEPLOY)
contract VulnerableBank {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    /// @notice Vulnerable: state updated AFTER external call
    function withdraw() external {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "no balance");
        // ❌ External call before state update — reentrancy vector
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
        balances[msg.sender] = 0;
    }

    function getBalance() external view returns (uint256) {
        return address(this).balance;
    }
}
