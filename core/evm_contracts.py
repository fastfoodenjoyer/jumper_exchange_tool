from libs.blockchains.classes import Singleton
from libs.blockchains.eth_async.data.models import RawContract, DefaultABIs, TransferAddress
from utils.utils import join_path, read_json
from core import config


class EVMContracts(Singleton):
    jumper_diamond_proxy_abi = read_json(path=join_path((config.ABIS_DIR, 'jumper_diamond_proxy.json')))

    Optimism_USDCe = RawContract(
        title='Optimism USDCe',
        address='0x7F5c764cBc14f9669B88837ca1490cCa17c31607',
        abi=DefaultABIs.Token,
        decimals=6
    )

    Unichain_USDC = RawContract(
        title='Unichain USDC',
        address='0x078D782b760474a361dDA0AF3839290b0EF57AD6',
        abi=DefaultABIs.Token,
        decimals=6
    )

    Ink_USDCe = RawContract(
        title='Ink USDCe',
        address='0xF1815bd50389c46847f0Bda824eC8da914045D14',
        abi=DefaultABIs.Token,
        decimals=6
    )

    Soneium_USDCe = RawContract(
        title='Soneium USDCe',
        address='0xbA9986D2381edf1DA03B0B9c1f8b00dc4AacC369',
        abi=DefaultABIs.Token,
        decimals=6
    )

    Lisk_USDCe = RawContract(
        title='Lisk USDCe',
        address='0xF242275d3a6527d877f2c927a82D9b057609cc71',
        abi=DefaultABIs.Token,
        decimals=6
    )

    Mode_USDC = RawContract(
        title='Mode USDC',
        address='0xd988097fb8612cc24eeC14542bC03424c656005f',
        abi=DefaultABIs.Token,
        decimals=6
    )

    Base_USDC = RawContract(
        title='Base USDC',
        address='0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
        abi=DefaultABIs.Token,
        decimals=6
    )
