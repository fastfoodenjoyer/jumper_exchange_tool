import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from better_proxy import Proxy

from core.init_settings import settings
from libs.blockchains.eth_async.ethclient import EthClient
from core.logger import get_logger
from libs.requests.session import get_ua_parameters
from utils.utils import excname


@dataclass
class AccountData:
    """Класс для хранения данных кошелька"""
    name: str
    evm_private_key: str
    proxy: str
    evm_address: str | None = None

    aptos_private_key: str | None = None
    aptos_address: str | None = None

    solana_private_key: str | None = None
    solana_address: str | None = None

    user_agent: str | None = None
    os_user_agent: str | None = None
    chrome_version: str | None = None

    twitter_token: str | None = None
    ct0: str | None = None
    discord_token: str | None = None
    email_address: str | None = None
    email_password: str | None = None

    def __post_init__(self):
        # Убираем пробелы и переносы строк
        self.name = self.name.strip()
        if not self.evm_private_key:
            eth_client = EthClient()
            self.evm_private_key = eth_client.w3_account.key.hex()

        self.evm_private_key = self.evm_private_key.strip()
        if self.proxy:
            self.proxy = self.proxy.strip()

        # Проверяем private key
        if not self.evm_private_key.startswith('0x'):
            self.evm_private_key = f'0x{self.evm_private_key}'

        ua, os_ua, chrome_version = get_ua_parameters()
        self.user_agent = ua
        self.os_user_agent = os_ua
        self.chrome_version = chrome_version

        if self.evm_private_key:
            eth_client = EthClient(private_key=self.evm_private_key)
            self.evm_address = eth_client.w3_account.address

        if self.aptos_private_key:
            aptos_client = AptosClient(None, self.aptos_private_key)
            self.aptos_address = aptos_client.address

        if self.solana_private_key:
            self.solana_address = str(Keypair.from_base58_string(self.solana_private_key))


class ExcelManager:
    """Класс для работы с Excel файлами"""
    def __init__(self):
        self.spare_proxies: set[str] = set()  # Множество запасных прокси
        self.logger = get_logger(class_name=self.__class__.__name__)

    def load_accounts(self,
                      socials_only: bool = False,
                      excel_path: str = "accounts_data.xlsx",
                      sheet_name: str = "Main",
                      name_column: str = "Name",
                      on_off_column: str = "ON/OFF",
                      evm_private_key_column: str = "EVM Private key",
                      aptos_private_key_column: str = "Aptos Private key",
                      solana_private_key_column: str = "Solana Private key",
                      proxy_column: str = "Proxy",
                      twitter_token_column: str = "Twitter Token",
                      ct0_column: str = "ct0",
                      discord_token_column: str = "DiscordClient Token",
                      email_address_column: str = "Email Address",
                      email_password_column: str = "Email Password",
                      ) -> tuple[list[AccountData], list[str]]:
        try:
            excel_path = Path(excel_path)
            if not excel_path.exists():
                raise FileNotFoundError(f"Excel file not found: {excel_path}")

            # Читаем Excel файл
            df = pd.read_excel(excel_path, sheet_name=sheet_name, dtype=str)
            
            required_columns = [name_column, on_off_column, evm_private_key_column, proxy_column]

            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
            
            accounts = []
            used_proxies = set()
            all_proxies = set()

            if proxy_column in df.columns:
                all_proxies = {
                    Proxy.from_str(proxy.strip()).as_url
                    for proxy in df[proxy_column].dropna() 
                    if proxy.strip()
                }
            
            for _, row in df.iterrows():
                if not socials_only:
                    # Пропускаем строки без имени или приватного ключа
                    if pd.isna(row[name_column]) or pd.isna(row[evm_private_key_column]):
                        continue
                else:
                    if pd.isna(row[name_column]):
                        continue

                if str(row[on_off_column]) != "ON" and str(row[on_off_column]) != "OFF":
                    raise Exception(f"Wrong value in ON/OFF column: {row[on_off_column]}, {row[evm_private_key_column]}")

                if str(row[on_off_column]) == "OFF":
                    if settings.logging.debug_logging:
                        self.logger.debug(f"Skipping row {row[evm_private_key_column]}")
                    continue

                try:
                    proxy = row.get(proxy_column) if proxy_column in df.columns else None
                    if pd.notna(proxy):
                        proxy = Proxy.from_str(proxy.strip()).as_url
                        used_proxies.add(proxy)

                    twitter_token = row.get(twitter_token_column) if twitter_token_column in df.columns else None
                    ct0 = row.get(ct0_column) if ct0_column in df.columns else None
                    discord_token = row.get(discord_token_column) if discord_token_column in df.columns else None
                    email_address = row.get(email_address_column) if email_address_column in df.columns else None
                    email_password = row.get(email_password_column) if email_password_column in df.columns else None

                    account = AccountData(
                        name=row[name_column],
                        evm_private_key=row[evm_private_key_column] if pd.notna(row[evm_private_key_column]) else None,
                        aptos_private_key=row[aptos_private_key_column] if pd.notna(row[aptos_private_key_column]) else None,
                        solana_private_key=row[solana_private_key_column] if pd.notna(row[solana_private_key_column]) else None,
                        proxy=proxy if pd.notna(proxy) else None,
                        twitter_token=twitter_token if pd.notna(twitter_token) else None,
                        ct0=ct0 if pd.notna(ct0) else None,
                        discord_token=discord_token if pd.notna(discord_token) else None,
                        email_address=email_address if pd.notna(email_address) else None,
                        email_password=email_password if pd.notna(email_password) else None,
                    )

                    accounts.append(account)
                except Exception as e:
                    self.logger.exception(f"{excname(e)}. Error processing row {row[name_column]}: {str(e)}")
                    raise e
            
            # Находим неиспользованные прокси
            self.spare_proxies = all_proxies - used_proxies
            
            self.logger.info(f"Successfully loaded {len(accounts)} accounts from {excel_path}")
            self.logger.info(f"Found {len(self.spare_proxies)} spare proxies")
            
            return accounts, list(self.spare_proxies)
            
        except Exception as e:
            self.logger.error(f"{excname(e)}. Error loading Excel file {excel_path}: {str(e)}")
            raise
