import pytest

from brownie import Wei


def test_liquidates_all_if_exact_same_want_balance(test_strategy, token, token_whale):
    amount = 100*(10 ** token.decimals())
    token.approve(test_strategy, amount, {"from": token_whale})
    token.transfer(test_strategy, amount, {"from": token_whale})

    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(amount).return_value
    assert _liquidatedAmount == amount
    assert _loss == 0


def test_liquidates_all_if_has_more_want_balance(test_strategy, token, token_whale):
    amount = 50*(10 ** token.decimals())
    token.approve(test_strategy, amount, {"from": token_whale})
    token.transfer(test_strategy, amount, {"from": token_whale})

    amountToLiquidate = amount * 0.5
    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(
        amountToLiquidate
    ).return_value
    assert _liquidatedAmount == amountToLiquidate
    assert _loss == 0


def test_liquidate_more_than_we_have_should_report_loss(
    test_strategy, token, token_whale
):
    amount = 50*(10 ** token.decimals())
    token.approve(test_strategy, amount, {"from": token_whale})
    token.transfer(test_strategy, amount, {"from": token_whale})

    amountToLiquidate = amount * 1.5
    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(
        amountToLiquidate
    ).return_value
    assert _liquidatedAmount == amount
    assert _loss == (amountToLiquidate - amount)


# In this test we attempt to liquidate the whole position a week after the deposit.
# We do not simulate any gains in the yVault, so there will not be enough money
# to unlock the whole collateral without a loss.
def test_liquidate_position_without_enough_profit_by_selling_want(
    chain, token, vault, test_strategy, user, amount, yvault, token_whale, gov
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # sleep 7 days
    chain.sleep(24 * 60 * 60 * 7)
    chain.mine(1)

    # Simulate a loss in yvault by sending some shares away
    yvault.transfer(
        token_whale, yvault.balanceOf(test_strategy) * 0.1, {"from": test_strategy}
    )

    # Harvest so all the collateral is locked in the CDP
    test_strategy.harvest({"from": gov})

    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(amount).return_value
    assert _liquidatedAmount + _loss == amount
    assert _loss > 0
    assert token.balanceOf(test_strategy) < amount




# In this test the strategy has enough profit to close the whole position
def test_happy_liquidation(
    chain, token, vault, test_strategy, yvDAI, dai, dai_whale, user, amount, gov
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # Harvest so all the collateral is locked in the CDP
    chain.sleep(1)
    test_strategy.harvest({"from": gov})

    # sleep 7 days
    chain.sleep(24 * 60 * 60 * 7)
    chain.mine(1)

    dai.transfer(yvDAI, yvDAI.totalAssets() * 0.01, {"from": dai_whale})

    (_liquidatedAmount, _loss) = test_strategy._liquidatePosition(amount).return_value

    assert _loss == 0
    assert _liquidatedAmount == amount
    assert test_strategy.estimatedTotalAssets() > 0
