import pytest
from brownie import chain, reverts, Contract


def test_set_collateralization_ratio_acl(
    strategy, gov, strategist, management, guardian, user
):
    strategy.setCollateralizationRatio(200 * 1e18, {"from": gov})
    assert strategy.collateralizationRatio() == 200 * 1e18

    strategy.setCollateralizationRatio(201 * 1e18, {"from": strategist})
    assert strategy.collateralizationRatio() == 201 * 1e18

    strategy.setCollateralizationRatio(202 * 1e18, {"from": management})
    assert strategy.collateralizationRatio() == 202 * 1e18

    with reverts("!authorized"):
        strategy.setCollateralizationRatio(203 * 1e18, {"from": guardian})

    with reverts("!authorized"):
        strategy.setCollateralizationRatio(200 * 1e18, {"from": user})


def test_set_rebalance_tolerance_acl(
    strategy, gov, strategist, management, guardian, user
):
    strategy.setRebalanceTolerance(5, {"from": gov})
    assert strategy.rebalanceTolerance() == 5

    strategy.setRebalanceTolerance(4, {"from": strategist})
    assert strategy.rebalanceTolerance() == 4

    strategy.setRebalanceTolerance(3, {"from": management})
    assert strategy.rebalanceTolerance() == 3

    with reverts("!authorized"):
        strategy.setRebalanceTolerance(2, {"from": guardian})

    with reverts("!authorized"):
        strategy.setRebalanceTolerance(5, {"from": user})


def test_set_max_loss_acl(strategy, gov, strategist, management, guardian, user):
    strategy.setMaxLossSwapSlippage(10, 500, {"from": gov})
    assert strategy.maxLoss() == 10

    strategy.setMaxLossSwapSlippage(11, 500, {"from": management})
    assert strategy.maxLoss() == 11

    with reverts("!authorized"):
        strategy.setMaxLossSwapSlippage(13, 500, {"from": guardian})

    with reverts("!authorized"):
        strategy.setMaxLossSwapSlippage(14, 500, {"from": user})


def test_set_swap_router_acl(strategy, gov, strategist, management, guardian, user):
    uniswap = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
    sushiswap = "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"

    with reverts("!authorized"):
        strategy.setSwapRouterSelection(0,0,0,0, {"from": user})

    with reverts("!authorized"):
        strategy.setSwapRouterSelection(0,0,0,0, {"from": guardian})

    strategy.setSwapRouterSelection(0,0,0,0, {"from": management})

    strategy.setSwapRouterSelection(0,0,0,0, {"from": management})

    strategy.setSwapRouterSelection(0,0,0,0, {"from": gov})

    strategy.setSwapRouterSelection(0,0,0,0, {"from": gov})




def test_migrate_dai_yvault_acl(
    strategy,
    gov,
    strategist,
    management,
    guardian,
    user,
    dai,
    new_dai_yvault,
    token,
    vault,
    amount,
):
    with reverts("!authorized"):
        strategy.migrateToNewDaiYVault(new_dai_yvault, {"from": strategist})

    with reverts("!authorized"):
        strategy.migrateToNewDaiYVault(new_dai_yvault, {"from": management})

    with reverts("!authorized"):
        strategy.migrateToNewDaiYVault(new_dai_yvault, {"from": guardian})

    with reverts("!authorized"):
        strategy.migrateToNewDaiYVault(new_dai_yvault, {"from": user})

    # Need to deposit so there is something in the yVault before migrating
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    strategy.migrateToNewDaiYVault(new_dai_yvault, {"from": gov})
    assert dai.allowance(strategy, new_dai_yvault) == 2 ** 256 - 1


def test_emergency_debt_repayment_acl(
    strategy, gov, strategist, management, guardian, user
):
    strategy.emergencyDebtRepayment(0, {"from": gov})
    assert strategy.balanceOfDebt() == 0

    strategy.emergencyDebtRepayment(0, {"from": management})
    assert strategy.balanceOfDebt() == 0

    with reverts("!authorized"):
        strategy.emergencyDebtRepayment(0, {"from": guardian})

    with reverts("!authorized"):
        strategy.emergencyDebtRepayment(0, {"from": user})


def test_repay_debt_acl(
    vault,
    strategy,
    token,
    amount,
    dai,
    dai_whale,
    gov,
    strategist,
    management,
    guardian,
    keeper,
    user,
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})

    # Send funds through the strategy
    chain.sleep(1)
    strategy.harvest({"from": gov})

    dai.transfer(strategy, 1000 * 1e18, {"from": dai_whale})
    debt_balance = strategy.balanceOfDebt()

    strategy.repayDebtWithDaiBalance(1, {"from": gov})
    assert pytest.approx(strategy.balanceOfDebt(), rel=RELATIVE_APPROX) == (debt_balance - 1)

    strategy.repayDebtWithDaiBalance(2, {"from": management})
    assert pytest.approx(strategy.balanceOfDebt(), rel=RELATIVE_APPROX) == (debt_balance - 3)

    with reverts("!authorized"):
        strategy.repayDebtWithDaiBalance(4, {"from": guardian})

    with reverts("!authorized"):
        strategy.repayDebtWithDaiBalance(5, {"from": keeper})

    with reverts("!authorized"):
        strategy.repayDebtWithDaiBalance(6, {"from": user})
