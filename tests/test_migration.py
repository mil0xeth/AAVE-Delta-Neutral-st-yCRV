# TODO: Add tests that show proper migration of the strategy to a newer one
#       Use another copy of the strategy to simulate the migration
#       Show that nothing is lost!

import pytest
from brownie import Contract, reverts


def test_migration(
    chain,
    token,
    vault,
    strategy,
    amount,
    Strategy,
    strategist,
    gov,
    user,
    RELATIVE_APPROX,
    collateralToken,
    yvault,
    chainlink
):
    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount
    new_strategy = strategist.deploy(Strategy, vault, collateralToken, yvault, "StrategyName", chainlink)
    # migration with more than dust reverts, there is no way to transfer the debt position
    with reverts():
        vault.migrateStrategy(strategy, new_strategy, {"from": gov})

    vault.revokeStrategy(strategy, {"from": gov})
    strategy.harvest({"from": gov})

    # migrate to a new strategy
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    vault.updateStrategyDebtRatio(new_strategy, 10_000, {"from": gov})
    new_strategy.harvest({"from": gov})
    assert (pytest.approx(new_strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount )
