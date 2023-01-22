import pytest
from brownie import config, convert, interface, Contract, ZERO_ADDRESS


# TODO: uncomment those tokens you want to test as want
@pytest.fixture(
    params=[
        #"WETH",
        #"YFI",
        #"WBTC",
        #"YFI",
        "WETH",
        #"wstETH",
        #"LINK",

    ],
    scope="session",
    autouse=True,
)
def token(request):
    yield Contract(token_addresses[request.param])

useOSMforYFI = True

#strategy = Strategy.deploy(vault,"0xdA816459F1AB5631232FE5e97a05BBBb94970c95","Maker-v3-ETH-C","0x4554482d4300000000000000000000000000000000
#0000000000000000000000","0xF04a5cC80B1E94C69B48f5ee68a08CD2F09A7c3E","0xCF63089A8aD2a9D8BD6Bb8022f3190EB7e1eD0f1", {"from": gov})

#Allow switching between Sushi (0), Univ2 (1), Univ3 (2), yswaps (3) -- Mid is the intermediatry token to swap to in case the want token is not WETH
#midTokenChoice: 0 = through WETH, 1 = through USDC, 2 = direct
swap_router_selection_dict = {
    "YFI": {'swapRouterSelection': 0, 'feeBorrowTokenToMidUNIV3': 3000, 'feeMidToWantUNIV3': 3000, 'midTokenChoice': 0},
    "WETH": {'swapRouterSelection': 2, 'feeBorrowTokenToMidUNIV3': 500, 'feeMidToWantUNIV3': 500, 'midTokenChoice': 0}, #sushi: 0, 100, 500, 0   #univ3 through usdc: 2,100,500,1
    "LINK": {'swapRouterSelection': 2, 'feeBorrowTokenToMidUNIV3': 500, 'feeMidToWantUNIV3': 3000, 'midTokenChoice': 0},
    "wstETH": {'swapRouterSelection': 2, 'feeBorrowTokenToMidUNIV3': 500, 'feeMidToWantUNIV3': 500, 'midTokenChoice': 0}, #sushi: 0, 100, 500, 0
    #"WBTC": {'swapRouterSelection': 2, 'feeBorrowTokenToMidUNIV3': 100, 'feeMidToWantUNIV3': 500, 'midTokenChoice': 1},
    "WBTC": {'swapRouterSelection': 2, 'feeBorrowTokenToMidUNIV3': 500, 'feeMidToWantUNIV3': 500, 'midTokenChoice': 0},
}

token_addresses = {
    "YFI": "0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e", 
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "wstETH": "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0", 
    "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
    "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
}

token_prices = {
    "YFI": 5_400,
    "WETH": 1_650,
    "LINK": 6,
    "WBTC": 17_000,
    "wstETH": 1_357,
}

collateralToken_list = {
    "WETH": "0x41c84c0e2EE0b740Cf0d31F63f3B6F627DC6b393", #ETH-C
    "WBTC": "0x8Fc8BFD80d6A9F17Fb98A373023d72531792B431",
}

gemJoin_adapters = {
    "YFI": "0x3ff33d9162aD47660083D7DC4bC02Fb231c81677",
    "WETH": "0xF04a5cC80B1E94C69B48f5ee68a08CD2F09A7c3E", # ETH-C
    "wstETH": "0x10CD5fbe1b404B7E19Ef964B63939907bdaf42E2",
    "LINK": "0xdFccAf8fDbD2F4805C174f856a317765B49E4a50",
    "WBTC": "0x7f62f9592b823331E012D3c5DdF2A7714CfB9de2",
}

osm_proxies = {
    "YFI": ZERO_ADDRESS, #YFI case handled in YFIosmProxy fixture
    "WETH": "0xCF63089A8aD2a9D8BD6Bb8022f3190EB7e1eD0f1",
    "wstETH": ZERO_ADDRESS,
    "LINK": ZERO_ADDRESS,
    "WBTC": ZERO_ADDRESS,
}

