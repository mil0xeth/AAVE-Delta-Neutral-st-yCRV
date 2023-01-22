import pytest
from brownie import chain, reverts, Wei, ZERO_ADDRESS


def test_passing_zero_should_repay_all_debt(
    vault, strategy, token, token_whale, user, gov, dai, dai_whale, yvDAI, amount, RELATIVE_APPROX
):
    #amount = 1_000 * (10 ** token.decimals())
    strategy.setHealthCheck(ZERO_ADDRESS, {"from": gov})
    strategy.setDoHealthCheck(False, {"from": gov})
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})

    # Send funds through the strategy
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert strategy.balanceOfDebt() > 0

    # Send some profit to yVault
    dai.transfer(yvDAI, yvDAI.totalAssets() * 0.01, {"from": dai_whale})

    # Harvest 2: Realize profit
    strategy.harvest({"from": gov})
    chain.sleep(3600 * 6)  # 6 hrs needed for profits to unlock
    chain.mine(1)

    prev_collat = strategy.balanceOfCollateral()
    strategy.emergencyDebtRepayment(0, {"from": vault.management()})

    # All debt is repaid and collateral is left untouched
    assert strategy.getCurrentCollRatio() > strategy.collateralizationRatio()
    assert pytest.approx(strategy.balanceOfCollateral(), rel=RELATIVE_APPROX) == prev_collat


def test_passing_value_over_collat_ratio_does_nothing(
    vault, strategy, token, amount, user, gov
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # Send funds through the strategy
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert strategy.balanceOfDebt() > 0

    prev_debt = strategy.balanceOfDebt()
    prev_collat = strategy.balanceOfCollateral()
    c_ratio = strategy.collateralizationRatio()
    strategy.emergencyDebtRepayment(c_ratio + 1, {"from": vault.management()})

    # Debt and collat remain the same
    assert strategy.balanceOfDebt() == prev_debt
    assert strategy.balanceOfCollateral() == prev_collat


def test_from_ratio_adjusts_debt(
    vault, strategy, token, amount, user, gov, RELATIVE_APPROX
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # Send funds through the strategy
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert strategy.balanceOfDebt() > 0

    prev_debt = strategy.balanceOfDebt()
    prev_collat = strategy.balanceOfCollateral()
    c_ratio = strategy.collateralizationRatio()
    strategy.emergencyDebtRepayment(c_ratio * 0.7, {"from": vault.management()})

    # Debt is partially repaid and collateral is left untouched
    assert (
        pytest.approx(strategy.balanceOfDebt(), rel=RELATIVE_APPROX) == prev_debt * 0.7
    )
    assert pytest.approx(strategy.balanceOfCollateral(), rel=RELATIVE_APPROX) == prev_collat
