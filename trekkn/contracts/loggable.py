# somnia,
#  monad
# megaeth
#  flow,

#  xrpl-evm,

# base,
#  pharos,
#  lisk,
#  soneium,
#  assetchain,
# solana
from eth_account import Account

from web3 import Web3
from web3.contract import Contract
from eth_account.datastructures import SignedTransaction


CREATOR_ADDRESS = "0xdF0725C2f40380A04FBF10695d0de531a00443e8"
CREATOR_KEY = "852d82afe4e7724ea8c9f19a6eac20d317b08bd1e802cd8d6c633f7aba1e50dc"


NETWORKS_LIST_ = [
    # "SOMNIA":
    {
        "url": "https://dream-rpc.somnia.network/",
        "contract": "0x661A88CEF5Bb8f58822C4f334C482d1Bf0DcD1e7",
    },
    # "MONAD":
    {
        "url": "https://testnet-rpc.monad.xyz/",
        "contract": "0x0D1f40B591FbB15CDFD5bd9e03734acc114de49e",
    },
    # "MEGAETH":
    {
        "url": "https://carrot.megaeth.com/rpc/",
        "contract": "0xe496edfc5384ba76d457a75a53b9819ee9a62e3c",
    },
    # "FLOW":
    {
        "url": "https://testnet.evm.nodes.onflow.org/",
        "contract": "0xE496edfc5384Ba76d457a75a53B9819Ee9a62e3C",
    },
    # # "ASSETCHAIN":
    # {
    #     "url": "https://enugu-rpc.assetchain.org/",
    #     "contract": "0xE496edfc5384Ba76d457a75a53B9819Ee9a62e3C",
    # },
    #
    #
    # "IOTA_EVM":
    # {
    #     "url": "https://json-rpc.evm.testnet.iotaledger.net/",
    #     "contract": "0xE496edfc5384Ba76d457a75a53B9819Ee9a62e3C",
    # },
    # "XRPL_EVM":
    {
        "url": "https://rpc.testnet.xrplevm.org/",
        "contract": "0x7965b0cff0ebe04051f221f07429d38d147c0c5c",
    },
]


def write_steps_to_multiple_networks(
    user_address,
    step_count,
):
    """
    Write step data to the WalkLog contract on multiple EVM networks.
    Args:

        user_address (str): The user's EVM address to log steps for.
        step_count (int): The number of steps to log.
    Each network is handled independently; errors are printed and do not stop the loop.
    """
    ABI_PATH = "trekkn/contracts/steps.abi"
    BYTECODE_PATH = "trekkn/contracts/steps.bin"
    if user_address:
        user_address = Web3.to_checksum_address(user_address)
    else:
        user_address = Web3.to_checksum_address(CREATOR_ADDRESS)
    try:
        ABI = open(ABI_PATH).read()
        BYTECODE = open(BYTECODE_PATH).read()
    except Exception as e:
        print(f"Error loading ABI or bytecode: {e}")
        return

    for net in NETWORKS_LIST_:
        url = net.get("url")
        contract_address = net.get("contract")
        print(f"\n--- Sending to network: {url} contract: {contract_address} ---")
        try:
            # Connect to network
            web3 = Web3(Web3.HTTPProvider(url))
            walk_log_contract: Contract = web3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=ABI,
                bytecode=BYTECODE,
            )
            # Build transaction
            txn = walk_log_contract.functions.logWalk(
                user_address,
                step_count,
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
            print(f"Success! network {net["url"]} Transaction hash: 0x{tx_hash}")
        except Exception as e:
            print(f"Error on network {url}: {e}")
    print("\nAll networks processed.")