chainlink_oracles = {
    "YFI": "0xa027702dbb89fbd58938e4324ac03b58d812b0e1", #YFI case handled in YFIosmProxy fixture
    "WETH": "0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419",
    "wstETH": ZERO_ADDRESS,
    "LINK": "0x2c1d072e956affc0d435cb7ac38ef18d24d9127c",
    "WBTC": "0xf4030086522a5beea4988f8ca5b36dbc97bee88c",
}

#chainlink_oracles = {
#    "YFI": ZERO_ADDRESS, #YFI case handled in YFIosmProxy fixture
#    "WETH": ZERO_ADDRESS,
#    "wstETH": ZERO_ADDRESS,
#    "LINK": ZERO_ADDRESS,
#    "WBTC": ZERO_ADDRESS,
#}

whale_addresses = {
    "YFI": "0xf977814e90da44bfa03b6295a0616a897441acec",  #or: 0xF977814e90dA44bFA03b6295A0616a897441aceC
    "WETH": "0x2f0b23f53734252bda2277357e97e1517d6b042a", #0xf584f8728b874a6a5c7a8d4d387c9aae9172d621 
    "wstETH": "0x2faf487a4414fe77e2327f0bf4ae2a264a776ad2",
    "LINK": "0xf977814e90da44bfa03b6295a0616a897441acec",
    "WBTC": "0x28c6c06298d514db089934071355e5743bf21d60",
}

whale2_addresses = {
    "YFI": "0xf977814e90da44bfa03b6295a0616a897441acec",  #or: 0xF977814e90dA44bFA03b6295A0616a897441aceC
    "WETH": "0x2f0b23f53734252bda2277357e97e1517d6b042a",
    "wstETH": "0x2faf487a4414fe77e2327f0bf4ae2a264a776ad2",
    "LINK": "0xf977814e90da44bfa03b6295a0616a897441acec",
    "WBTC": "0x28c6c06298d514db089934071355e5743bf21d60",
}


apetax_vault_address = {
    "YFI": "0xdb25cA703181E7484a155DD612b06f57E12Be5F0",
    "WETH": "0x5120FeaBd5C21883a4696dBCC5D123d6270637E9",
    "wstETH": ZERO_ADDRESS,
    "LINK": "0x671a912C10bba0CFA74Cfc2d6Fba9BA1ed9530B2",
    "WBTC": "0xA696a63cc78DfFa1a63E9E50587C197387FF6C7E",
}

production_vault_address = {
    "YFI": "0xdb25cA703181E7484a155DD612b06f57E12Be5F0",
    "WETH": "0xa258C4606Ca8206D8aA700cE2143D7db854D168c",
    "wstETH": ZERO_ADDRESS,
    "LINK": "0x671a912C10bba0CFA74Cfc2d6Fba9BA1ed9530B2",
    "WBTC": "0xA696a63cc78DfFa1a63E9E50587C197387FF6C7E",
}
#daistats.com --> collateral --> Dust: x*1e18
maker_floor = {
    "YFI": 15000e18,
    "WETH": 5000e18,
    "wstETH": 5000e18,
    "LINK": 15000e18,
    "WBTC": 7500e8,
}

#Maker ilk list: 
#ilk_list = Contract("0x5a464C28D19848f44199D003BeF5ecc87d090F87")
#for x in range(0,ilk_list.count()):
#ilk = ilk_list.get(x)
#print(f"{x}"+" "+f"{ilk_list.ilkData(ilk)['symbol']}")
#
#ilk_list.ilkData(ilk_list.get(15)).dict()
#Find liquidation collateralization ratio:
#xlip = Contract(ilk_list.ilkData(ilk_list.get(0))["xlip"])
#spot = Contract(xlip.spotter())
#liqCollRatio = spot.ilks(xlip.ilk())["mat"]/1e27
#############
# Obtaining the bytes32 ilk (verify its validity before using)
# >>> ilk = ""
# >>> for i in "YFI-A":
# ...   ilk += hex(ord(i)).replace("0x","")
# ...
# >>> ilk += "0"*(64-len(ilk))
# >>>
# >>> ilk
# '5946492d41000000000000000000000000000000000000000000000000000000'

