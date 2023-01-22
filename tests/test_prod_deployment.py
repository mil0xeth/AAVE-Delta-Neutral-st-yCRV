import pytest

from brownie import reverts, chain, Contract, Wei, history, ZERO_ADDRESS
from eth_abi import encode_single


def test_prod_weth(
    weth, dai, strategist, weth_whale, dai_whale, MarketLibCloner, Strategy, token, import_swap_router_selection_dict, 
):
    if (token != weth):
        vault = Contract("0xa258C4606Ca8206D8aA700cE2143D7db854D168c")
        gov = vault.governance()
        yvault = Contract("0xdA816459F1AB5631232FE5e97a05BBBb94970c95")
        collateralToken = Contract("0x41c84c0e2EE0b740Cf0d31F63f3B6F627DC6b393")

        cloner = strategist.deploy(
            MarketLibCloner,
            vault,
            collateralToken,
            yvault,
            f"StrategyMakerV2_ETH-C",
            "0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419"
        )

        original_strategy_address = history[-1].events["Deployed"]["original"]
        strategy = Strategy.at(original_strategy_address)
        swap_router_selection_dict = import_swap_router_selection_dict
        strategy.setSwapRouterSelection(swap_router_selection_dict["WETH"]['swapRouterSelection'], swap_router_selection_dict["WETH"]['feeBorrowTokenToMidUNIV3'], swap_router_selection_dict["WETH"]['feeMidToWantUNIV3'], swap_router_selection_dict["WETH"]['midTokenChoice'], {"from": gov})
        strategy.setHealthCheck(ZERO_ADDRESS, {"from": gov})
        strategy.setDoHealthCheck(False, {"from": gov})
        assert strategy.strategist() == "0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7"
        assert strategy.keeper() == "0x736D7e3c5a6CB2CE3B764300140ABF476F6CFCCF"

        # Reduce other strategies debt allocation
        for i in range(0, 20):
            strat_address = vault.withdrawalQueue(i)
            if strat_address == ZERO_ADDRESS:
                break

            vault.updateStrategyDebtRatio(strat_address, 0, {"from": gov})

        vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov})

        weth.approve(vault, 2 ** 256 - 1, {"from": weth_whale})
        vault.deposit(250 * (10 ** weth.decimals()), {"from": weth_whale})

        strategy.harvest({"from": gov})
        assert yvault.balanceOf(strategy) > 0

        print(f"After first harvest")
        print(f"strat estimatedTotalAssets: {strategy.estimatedTotalAssets()/1e18:_}")
        print(f"strat balanceOf yvDAI: {yvault.balanceOf(strategy)/1e18:_}")
        print(
            f"strat balanceOf DAI: {(yvault.balanceOf(strategy)/1e18 * yvault.pricePerShare()/1e18):_}"
        )

        # Sleep for 2 days
        chain.sleep(60 * 60 * 24 * 2)
        chain.mine(1)

        # Send some profit to yvDAI
        dai.transfer(yvault, yvault.totalDebt() * 0.02, {"from": dai_whale})
        tx = strategy.harvest({"from": gov})

        print(f"After second harvest")
        print(f"strat estimatedTotalAssets: {strategy.estimatedTotalAssets()/1e18:_}")
        print(f"strat balanceOf yvDAI: {yvault.balanceOf(strategy)/1e18:_}")
        print(
            f"strat balanceOf DAI: {(yvault.balanceOf(strategy)/1e18 * yvault.pricePerShare()/1e18):_}"
        )

        assert vault.strategies(strategy).dict()["totalGain"] > 0
        assert vault.strategies(strategy).dict()["totalLoss"] == 0
        chain.sleep(60 * 60 * 8)
        chain.mine(1)

        vault.updateStrategyDebtRatio(strategy, 0, {"from": gov})
        strategy.harvest({"from": gov})

        print(f"After third harvest")
        print(f"strat estimatedTotalAssets: {strategy.estimatedTotalAssets()/1e18:_}")
        print(f"strat balanceOf yvDAI: {yvault.balanceOf(strategy)/1e18:_}")
        print(
            f"strat balanceOf DAI: {(yvault.balanceOf(strategy)/1e18 * yvault.pricePerShare()/1e18):_}"
        )
        print(f"totalLoss: {vault.strategies(strategy).dict()['totalLoss']/1e18:_}")

        assert vault.strategies(strategy).dict()["totalLoss"] < Wei("0.75 ether")
        assert vault.strategies(strategy).dict()["totalDebt"] == 0


