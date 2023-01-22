// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "./Strategy.sol";
import "../interfaces/yearn/IOSMedianizer.sol";

// The purpose of this wrapper contract is to expose internal functions
// that may contain application logic and therefore need to be unit tested.
contract TestStrategy is Strategy {
    constructor(
        address _vault,
        address _collateralToken,
        address _yVault,
        string memory _strategyName,
        address _chainlinkWantToUSDPriceFeed
    )
        public
        Strategy(
            _vault,
            _collateralToken,
            _yVault,
            _strategyName,
            _chainlinkWantToUSDPriceFeed
        )
    {}

    function _liquidatePosition(uint256 _amountNeeded)
        public
        returns (uint256 _liquidatedAmount, uint256 _loss)
    {
        (_liquidatedAmount, _loss) = liquidatePosition(_amountNeeded);
    }

    function _getPrice() public view returns (uint256) {
        return _getCollateralPrice();
    }

    function freeCollateral(uint256 collateralAmount) public {
        return _freeCollateralAndRepayDebt(collateralAmount, 0);
    }
}
