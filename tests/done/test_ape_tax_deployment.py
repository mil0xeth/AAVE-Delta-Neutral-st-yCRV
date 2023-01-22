import pytest

from brownie import reverts, chain, Contract, Wei, ZERO_ADDRESS
from eth_abi import encode_single


def test_ape_tax(
    token,
    dai,
    yvault,
    cloner,
    strategy,
    strategist,
    token_whale,
    dai_whale,
    gov,
    apetax_vault,
    amount,
    import_swap_router_selection_dict,
    chainlink,
    collateralToken
):
    vault = apetax_vault
    daddy = gov
    gov = vault.governance()
    vault.setDepositLimit(2**256-1, {"from": gov})

    clone_tx = cloner.cloneMarketLib(
        vault,
        strategist,
        strategist,
        strategist,
        collateralToken,
        yvault,
        f"StrategyMaker{token.symbol()}",
        chainlink,
        {"from": strategist},
    )

    cloned_strategy = Contract.from_abi(
        "Strategy", clone_tx.events["Cloned"]["clone"], strategy.abi
    )
    swap_router_selection_dict = import_swap_router_selection_dict
    cloned_strategy.setSwapRouterSelection(swap_router_selection_dict[token.symbol()]['swapRouterSelection'], swap_router_selection_dict[token.symbol()]['feeBorrowTokenToMidUNIV3'], swap_router_selection_dict[token.symbol()]['feeMidToWantUNIV3'], swap_router_selection_dict[token.symbol()]['midTokenChoice'],  {"from": gov})
    # Reduce other strategies debt allocation
    for i in range(0, 20):
        strat_address = vault.withdrawalQueue(i)
        if strat_address == ZERO_ADDRESS:
            break

        vault.updateStrategyDebtRatio(strat_address, 0, {"from": gov})

    vault.addStrategy(cloned_strategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov})

    token.approve(vault, 2 ** 256 - 1, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})

    cloned_strategy.harvest({"from": gov})
    assert yvault.balanceOf(cloned_strategy) > 0

    print(f"After first harvest")
    print(
        f"strat estimatedTotalAssets: {cloned_strategy.estimatedTotalAssets()/1e18:_}"
    )
    print(f"strat balanceOf yvDAI: {yvault.balanceOf(cloned_strategy)/1e18:_}")
    print(
        f"strat balanceOf DAI: {(yvault.balanceOf(cloned_strategy)/1e18 * yvault.pricePerShare()/1e18):_}"
    )

    # Sleep for 2 days
    chain.sleep(60 * 60 * 24 * 2)
    chain.mine(1)

    # Send some profit to yvDAI
    dai.transfer(yvault, yvault.totalDebt() * 0.01, {"from": dai_whale})
    tx = cloned_strategy.harvest({"from": gov})

    print(f"After second harvest")
    print(
        f"strat estimatedTotalAssets: {cloned_strategy.estimatedTotalAssets()/1e18:_}"
    )
    print(f"strat balanceOf yvDAI: {yvault.balanceOf(cloned_strategy)/1e18:_}")
    print(
        f"strat balanceOf DAI: {(yvault.balanceOf(cloned_strategy)/1e18 * yvault.pricePerShare()/1e18):_}"
    )

    assert vault.strategies(cloned_strategy).dict()["totalGain"] > 0
    assert vault.strategies(cloned_strategy).dict()["totalLoss"] == 0
    chain.sleep(60 * 60 * 8)
    chain.mine(1)

    vault.updateStrategyDebtRatio(cloned_strategy, 0, {"from": gov})
    cloned_strategy.harvest({"from": gov})

    print(f"After third harvest")
    print(
        f"strat estimatedTotalAssets: {cloned_strategy.estimatedTotalAssets()/1e18:_}"
    )
    print(f"strat balanceOf yvDAI: {yvault.balanceOf(cloned_strategy)/1e18:_}")
    print(
        f"strat balanceOf DAI: {(yvault.balanceOf(cloned_strategy)/1e18 * yvault.pricePerShare()/1e18):_}"
    )
    print(f"totalLoss: {vault.strategies(cloned_strategy).dict()['totalLoss']/1e18:_}")

    assert vault.strategies(cloned_strategy).dict()["totalLoss"] < Wei("0.5 ether")
    assert vault.strategies(cloned_strategy).dict()["totalDebt"] == 0
