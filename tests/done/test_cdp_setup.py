import pytest

from brownie.convert import to_string
from brownie.network.state import TxHistory
from brownie import chain, Wei

# Leaving this test as a sanity check.

def test_dai_should_be_minted_after_depositing_collateral(
    strategy, vault, yvDAI, token, token_whale, dai, gov, amount
):
    # Make sure there is no balance before the first deposit
    assert yvDAI.balanceOf(strategy) == 0

    token.approve(vault.address, amount, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})

    chain.sleep(1)
    strategy.harvest({"from": gov})

    # Minted DAI should be deposited in yvDAI
    assert dai.balanceOf(strategy) == 0
    assert yvDAI.balanceOf(strategy) > 0


def test_minted_dai_should_match_collateralization_ratio(
    test_strategy, vault, yvDAI, token, token_whale, gov, RELATIVE_APPROX, amount
):
    assert yvDAI.balanceOf(test_strategy) == 0

    token.approve(vault.address, amount, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})

    chain.sleep(1)
    test_strategy.harvest({"from": gov})

    token_price = test_strategy._getPrice()

    assert pytest.approx(
        yvDAI.balanceOf(test_strategy) * yvDAI.pricePerShare() / 1e18,
        rel=RELATIVE_APPROX,
    ) == (
        token_price * amount / test_strategy.collateralizationRatio() /(10 ** token.decimals())*1e18 # already in wad
    )


def DISABLED_WETH_test_ethToWant_should_convert_to_yfi(
    strategy, price_oracle_eth, RELATIVE_APPROX
):
    price = price_oracle_eth.latestAnswer()
    assert pytest.approx(
        strategy.ethToWant(Wei("1 ether")), rel=RELATIVE_APPROX
    ) == Wei("1 ether") / (price / 1e18)
    assert pytest.approx(
        strategy.ethToWant(Wei(price * 420)), rel=RELATIVE_APPROX
    ) == Wei("420 ether")
    assert pytest.approx(
        strategy.ethToWant(Wei(price * 0.5)), rel=RELATIVE_APPROX
    ) == Wei("0.5 ether")


# Needs to use test_strategy fixture to be able to read token_price
def test_delegated_assets_pricing(
    test_strategy, vault, yvDAI, token, token_whale, gov, RELATIVE_APPROX, amount
):

    token.approve(vault.address, amount, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})

    chain.sleep(1)
    test_strategy.harvest({"from": gov})

    dai_balance = yvDAI.balanceOf(test_strategy) * yvDAI.pricePerShare() / 1e18
    token_price = test_strategy._getPrice()

    assert pytest.approx(test_strategy.delegatedAssets(), rel=RELATIVE_APPROX) == ( dai_balance / token_price * (10 ** token.decimals()))
