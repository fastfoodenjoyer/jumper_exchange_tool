import asyncio
import json

import curl_cffi
from curl_cffi.requests.exceptions import ProxyError, SSLError, Timeout
from aiohttp.client_exceptions import ClientHttpProxyError, ClientProxyConnectionError
from web3.exceptions import BadFunctionCallOutput

from core.db_utils.models import Account, RouteAction
from core.logger import get_logger
from core.init_settings import settings
from libs.blockchains.eth_async.applications.jumper_exchange.jumper_client import JumperExchange
from libs.blockchains.eth_async.ethclient import NetworkClient
from libs.blockchains.omnichain_models import TokenAmount
from libs.blockchains.eth_async.exceptions import InsufficientFundsException
from utils.utils import randfloat, excname
from tasks.controller import Controller


class Executioner:
    def __init__(self, account: Account, total_account_num: int, action_num: int, total_actions: int):
        self.account = account
        self.try_num = 1
        self.action_num = action_num

        self.log_context = {
            "total_account_num": total_account_num,
            "action_num": action_num,
            "total_actions": total_actions,
            "account_name": account.name,
            "account_address": account.evm_address,
            "try_num": self.try_num,
        }

        self.logger = get_logger(
            class_name=self.__class__.__name__,
            **self.log_context
        )

    @staticmethod
    def random_to_none(action_params: dict, key: str):
        if action_params[key] == "random":
            action_params[key] = None
        return action_params

    async def sleep(self, time: float = 10, message: str = ""):
        self.logger.info(f"Sleeping for 💤{time}💤 seconds{message}.")
        await asyncio.sleep(time)

    async def gas_control(self, controller: Controller):
        if settings.gas.gas_control:
            network_client = getattr(controller.eth_client, settings.gas.gas_chain_name)
            gas_price = await network_client.transactions.gas_price()
            gwei = gas_price.Wei / 10 ** 9
            while gwei > settings.gas.maximum_gwei:
                self.logger.warning(f"High gas in {settings.gas.gas_chain_name}: {gwei} Gwei")
                await self.sleep(settings.gas.gas_retry_delay)
                gas_price = await network_client.transactions.gas_price()
                gwei = gas_price.Wei / 10 ** 9
            else:
                self.logger.success(f"Current gas price is good: {gwei} Gwei")


    def get_function(self, func_name: str):
        return self.__getattribute__(func_name)

    async def execute_action(self, action: RouteAction):
        action_params = json.loads(action.params.action_params) if action.params else {}

        action_type = action.action_type.lower()
        project_type = action_type.split("_")[0]

        action_function = self.get_function(f"execute_{project_type}_actions")

        async with Controller(self.account, self.log_context) as controller:
            while self.try_num <= settings.general.number_of_retries:
                self.log_context["try_num"] = self.try_num
                self.logger = get_logger(class_name=self.__class__.__name__, **self.log_context)
                try:
                    await self.gas_control(controller)

                    self.logger.info(f"Starting action '{action.action_name}'")
                    result = await action_function(action_type, action_params, controller)
                    if result == "Bridge isn't needed":
                        result = True

                    if result is True:
                        self.logger.success(f"Completed action {action.action_name}")
                    elif isinstance(result, dict):
                        self.logger.success(f"Completed action {action.action_name}: {result}")
                    else:
                        self.logger.error(f"Failed action {action.action_name} with reason: {result}")

                    return result

                except (ProxyError, Timeout, SSLError, curl_cffi.requests.exceptions.ConnectionError, # curl_cffi
                        ClientHttpProxyError, ClientProxyConnectionError) as e: # aiohttp
                    self.logger.error(f"{excname(e)} {str(e)}")
                    await controller.change_proxy()

                except InsufficientFundsException:
                    self.logger.error(f"Insufficient funds for transaction in action {action.action_type}")
                    return False

                except BadFunctionCallOutput:
                    self.logger.error(f"{excname(e)} {str(e)}")
                    if "uniswap" in action_type:
                        self.logger.error(f"Check provided token addresses: {action_params['swap_token_addresses']}, wrong address or token is not in desired Uniswap chain")
                        return False

                except Exception as e:
                    if settings.logging.debug_logging:
                        self.logger.exception(f"{excname(e)}. Action {action.action_type} failed: {str(e)}")
                    else:
                        self.logger.error(f"{excname(e)}. Action {action.action_type} failed: {str(e)}")
                    self.try_num += 1
                    await self.sleep(settings.general.retry_delay)

            else:
                return False # this is only if @BaseController.retry is used

    async def execute_jumper_actions(self, action_type: str, action_params: dict, controller: Controller):
        action_network = action_type.split("_")[-1]
        jumper = JumperExchange(controller, self.log_context)
        jumper.use_network(action_network)

        swap_params = action_params.get("swap")
        # bridge_params = action_params.get("bridge")

        results = {}

        # С этой настройкой true, если в ходе рандома абсолютного числа токена было выбрано количество токена,
        # превышающее баланс кошелька, то будет свапнут весь доступный баланс (если нативка - оставит на газ)
        # Если false, то при недостаточном балансе просто выдаст ошибку и пойдет дальше
        # swap_if_not_sufficient = true

        if "swap" in action_type:
            chain_swap_params = swap_params.get(action_network)
            for token_params in chain_swap_params:
                swap_amount = await self.get_evm_swap_amount(jumper.network_client,
                                                             token_params["from_token"], token_params["amount"])
                result_string = f"{action_network} from {token_params["from_token"]} to {token_params["to_token"]}"
                results[result_string] = await jumper.swap(swap_amount,
                                         token_params["from_token"],
                                         token_params["to_token"],
                                         token_params["slippage"] / 100)

                if token_params["swap_mode"] == "to_and_from":
                    if token_params["to_token"] == "native":
                        raise Exception(f"You are trying to swap back all native into token {token_params['from_token']}")

                    swap_amount = await jumper.network_client.wallet.balance(token_params["to_token"])
                    result_string = f"{action_network} from {token_params["to_token"]} to {token_params["from_token"]}"
                    results[result_string] = await jumper.swap(swap_amount,
                                                               token_params["to_token"],
                                                               token_params["from_token"],
                                                               token_params["slippage"] / 100)

        return results


    async def get_evm_swap_amount(self, network_client: NetworkClient, token: str, swap_amounts: list[float | str]):
        token = token if token.lower() != "native" else None
        decimals = await network_client.transactions.get_decimals(token) if token else 18
        balance = await network_client.wallet.balance(token)

        if all(isinstance(amount, str) for amount in swap_amounts):
            swap1 = int(swap_amounts[0])
            swap2 = int(swap_amounts[1])
            if swap1 < 0 or swap2 < 0 or swap1 > swap2 or swap1 > 100 or swap2 > 100:
                raise Exception(f"Incorrect percentage for swap: {swap_amounts}")

            swap_percent = randfloat(swap1 / 100, swap2 / 100, 0.00000001)
            return TokenAmount(float(balance.Ether) * swap_percent, decimals, False)

        elif all(isinstance(amount, float) for amount in swap_amounts):
            amount = randfloat(*swap_amounts, step=0.00000001)
            amount = TokenAmount(amount, decimals, False)
            if amount < balance:
                token_str = token if token else "native"
                self.logger.error(f"Tried to swap {amount} {token_str} but balance is {balance} {token_str}")
                raise InsufficientFundsException

        else:
            raise Exception(f"Swap amounts must be str or float: {swap_amounts}")
