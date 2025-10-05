# base, somnia, xrpl-evm, flow, pharos, lisk, soneium, assetchain,
# solana
from eth_account import Account

from web3 import Web3
from web3.contract import Contract


from eth_account.datastructures import SignedTransaction


def generate_evm_account():
    """Generate a new EVM account and return private key and address."""
    account = Account.create()
    private_key = account.key.hex()
    address = account.address
    return private_key, address


def get_address(private_key: str) -> str:
    """Get the EVM address from a private key (hex string)."""
    acct = Account.from_key(private_key)
    return acct.address


CREATOR_ADDRESS = "0xdF0725C2f40380A04FBF10695d0de531a00443e8"
CREATOR_KEY = "852d82afe4e7724ea8c9f19a6eac20d317b08bd1e802cd8d6c633f7aba1e50dc"


NETWORKS_LIST_ = [
    # "SOMNIA":
    {
        "url": "https://dream-rpc.somnia.network/",
        "contract": "0x90510f40aD84eA5B01a3aC7C54C1415a24EA19D6",
    },
    # "MONAD":
    {
        "url": "https://testnet-rpc.monad.xyz/",
        "contract": "0xE496edfc5384Ba76d457a75a53B9819Ee9a62e3C",
    },
    # "XRPL_EVM":
    {
        "url": "https://rpc.testnet.xrplevm.org/",
        "contract": "0xE496edfc5384Ba76d457a75a53B9819Ee9a62e3C",
    },
    # "IOTA_EVM":
    {
        "url": "https://json-rpc.evm.testnet.iotaledger.net/",
        "contract": "0xE496edfc5384Ba76d457a75a53B9819Ee9a62e3C",
    },
]


def write_steps_to_multiple_networks(networks, user_address, step_count):
    """
    Write step data to the WalkLog contract on multiple EVM networks.
    Args:
        networks (list): List of dicts with 'url' and 'contract' keys for each network.
        user_address (str): The user's EVM address to log steps for.
        step_count (int): The number of steps to log.
    Each network is handled independently; errors are printed and do not stop the loop.
    """
    ABI_PATH = "trekkn/contracts/steps.abi"
    BYTECODE_PATH = "trekkn/contracts/steps.bin"
    try:
        ABI = open(ABI_PATH).read()
        BYTECODE = open(BYTECODE_PATH).read()
    except Exception as e:
        print(f"Error loading ABI or bytecode: {e}")
        return

    for net in networks:
        url = net.get("url")
        contract_address = net.get("contract")
        print(f"\n--- Sending to network: {url} contract: {contract_address} ---")
        try:
            # Connect to network
            web3 = Web3(Web3.HTTPProvider(url))
            walk_log_contract = web3.eth.contract(
                address=contract_address,
                abi=ABI,
                bytecode=BYTECODE,
            )
            # Build transaction
            txn = walk_log_contract.functions.logWalk(
                Web3.to_checksum_address(user_address), step_count
            ).build_transaction(
                {
                    "from": CREATOR_ADDRESS,
                    "nonce": web3.eth.get_transaction_count(CREATOR_ADDRESS),
                    "chainId": web3.eth.chain_id,
                    "gasPrice": web3.eth.gas_price,
                }
            )
            # Sign transaction
            stxn = web3.eth.account.sign_transaction(txn, private_key=CREATOR_KEY)
            # Send transaction
            send_stxn = web3.eth.send_raw_transaction(stxn.raw_transaction)
            tx_hash = send_stxn.hex()
            print(f"Success! Transaction hash: 0x{tx_hash}")
        except Exception as e:
            print(f"Error on network {url}: {e}")
    print("\nAll networks processed.")