@pytest.fixture 
def collateralToken(token):
    collateralToken = collateralToken_list[token.symbol()]
    yield collateralToken

@pytest.fixture
def gemJoinAdapter(token):
    gemJoin = Contract(gemJoin_adapters[token.symbol()])
    yield gemJoin

@pytest.fixture 
def osmProxy(token): # Allow the strategy to query the OSM proxy
    if (token.symbol() == "YFI" and useOSMforYFI == True):
        #yield YFIosmProxy
        yield Contract("0x08569B52B009F1Cd3C7765f0E3b2e49e139618bC")
    else:
        try:
            osm = Contract(osm_proxies[token.symbol()])
            yield osm
        except:
            yield ZERO_ADDRESS

@pytest.fixture
def chainlink(token):
    address = chainlink_oracles[token.symbol()]
    if address == ZERO_ADDRESS:
        yield ZERO_ADDRESS
    else:
        yield Contract(chainlink_oracles[token.symbol()])



@pytest.fixture(scope="session", autouse=True)
def token_whale(accounts, token):
    yield accounts.at(whale_addresses[token.symbol()], force=True)
    
@pytest.fixture(scope="session", autouse=True)
def token_whale2(accounts, token):
    yield accounts.at(whale2_addresses[token.symbol()], force=True)

@pytest.fixture(scope="session")
def apetax_vault(token):
    yield Contract(apetax_vault_address[token.symbol()])

@pytest.fixture(scope="session")
def production_vault(token):
    yield Contract(production_vault_address[token.symbol()])


@pytest.fixture(scope="session")
def maker_debt_floor(token):
    yield maker_floor[token.symbol()]

@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


@pytest.fixture(autouse=True)
def lib(gov, MarketLib):
    yield MarketLib.deploy({"from": gov})


@pytest.fixture
def gov(accounts):
    yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)


@pytest.fixture
def user(accounts):
    yield accounts[0]


@pytest.fixture
def rewards(accounts):
    yield accounts[1]


@pytest.fixture
def guardian(accounts):
    yield accounts[2]


@pytest.fixture
def management(accounts, strategist):
    yield strategist


@pytest.fixture
def strategist(accounts):
    yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)


@pytest.fixture
def keeper(accounts):
    yield accounts[5]


@pytest.fixture
def dai():
    dai_address = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
    yield Contract(dai_address)


@pytest.fixture
def weth():
    address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    yield Contract(address)


@pytest.fixture
def da():
    address = "0x6B175474E89094C44Da98b954EedeAC495271d0F"
    yield Contract(address)

@pytest.fixture
def yfi():
    address = "0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e"
    yield Contract(address)


@pytest.fixture
def dai_whale(accounts):
    yield accounts.at("0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643", force=True)


@pytest.fixture
def weth_whale(accounts):
    yield accounts.at("0x57757e3d981446d585af0d9ae4d7df6d64647806", force=True)

@pytest.fixture
def borrow_token(dai):
    yield dai


@pytest.fixture
def borrow_whale(dai_whale):
    yield dai_whale


@pytest.fixture
def yvault(yvDAI):
    yield yvDAI


@pytest.fixture
def yvDAI():
    vault_address = "0xdA816459F1AB5631232FE5e97a05BBBb94970c95"
    yield Contract(vault_address)


@pytest.fixture
def router():
    sushiswap_router = interface.ISwap("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F")
    yield sushiswap_router


@pytest.fixture(autouse=True)
def amount(token, token_whale2, user):
    # this will get the number of tokens (around $1m worth of token)
    hundredthousanddollars = round(50_000 / token_prices[token.symbol()])
    amount = hundredthousanddollars * 10 ** token.decimals()
    # # In order to get some funds for the token you are about to use,
    # # it impersonate a whale address
    if amount > token.balanceOf(token_whale2):
        amount = token.balanceOf(token_whale2)
    token.transfer(user, amount, {"from": token_whale2})
    yield amount


