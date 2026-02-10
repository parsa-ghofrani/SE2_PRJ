// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract TradeLedger {
    struct Trade {
        uint256 tradeId;
        string symbol;
        uint256 priceCents;     // price * 100
        uint256 quantity;
        uint256 buyOrderId;
        uint256 sellOrderId;
        uint256 timestamp;
    }

    Trade[] private trades;
    mapping(uint256 => uint256) private tradeIdToIndexPlus1; // 0 = not exists

    event TradeRecorded(
        uint256 tradeId,
        string symbol,
        uint256 priceCents,
        uint256 quantity,
        uint256 buyOrderId,
        uint256 sellOrderId,
        uint256 timestamp
    );

    function recordTrade(
        uint256 tradeId,
        string calldata symbol,
        uint256 priceCents,
        uint256 quantity,
        uint256 buyOrderId,
        uint256 sellOrderId
    ) external {
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

        tradeIdToIndexPlus1[tradeId] = trades.length; // index+1

        emit TradeRecorded(tradeId, symbol, priceCents, quantity, buyOrderId, sellOrderId, block.timestamp);
    }

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
