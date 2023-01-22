// SPDX-License-Identifier: agpl-3.0
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "@openzeppelin/contracts/math/SafeMath.sol";
import "@openzeppelin/contracts/math/Math.sol";
import {SafeERC20,IERC20,Address} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

import "../../interfaces/maker/IMaker.sol";

import "../../interfaces/IERC20Metadata.sol";

//UniswapV3
import "../../interfaces/swap/ISwapRouter.sol";
//UniswapV2
import "../../interfaces/swap/ISwap.sol";

library MarketLib {
    using SafeMath for uint256;
    using SafeERC20 for IERC20;
    
    // Uniswap V3 router:
    address internal constant univ3router = 0xE592427A0AEce92De3Edee1F18E0157C05861564;
    //Uniswap V2 router:
    address internal constant univ2router = 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D;
    // SushiSwap router
    address internal constant sushiswapRouter = 0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F;

    // Wrapped Ether - Used for swaps routing
    address internal constant WETH = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2;

    // USDC - Used for swaps routing
    address internal constant USDC = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48;

    // Units used in Maker contracts
    uint256 internal constant WAD = 10**18;
    uint256 internal constant RAY = 10**27;

    // Do not attempt to mint DAI if there are less than MIN_MINTABLE available
    uint256 internal constant MIN_MINTABLE = 500000 * WAD;

    // Maker vaults manager
    ManagerLike internal constant manager =
        ManagerLike(0x5ef30b9986345249bc32d8928B7ee64DE9435E39);

    // Token Adapter Module for collateral
    DaiJoinLike internal constant daiJoin =
        DaiJoinLike(0x9759A6Ac90977b93B58547b4A71c78317f391A28);

    // Liaison between oracles and core Maker contracts
    SpotLike internal constant spotter =
        SpotLike(0x65C79fcB50Ca1594B025960e539eD7A9a6D434A3);

    // Part of the Maker Rates Module in charge of accumulating stability fees
    JugLike internal constant jug =
        JugLike(0x19c0976f590D67707E62397C87829d896Dc0f1F1);

    // Debt Ceiling Instant Access Module
    DssAutoLine internal constant autoLine =
        DssAutoLine(0xC7Bdd1F2B16447dcf3dE045C4a039A60EC2f0ba3);

    // ----------------- PUBLIC FUNCTIONS -----------------

    // Creates an UrnHandler (cdp) for a specific ilk and allows to manage it via the internal
    // registry of the manager.
    function openCdp(bytes32 ilk) public returns (uint256) {
        return manager.open(ilk, address(this));
    }

    // Moves cdpId collateral balance and debt to newCdpId.
    function shiftCdp(uint256 cdpId, uint256 newCdpId) public {
        manager.shift(cdpId, newCdpId);
    }

    // Transfers the ownership of cdp to recipient address in the manager registry.
    function transferCdp(uint256 cdpId, address recipient) public {
        manager.give(cdpId, recipient);
    }

    // Allow/revoke manager access to a cdp
    function allowManagingCdp(
        uint256 cdpId,
        address user,
        bool isAccessGranted
    ) public {
        manager.cdpAllow(cdpId, user, isAccessGranted ? 1 : 0);
    }

    // Deposits collateral (gem) and mints DAI
    // Adapted from https://github.com/makerdao/dss-proxy-actions/blob/master/src/DssProxyActions.sol#L639
    function lockGemAndDraw(
        address gemJoin,
        uint256 cdpId,
        uint256 collateralAmount,
        uint256 borrowTokenToMint,
        uint256 totalDebt
    ) public {
        address urn = manager.urns(cdpId);
        VatLike vat = VatLike(manager.vat());
        bytes32 ilk = manager.ilks(cdpId);

        if (borrowTokenToMint > 0) {
            borrowTokenToMint = _forceMintWithinLimits(vat, ilk, borrowTokenToMint, totalDebt);
        }

        // Takes token amount from the strategy and joins into the vat
        if (collateralAmount > 0) {
            GemJoinLike(gemJoin).join(urn, collateralAmount);
        }

        // Locks token amount into the CDP and generates debt
        manager.frob(
            cdpId,
            int256(convertTo18(gemJoin, collateralAmount)),
            _getDrawDart(vat, urn, ilk, borrowTokenToMint)
        );

        // Moves the DAI amount to the strategy. Need to convert dai from [wad] to [rad]
        manager.move(cdpId, address(this), borrowTokenToMint.mul(1e27));

        // Allow access to DAI balance in the vat
        vat.hope(address(daiJoin));

        // Exits DAI to the user's wallet as a token
        daiJoin.exit(address(this), borrowTokenToMint);
    }

    // Returns DAI to decrease debt and attempts to unlock any amount of collateral
    // Adapted from https://github.com/makerdao/dss-proxy-actions/blob/master/src/DssProxyActions.sol#L758
    function wipeAndFreeGem(
        address gemJoin,
        uint256 cdpId,
        uint256 collateralAmount,
        uint256 daiToRepay
    ) public {
        address urn = manager.urns(cdpId);

        // Joins DAI amount into the vat
        if (daiToRepay > 0) {
            daiJoin.join(urn, daiToRepay);
        }

        uint256 wadC = collateralAmount;

        // Paybacks debt to the CDP and unlocks token amount from it
        manager.frob(
            cdpId,
            -int256(wadC),
            _getWipeDart(
                VatLike(manager.vat()),
                VatLike(manager.vat()).dai(urn),
                urn,
                manager.ilks(cdpId)
            )
        );

        // Moves the amount from the CDP urn to proxy's address
        manager.flux(cdpId, address(this), collateralAmount);

        // Exits token amount to the strategy as a token
        GemJoinLike(gemJoin).exit(address(this), convertToWantDecimals(gemJoin, collateralAmount));
    }

    function debtFloor(bytes32 ilk) public view returns (uint256) {
        // uint256 Art;   // Total Normalised Debt     [wad]
        // uint256 rate;  // Accumulated Rates         [ray]
        // uint256 spot;  // Price with Safety Margin  [ray]
        // uint256 line;  // Debt Ceiling              [rad]
        // uint256 dust;  // Urn Debt Floor            [rad]
        (, , , , uint256 dust) = VatLike(manager.vat()).ilks(ilk);
        return dust.div(RAY);
    }

    function debtForCdp(uint256 cdpId, bytes32 ilk)
        public
        view
        returns (uint256)
    {
        address urn = manager.urns(cdpId);
        VatLike vat = VatLike(manager.vat());

        // Normalized outstanding stablecoin debt [wad]
        (, uint256 art) = vat.urns(ilk, urn);

        // Gets actual rate from the vat [ray]
        (, uint256 rate, , , ) = vat.ilks(ilk);

        // Return the present value of the debt with accrued fees
        return art.mul(rate).div(RAY);
    }

    function balanceOfCdp(uint256 cdpId, bytes32 ilk)
        public
        view
        returns (uint256)
    {
        address urn = manager.urns(cdpId);
        VatLike vat = VatLike(manager.vat());

        (uint256 ink, ) = vat.urns(ilk, urn);
        return ink;
    }

    // Returns value of DAI in the reference asset (e.g. $1 per DAI)
    function getDaiPar() public view returns (uint256) {
        // Value is returned in ray (10**27)
        return spotter.par();
    }

    // Liquidation ratio for the given ilk returned in [ray]
    // https://github.com/makerdao/dss/blob/master/src/spot.sol#L45
    function getLiquidationRatio(bytes32 ilk) public view returns (uint256) {
        (, uint256 liquidationRatio) = spotter.ilks(ilk);
        return liquidationRatio;
    }

    function getSpotPrice(bytes32 ilk) public view returns (uint256) {
        VatLike vat = VatLike(manager.vat());

        // spot: collateral price with safety margin returned in [ray]
        (, , uint256 spot, , ) = vat.ilks(ilk);

        uint256 liquidationRatio = getLiquidationRatio(ilk);

        // convert ray*ray to wad
        return spot.mul(liquidationRatio).div(RAY * 1e9);
    }

    function getPessimisticRatioOfCdpWithExternalPrice(
        uint256 cdpId,
        bytes32 ilk,
        uint256 externalPrice,
        uint256 collateralizationRatioPrecision
    ) public view returns (uint256) {
        // Use pessimistic price to determine the worst ratio possible
        uint256 price = Math.min(getSpotPrice(ilk), externalPrice);
        require(price > 0); // dev: invalid price

        uint256 totalCollateralValue =
            balanceOfCdp(cdpId, ilk).mul(price).div(WAD);
        uint256 totalDebt = debtForCdp(cdpId, ilk);

        // If for some reason we do not have debt (e.g: deposits under dust)
        // make sure the operation does not revert
        if (totalDebt == 0) {
            totalDebt = 1;
        }

        return
            totalCollateralValue.mul(collateralizationRatioPrecision).div(
                totalDebt
            );
    }

    // Make sure we update some key content in Maker contracts
    // These can be updated by anyone without authenticating
    function keepBasicMakerHygiene(bytes32 ilk) public {
        // Update accumulated stability fees
        jug.drip(ilk);

        // Update the debt ceiling using DSS Auto Line
        autoLine.exec(ilk);
    }

    function daiJoinAddress() public view returns (address) {
        return address(daiJoin);
    }

    // Checks if there is at least MIN_MINTABLE dai available to be minted
    function isDaiAvailableToMint(bytes32 ilk) public view returns (bool) {
        return balanceOfDaiAvailableToMint(ilk) >= MIN_MINTABLE;
    }

    // Checks amount of Dai mintable
    function balanceOfDaiAvailableToMint(bytes32 ilk) public view returns (uint256) {
        VatLike vat = VatLike(manager.vat());
        (uint256 Art, uint256 rate, , uint256 line, ) = vat.ilks(ilk);

        // Total debt in [rad] (wad * ray)
        uint256 vatDebt = Art.mul(rate);

        if (vatDebt >= line) {
            return 0;
        }

        return line.sub(vatDebt).div(RAY);
    }

    // ----------------- INTERNAL FUNCTIONS -----------------

    // This function repeats some code from daiAvailableToMint because it needs
    // to handle special cases such as not leaving debt under dust
    function _forceMintWithinLimits(
        VatLike vat,
        bytes32 ilk,
        uint256 desiredAmount,
        uint256 debtBalance
    ) internal view returns (uint256) {
        // uint256 Art;   // Total Normalised Debt     [wad]
        // uint256 rate;  // Accumulated Rates         [ray]
        // uint256 spot;  // Price with Safety Margin  [ray]
        // uint256 line;  // Debt Ceiling              [rad]
        // uint256 dust;  // Urn Debt Floor            [rad]
        (uint256 Art, uint256 rate, , uint256 line, uint256 dust) =
            vat.ilks(ilk);

        // Total debt in [rad] (wad * ray)
        uint256 vatDebt = Art.mul(rate);

        // Make sure we are not over debt ceiling (line) or under debt floor (dust)
        if (
            vatDebt >= line || (desiredAmount.add(debtBalance) <= dust.div(RAY))
        ) {
            return 0;
        }

        uint256 maxMintableDAI = line.sub(vatDebt).div(RAY);

        // Avoid edge cases with low amounts of available debt
        if (maxMintableDAI < MIN_MINTABLE) {
            return 0;
        }

        // Prevent rounding errors
        if (maxMintableDAI > WAD) {
            maxMintableDAI = maxMintableDAI - WAD;
        }

        return Math.min(maxMintableDAI, desiredAmount);
    }

    // Adapted from https://github.com/makerdao/dss-proxy-actions/blob/master/src/DssProxyActions.sol#L161
    function _getDrawDart(
        VatLike vat,
        address urn,
        bytes32 ilk,
        uint256 wad
    ) internal returns (int256 dart) {
        // Updates stability fee rate
        uint256 rate = jug.drip(ilk);

        // Gets DAI balance of the urn in the vat
        uint256 dai = vat.dai(urn);

        // If there was already enough DAI in the vat balance, just exits it without adding more debt
        if (dai < wad.mul(RAY)) {
            // Calculates the needed dart so together with the existing dai in the vat is enough to exit wad amount of DAI tokens
            dart = int256(wad.mul(RAY).sub(dai).div(rate));
            // This is neeeded due to lack of precision. It might need to sum an extra dart wei (for the given DAI wad amount)
            dart = uint256(dart).mul(rate) < wad.mul(RAY) ? dart + 1 : dart;
        }
    }

    // Adapted from https://github.com/makerdao/dss-proxy-actions/blob/master/src/DssProxyActions.sol#L183
    function _getWipeDart(
        VatLike vat,
        uint256 dai,
        address urn,
        bytes32 ilk
    ) internal view returns (int256 dart) {
        // Gets actual rate from the vat
        (, uint256 rate, , , ) = vat.ilks(ilk);
        // Gets actual art value of the urn
        (, uint256 art) = vat.urns(ilk, urn);

        // Uses the whole dai balance in the vat to reduce the debt
        dart = int256(dai / rate);

        // Checks the calculated dart is not higher than urn.art (total debt), otherwise uses its value
        dart = uint256(dart) <= art ? -dart : -int256(art);
    }

    function convertTo18(address gemJoin, uint256 amt)
        internal
        returns (uint256 wad)
    {
        // For those collaterals that have less than 18 decimals precision we need to do the conversion before
        // passing to frob function
        // Adapters will automatically handle the difference of precision
        wad = amt.mul(10**(18 - GemJoinLike(gemJoin).dec()));
    }

    function convertToWantDecimals(address gemJoin, uint256 amt)
        internal
        returns (uint256 wad)
    {
        wad = amt.div(10**(18 - GemJoinLike(gemJoin).dec()));
    }
    
    function _checkAllowance(
        address _contract,
        address _token,
        uint256 _amount
    ) internal {
        if (IERC20(_token).allowance(address(this), _contract) < _amount) {
            IERC20(_token).safeApprove(_contract, 0);
            IERC20(_token).safeApprove(_contract, type(uint256).max);
        }
    }

    function _getTokenOutPath(address _token_in, address _token_out, uint24 _midTokenChoice)
        internal
        pure
        returns (address[] memory _path)
    {
        // 0 = through WETH, 1 = through USDC, 2 = direct
        if (_midTokenChoice == 1){ //_token_in --> USDC --> _token_out, check first in case we want to swap DAI --> USDC --> WETH or WETH --> USDC --> DAI
            _path = new address[](3);
            _path[1] = USDC;
            _path[2] = _token_out;
        } 
        else if (_token_in == WETH || _token_out == WETH) { // _token_in --> WETH or WETH --> _token_out
            _path = new address[](2);
            _path[1] = _token_out;
            }
        else if (_midTokenChoice == 2){ //_token_in --> _token_out (ignoring WETH as intermediate)
            _path = new address[](2);
            _path[1] = _token_out;
        }
        else { //_token_in --> WETH --> _token_out for 0 or 
            _path = new address[](3);
            _path[1] = WETH;
            _path[2] = _token_out;
        }
        _path[0] = _token_in;        
    }

    //borrowToken --> want
    function swapKnownInBorrowTokenToWant(uint24 _swapRouterSelection, uint256 _amountIn, address _borrowToken, address _want, uint24 _feeBorrowTokenToMidUNIV3, uint24 _feeMidToWantUNIV3, uint24 _midTokenChoice, uint256 _slippagePrice) external {
        uint256 wantDecimals = uint256(IERC20Metadata(_want).decimals());
        uint256 minAmountOut; //initialization sets it to 0, so if swapslippage defined, minAmountOut = 0
        if (_slippagePrice != 0 && _amountIn >= 1e18){
            minAmountOut = _amountIn.mul(10**wantDecimals).div(_slippagePrice);
        }
        address router;
        // 0 = sushi, 1 = univ2, 2 = univ3, 3+ = yswaps
        if (_swapRouterSelection ==  0){ //sushi
            router = sushiswapRouter;
        }
        else if (_swapRouterSelection == 1){ //univ2
            router = univ2router;
        }
        if (_swapRouterSelection ==  0 || _swapRouterSelection == 1){ //univ2 & sushi execution
        _checkAllowance(router, _borrowToken, _amountIn);
        ISwap(router).swapExactTokensForTokens(_amountIn, minAmountOut, _getTokenOutPath(_borrowToken, _want, _midTokenChoice), address(this), now);
        return;
        }
        ///////////////////////// UNISWAPV3:
        if (_swapRouterSelection == 2){ //univ3
            address midToken;
            if (_midTokenChoice == 0){midToken = WETH;}
            else if (_midTokenChoice == 1){midToken = USDC;}
            else if (_midTokenChoice == 2){midToken = _want;}
            _UNIV3swapKnownIn(_amountIn, _borrowToken, midToken, _want, _feeBorrowTokenToMidUNIV3, _feeMidToWantUNIV3, minAmountOut);
            return;
        }
    }

    //want --> borrowToken
    function swapKnownOutWantToBorrowToken(uint24 _swapRouterSelection, uint256 _amountOut, address _want, address _borrowToken, uint24 _feeBorrowTokenToMidUNIV3, uint24 _feeMidToWantUNIV3, uint24 _midTokenChoice, uint256 _slippagePrice) external {
        uint256 wantDecimals = uint256(IERC20Metadata(_want).decimals());
        uint256 maxAmountIn = type(uint256).max;
        if (_slippagePrice != 0 && _amountOut >= 1e18){
            maxAmountIn = _amountOut.mul(10**wantDecimals).div(_slippagePrice);
        }
        address router;
        // 0 = sushi, 1 = univ2, 2 = univ3, 3+ = yswaps
        if (_swapRouterSelection ==  0){ //sushi
            router = sushiswapRouter;
        }
        else if ( _swapRouterSelection == 1){ //univ2
            router = univ2router;
        }
        if (_swapRouterSelection ==  0 || _swapRouterSelection == 1){ //univ2 & sushi execution
        _checkAllowance(router, _want, _amountOut);
        ISwap(router).swapTokensForExactTokens(_amountOut, maxAmountIn, _getTokenOutPath(_want, _borrowToken, _midTokenChoice), address(this), now);
        return;
        }
        ///////////////////////// UNISWAPV3:
        if (_swapRouterSelection == 2){ //univ3
            address midToken;
            if (_midTokenChoice == 0){midToken = WETH;}
            else if (_midTokenChoice == 1){midToken = USDC;}
            else if (_midTokenChoice == 2){midToken = _want;}
            _UNIV3swapKnownOut(_amountOut, _want, midToken, _borrowToken, _feeMidToWantUNIV3, _feeBorrowTokenToMidUNIV3, maxAmountIn);
            return;
        }
    }

    ////// UNISWAP V3:
    function _UNIV3swapKnownIn(uint256 _amountIn, address _tokenIn, address _tokenMid, address _tokenOut, uint24 _feeTokenToMid, uint24 _feeMidToOut, uint256 _amountOutMinimum) internal returns (uint256) {
        if (_tokenIn == _tokenOut || _amountIn == 0) {
            return _amountIn;
        }
        _checkAllowance(univ3router, _tokenIn, _amountIn);
        if ( _tokenIn == _tokenMid || _tokenMid == _tokenOut ) {
            require (_feeTokenToMid == _feeMidToOut, "direct swap, but feeBorrowTokenToMid != feeMidToWant");
            ISwapRouter.ExactInputSingleParams memory params =
            ISwapRouter.ExactInputSingleParams({
                tokenIn: _tokenIn,
                tokenOut: _tokenOut,
                fee: _feeTokenToMid,
                recipient: address(this),
                deadline: block.timestamp,
                amountIn: _amountIn,
                amountOutMinimum: _amountOutMinimum,
                sqrtPriceLimitX96: 0
            });
            return ISwapRouter(univ3router).exactInputSingle(params);
        }
        ISwapRouter.ExactInputParams memory params =
            ISwapRouter.ExactInputParams({
                path: abi.encodePacked(_tokenIn, _feeTokenToMid, _tokenMid, _feeMidToOut, _tokenOut),
                recipient: address(this),
                deadline: block.timestamp,
                amountIn: _amountIn,
                amountOutMinimum: _amountOutMinimum
            });
        return ISwapRouter(univ3router).exactInput(params);
    }

    function _UNIV3swapKnownOut(uint256 _amountOut, address _tokenIn, address _tokenMid, address _tokenOut, uint24 _feeTokenToMid, uint24 _feeMidToOut, uint256 _amountInMaximum) internal returns (uint256) {
        if (_tokenIn == _tokenOut || _amountOut == 0) {
            return _amountOut;
        }
        _checkAllowance(univ3router, _tokenIn, _amountInMaximum);
        if ( _tokenIn == _tokenMid || _tokenMid == _tokenOut ) {
            require (_feeTokenToMid == _feeMidToOut, "direct swap, but feeBorrowTokenToMid != feeMidToWant");
            ISwapRouter.ExactOutputSingleParams memory params =
                ISwapRouter.ExactOutputSingleParams({
                    tokenIn: _tokenIn,
                    tokenOut: _tokenOut,
                    fee: _feeTokenToMid,
                    recipient: address(this),
                    deadline: block.timestamp,
                    amountOut: _amountOut,
                    amountInMaximum: _amountInMaximum,
                    sqrtPriceLimitX96: 0
                });
            return ISwapRouter(univ3router).exactOutputSingle(params);
        }
        ISwapRouter.ExactOutputParams memory params =
            ISwapRouter.ExactOutputParams({
                //path: abi.encodePacked(_tokenIn, _feeTokenToMid, _tokenMid, _feeMidToOut, _tokenOut),
                path: abi.encodePacked(_tokenOut, _feeMidToOut, _tokenMid, _feeTokenToMid, _tokenIn),
                recipient: address(this),
                deadline: block.timestamp,
                amountOut: _amountOut,
                amountInMaximum: _amountInMaximum
            });
        return ISwapRouter(univ3router).exactOutput(params);
    }





}
