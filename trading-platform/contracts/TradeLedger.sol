// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract TradeLedger {
    // Owner address
    address public owner;
    
    // Access levels
    mapping(address => AccessLevel) public accessLevels;
    
    enum AccessLevel {
        NONE,
        READER,      // فقط خواندن
        RECORDER,    // ثبت معاملات
        ADMIN        // مدیریت کامل
    }
    
    struct Trade {
        uint256 tradeId;
        string symbol;
        uint256 priceCents;
        uint256 quantity;
        uint256 buyOrderId;
        uint256 sellOrderId;
        uint256 timestamp;
    }

    Trade[] private trades;
    mapping(uint256 => uint256) private tradeIdToIndexPlus1;

    // Events
    event TradeRecorded(
        uint256 tradeId,
        string symbol,
        uint256 priceCents,
        uint256 quantity,
        uint256 buyOrderId,
        uint256 sellOrderId,
        uint256 timestamp
    );
    
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event AccessLevelChanged(address indexed user, AccessLevel level);
    event IncidentLogged(uint256 indexed timestamp, string description, address indexed reporter);

    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this");
        _;
    }
    
    modifier onlyAdmin() {
        require(
            msg.sender == owner || accessLevels[msg.sender] == AccessLevel.ADMIN,
            "Only admin can call this"
        );
        _;
    }
    
    modifier onlyRecorder() {
        require(
            msg.sender == owner || 
            accessLevels[msg.sender] == AccessLevel.RECORDER ||
            accessLevels[msg.sender] == AccessLevel.ADMIN,
            "Only recorder or higher can call this"
        );
        _;
    }

    constructor() {
        owner = msg.sender;
        accessLevels[msg.sender] = AccessLevel.ADMIN;
    }

    // Owner management
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "New owner cannot be zero address");
        address oldOwner = owner;
        owner = newOwner;
        accessLevels[newOwner] = AccessLevel.ADMIN;
        emit OwnershipTransferred(oldOwner, newOwner);
    }

    // Access control
    function setAccessLevel(address user, AccessLevel level) external onlyAdmin {
        accessLevels[user] = level;
        emit AccessLevelChanged(user, level);
    }

    function getAccessLevel(address user) external view returns (AccessLevel) {
        return accessLevels[user];
    }

    // Trade recording (با کنترل دسترسی)
    function recordTrade(
        uint256 tradeId,
        string calldata symbol,
        uint256 priceCents,
        uint256 quantity,
        uint256 buyOrderId,
        uint256 sellOrderId
    ) external onlyRecorder {
        require(tradeIdToIndexPlus1[tradeId] == 0, "tradeId already recorded");

        trades.push(
            Trade({
                tradeId: tradeId,
                symbol: symbol,
                priceCents: priceCents,
                quantity: quantity,
                buyOrderId: buyOrderId,
                sellOrderId: sellOrderId,
                timestamp: block.timestamp
            })
        );

        tradeIdToIndexPlus1[tradeId] = trades.length;

        emit TradeRecorded(tradeId, symbol, priceCents, quantity, buyOrderId, sellOrderId, block.timestamp);
    }

    // Incident management
    function logIncident(string calldata description) external onlyRecorder {
        emit IncidentLogged(block.timestamp, description, msg.sender);
    }

    // View functions (همه می‌توانند بخوانند)
    function count() external view returns (uint256) {
        return trades.length;
    }

    function getTrade(uint256 index) external view returns (
        uint256 tradeId,
        string memory symbol,
        uint256 priceCents,
        uint256 quantity,
        uint256 buyOrderId,
        uint256 sellOrderId,
        uint256 timestamp
    ) {
        Trade memory t = trades[index];
        return (t.tradeId, t.symbol, t.priceCents, t.quantity, t.buyOrderId, t.sellOrderId, t.timestamp);
    }

    function exists(uint256 tradeId) external view returns (bool) {
        return tradeIdToIndexPlus1[tradeId] != 0;
    }
}