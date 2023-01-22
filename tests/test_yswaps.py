from brownie import Contract, Wei
import brownie
from eth_abi import encode_single, encode_abi
from brownie.convert import to_bytes
from eth_abi.packed import encode_abi_packed
import pytest
import eth_utils


def test_profitable_harvest(
    chain,
    accounts,
    token,
    vault,
    strategy,
    strategist,
    amount,
    RELATIVE_APPROX,
    yvault,
    yvault_whale,
    router,
    multicall_swapper,
    weth,
    ymechs_safe,
    trade_factory,
    gov,
    dai,
    token_whale,
    import_swap_router_selection_dict
):
    strategy.setDoHealthCheck(False, {"from": gov})
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})
    assert token.balanceOf(vault.address) == amount

    #set ySwaps configuration:
    trade_factory.grantRole(trade_factory.STRATEGY(), strategy.address, {"from": ymechs_safe, "gas_price": "0 gwei"},)
    strategy.setTradeFactory(trade_factory.address, {"from": gov})
    swap_router_selection_dict = import_swap_router_selection_dict
    strategy.setSwapRouterSelection(3, swap_router_selection_dict[token.symbol()]['feeBorrowTokenToMidUNIV3'], swap_router_selection_dict[token.symbol()]['feeMidToWantUNIV3'], swap_router_selection_dict[token.symbol()]['midTokenChoice'], {"from": gov})

    # Harvest 1: Send funds through the strategy
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    # Send simualted profit and then swap simulated profit through ySwaps
    amount_in = 1_000e18
    yvault_token = yvault
    yvault_token.transfer(strategy, amount_in, {"from": yvault_whale})

    token_in = yvault_token
    token_out = token

    trade_factory.enable(yvault_token, token, {"from": strategy})

    print(f"Executing trade...")
    receiver = strategy.address
    asyncTradeExecutionDetails = [strategy, token_in, token_out, amount_in, 1]

    # always start with optimizations. 5 is CallOnlyNoValue
    optimizations = [["uint8"], [5]]
    a = optimizations[0]
    b = optimizations[1]

    # withdraw yvDAI from yvDAI vault to receive DAI:
    calldata = yvault.withdraw.encode_input(amount_in)
    t = createTx(yvault, calldata)
    a = a + t[0]
    b = b + t[1]

    # approve DAI to router
    calldata = dai.approve.encode_input(router, 2 ** 256 - 1)
    t = createTx(dai, calldata)
    a = a + t[0]
    b = b + t[1]

    # swap DAI to want through path depending on want
    if weth != token_out:
        path = [dai.address, weth.address, token_out.address]
    else:
        path = [dai.address, weth.address]

    calldata = router.swapExactTokensForTokens.encode_input(amount_in*0.8, 0, path, multicall_swapper.address, 2 ** 256 - 1)
    t = createTx(router, calldata)
    a = a + t[0]
    b = b + t[1]

    #estimate how much want we receive from swap
    if weth != token:
        expected_out = router.getAmountsOut(amount_in*0.8, path)[2]
    else:
        expected_out = router.getAmountsOut(amount_in*0.8, path)[1]

    # transfer want to strategy
    calldata = token_out.transfer.encode_input(receiver, expected_out*0.98)
    t = createTx(token_out, calldata)
    a = a + t[0]
    b = b + t[1]

    transaction = encode_abi_packed(a, b)

    # min out must be at least 1 to ensure that the tx works correctly
    # trade_factory.execute["uint256, address, uint, bytes"](
    #    multicall_swapper.address, 1, transaction, {"from": ymechs_safe}
    # )
    trade_factory.execute["tuple,address,bytes"](
        asyncTradeExecutionDetails,
        multicall_swapper.address,
        transaction,
        {"from": ymechs_safe},
    )
    print(token_out.balanceOf(strategy))

    tx = strategy.harvest({"from": strategist})
    print(tx.events)
    assert tx.events["Harvested"]["profit"] > 0

    before_pps = vault.pricePerShare()
    # Harvest 2: Realize profit
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    chain.sleep(3600 * 6)  # 6 hrs needed for profits to unlock
    chain.mine(1)
    profit = token.balanceOf(vault.address)  # Profits go to vault

    assert strategy.estimatedTotalAssets() + profit > amount
    assert vault.pricePerShare() > before_pps


def createTx(to, data):
    inBytes = eth_utils.to_bytes(hexstr=data)
    return [["address", "uint256", "bytes"], [to.address, len(inBytes), inBytes]]


def test_remove_trade_factory(strategy, gov, trade_factory, yvault, ymechs_safe):
    yvault_token = yvault
    trade_factory.grantRole(trade_factory.STRATEGY(), strategy.address, {"from": ymechs_safe, "gas_price": "0 gwei"},)
    strategy.setTradeFactory(trade_factory.address, {"from": gov})
    assert strategy.tradeFactory() == trade_factory.address
    assert yvault_token.allowance(strategy.address, trade_factory.address) > 0

    strategy.removeTradeFactoryPermissions({"from": gov})

    assert strategy.tradeFactory() != trade_factory.address
    assert yvault_token.allowance(strategy.address, trade_factory.address) == 0