#@pytest.fixture
#def amount(accounts, token, user, token_whale):
#    amount = 10 * 10 ** token.decimals()
#    reserve = token_whale
#    token.transfer(user, amount, {"from": reserve})
#    yield amount


@pytest.fixture
def vault(pm, gov, rewards, guardian, management, token):
    Vault = pm(config["dependencies"][0]).Vault
    vault = guardian.deploy(Vault)
    vault.initialize(token, gov, rewards, "", "", guardian, management)
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(management, {"from": gov})
    yield vault


@pytest.fixture
def new_dai_yvault(pm, gov, rewards, guardian, management, dai):
    Vault = pm(config["dependencies"][0]).Vault
    vault = guardian.deploy(Vault)
    vault.initialize(dai, gov, rewards, "", "", guardian, management)
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(management, {"from": gov})
    yield vault

    
@pytest.fixture
def healthCheck():
    yield Contract("0xDDCea799fF1699e98EDF118e0629A974Df7DF012")


@pytest.fixture
def import_swap_router_selection_dict():
    yield swap_router_selection_dict


@pytest.fixture
def strategy(vault, Strategy, gov, cloner, token):
    strategy = Strategy.at(cloner.original())
    strategy.setDoHealthCheck(True, {"from": gov})
    strategy.setSwapRouterSelection(swap_router_selection_dict[token.symbol()]['swapRouterSelection'], swap_router_selection_dict[token.symbol()]['feeBorrowTokenToMidUNIV3'], swap_router_selection_dict[token.symbol()]['feeMidToWantUNIV3'], swap_router_selection_dict[token.symbol()]['midTokenChoice'], {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})
    yield strategy

@pytest.fixture
def test_strategy(
    TestStrategy,
    strategist,
    vault,
    yvault,
    token,
    gov,
    chainlink,
    collateralToken
):
    strategy = strategist.deploy(
        TestStrategy,
        vault,
        collateralToken,
        yvault,
        f"Strategy{token.symbol()}",
        chainlink
    )
    strategy.setSwapRouterSelection(swap_router_selection_dict[token.symbol()]['swapRouterSelection'], swap_router_selection_dict[token.symbol()]['feeBorrowTokenToMidUNIV3'], swap_router_selection_dict[token.symbol()]['feeMidToWantUNIV3'], swap_router_selection_dict[token.symbol()]['midTokenChoice'], {"from": gov})
    strategy.setDoHealthCheck(True, {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})
    yield strategy


@pytest.fixture(scope="session")
def RELATIVE_APPROX():
    yield 1e-5

@pytest.fixture
def cloner(
    strategist,
    vault,
    yvault,
    token,
    MarketLibCloner,
    chainlink,
    collateralToken,
):
    cloner = strategist.deploy(
        MarketLibCloner,
        vault,
        collateralToken,
        yvault,
        f"Strategy{token.symbol()}",
        chainlink
    )
    yield cloner


@pytest.fixture
def yvault_whale():
    address = "0x93a62da5a14c80f265dabc077fcee437b1a0efde"
    yield Contract(address)

@pytest.fixture(scope="module")
def multicall_swapper(interface):
    #yield interface.MultiCallOptimizedSwapper("0xB2F65F254Ab636C96fb785cc9B4485cbeD39CDAA")
    yield Contract("0xB2F65F254Ab636C96fb785cc9B4485cbeD39CDAA")

@pytest.fixture
def ymechs_safe():
    yield Contract("0x2C01B4AD51a67E2d8F02208F54dF9aC4c0B778B6")

@pytest.fixture
def univ3_swapper():
    address = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
    yield Contract(address)

@pytest.fixture
def trade_factory():
    yield Contract("0x99d8679bE15011dEAD893EB4F5df474a4e6a8b29")