def test_prod_universal(
    token, dai, strategist, token_whale, dai_whale, MarketLibCloner, Strategy, production_vault, yvDAI, chainlink, amount, import_swap_router_selection_dict, collateralToken,
):
    vault = production_vault
    gov = vault.governance()
    yvault = yvDAI
    
    cloner = strategist.deploy(
        MarketLibCloner,
        vault,
        collateralToken,
        yvault, 
        f"StrategyMakerV3{token.symbol()}",
        chainlink
    )

    original_strategy_address = history[-1].events["Deployed"]["original"]
    strategy = Strategy.at(original_strategy_address)
    strategy.setHealthCheck(ZERO_ADDRESS, {"from": gov})
    strategy.setDoHealthCheck(False, {"from": gov})
    swap_router_selection_dict = import_swap_router_selection_dict
    strategy.setSwapRouterSelection(swap_router_selection_dict[token.symbol()]['swapRouterSelection'], swap_router_selection_dict[token.symbol()]['feeBorrowTokenToMidUNIV3'], swap_router_selection_dict[token.symbol()]['feeMidToWantUNIV3'], swap_router_selection_dict[token.symbol()]['midTokenChoice'], {"from": gov})
    assert strategy.strategist() == "0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7"
    assert strategy.keeper() == "0x736D7e3c5a6CB2CE3B764300140ABF476F6CFCCF"

    # Reduce other strategies debt allocation
    for i in range(0, 20):
        strat_address = vault.withdrawalQueue(i)
        if strat_address == ZERO_ADDRESS:
            break

        vault.updateStrategyDebtRatio(strat_address, 0, {"from": gov})

    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov})

    token.approve(vault, 2 ** 256 - 1, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})

    strategy.harvest({"from": gov})
    assert yvault.balanceOf(strategy) > 0

    print(f"After first harvest")
    print(f"strat estimatedTotalAssets: {strategy.estimatedTotalAssets()/1e18:_}")
    print(f"strat balanceOf yvDAI: {yvault.balanceOf(strategy)/1e18:_}")
    print(
        f"strat balanceOf DAI: {(yvault.balanceOf(strategy)/1e18 * yvault.pricePerShare()/1e18):_}"
    )

    # Sleep for 2 days
    chain.sleep(60 * 60 * 24 * 2)
    chain.mine(1)

    # Send some profit to yvDAI
    dai.transfer(yvault, yvault.totalDebt() * 0.02, {"from": dai_whale})
    tx = strategy.harvest({"from": gov})

    print(f"After second harvest")
    print(f"strat estimatedTotalAssets: {strategy.estimatedTotalAssets()/1e18:_}")
    print(f"strat balanceOf yvDAI: {yvault.balanceOf(strategy)/1e18:_}")
    print(
        f"strat balanceOf DAI: {(yvault.balanceOf(strategy)/1e18 * yvault.pricePerShare()/1e18):_}"
    )

    assert vault.strategies(strategy).dict()["totalGain"] > 0
    assert vault.strategies(strategy).dict()["totalLoss"] == 0
    chain.sleep(60 * 60 * 8)
    chain.mine(1)

    vault.updateStrategyDebtRatio(strategy, 0, {"from": gov})
    strategy.harvest({"from": gov})

    print(f"After third harvest")
    print(f"strat estimatedTotalAssets: {strategy.estimatedTotalAssets()/1e18:_}")
    print(f"strat balanceOf yvDAI: {yvault.balanceOf(strategy)/1e18:_}")
    print(
        f"strat balanceOf DAI: {(yvault.balanceOf(strategy)/1e18 * yvault.pricePerShare()/1e18):_}"
    )
    print(f"totalLoss: {vault.strategies(strategy).dict()['totalLoss']/1e18:_}")

    assert vault.strategies(strategy).dict()["totalLoss"] < Wei("0.75 ether")
    assert vault.strategies(strategy).dict()["totalDebt"] == 0
