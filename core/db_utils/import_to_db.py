import random
import traceback

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from loguru import logger

from core.db_utils.db import db
from core.db_utils.models import Account
from core.excel import AccountData


# Этот файл только для постоянной базы

class ImportToDB:
    imported = []
    edited = []

    @staticmethod
    async def add_info_to_db(accounts_data: list[AccountData]) -> None:
        """
        Добавляет или обновляет информацию об аккаунтах в базе данных.
        :param accounts_data: список словарей с полями 'solana_pk', 'evm_pk', 'proxy'
        """
        if not accounts_data:
            logger.info('There are no wallets in the file!')
            return

        total = len(accounts_data)
        logger.info(f'Начинаем импорт {total} аккаунтов')

        """
        name: str
        evm_private_key: str
        proxy: str
        evm_address: str | None = None
        user_agent: str | None = None
        os_user_agent: str | None = None
        chrome_version: str | None = None
        """

        for num, account in enumerate(accounts_data, start=1):
            logger.info(f'Импортирую аккаунт {num} из {total}')
            try:
                # Проверяем, есть ли уже запись в БД
                account_instance = await db.get_account_by_pk(account.evm_private_key)

                if account_instance:
                    # Обновляем, если есть изменения
                    await ImportToDB.update_account_instance(
                        account_instance,
                        account.evm_private_key,
                        account.proxy,
                        # twitter,
                        # discord,
                        # invite_code
                    )
                else:
                    # Создаём новую запись
                    account_instance = Account(
                        name=account.name,
                        private_key=account.evm_private_key,
                        evm_address=account.evm_address,
                        proxy=account.proxy,
                        user_agent=account.user_agent,
                        os_user_agent=account.os_user_agent,
                        chrome_version=account.chrome_version
                    )
                    ImportToDB.imported.append(account_instance)
                    db.add(account_instance)

            except Exception as err:
                logger.error(f'Ошибка при обработке аккаунта №{num}: {err}')
                logger.exception('Stack Trace:')

        # Формируем текстовый отчёт
        # report_lines = []
        #
        # if ImportToDB.imported:
        #     report_lines.append("\n--- Imported")
        #     report_lines.append("{:<4}{:<45}{:<45}{:<25}".format("N", "Sol Address", "EVM Address", "Proxy"))
        #     for i, wallet in enumerate(ImportToDB.imported, 1):
        #         report_lines.append(
        #             "{:<4}{:<45}{:<45}{:<25}".format(
        #                 i,
        #                 wallet.sol_address or "-",
        #                 wallet.evm_address or "-",
        #                 wallet.proxy or "-"
        #             )
        #         )
        #
        # if ImportToDB.edited:
        #     report_lines.append("\n--- Edited")
        #     report_lines.append("{:<4}{:<45}{:<45}{:<25}".format("N", "Sol Address", "EVM Address", "Proxy"))
        #     for i, wallet in enumerate(ImportToDB.edited, 1):
        #         report_lines.append(
        #             "{:<4}{:<45}{:<45}{:<25}".format(
        #                 i,
        #                 wallet.sol_address or "-",
        #                 wallet.evm_address or "-",
        #                 wallet.proxy or "-"
        #             )
        #         )
        #
        # # Логируем и выводим финальную информацию
        # if report_lines:
        #     full_report = "\n".join(report_lines)
        #     _logger.info(full_report)  # Выводим в лог
        #     # print(full_report)        # Дублируем в консоль
        #
        # _logger.info(
        #     f"Импорт завершён! "
        #     f"Импортировано: {len(ImportToDB.imported)} из {total}. "
        #     f"Обновлено: {len(ImportToDB.edited)} из {total}."
        # )
        # print(
        #     f"Done! {len(ImportToDB.imported)}/{total} wallets were imported, "
        #     f"and {len(ImportToDB.edited)}/{total} wallets were updated."
        # )
        #
        # try:
        #     await session.commit()
        # except IntegrityError as e:
        #     await session.rollback()
        #     if "UNIQUE constraint failed" in str(e.orig):
        #         print(f"Ошибка: Дублирующая запись. Данные не добавлены: {e}")
        #         return
        #     else:
        #         print(f"Неожиданная ошибка: {e}")
        #         return


    @staticmethod
    async def update_account_instance(
            account_instance: Account,
            name: str,
            proxy: str,

    ) -> None:
        """
        Обновляет поля account_instance, если они отличаются от текущих.
        :param name: name
        :param account_instance: модель аккаунта, которую нужно обновить
        :param proxy: обновлённый прокси
        """
        has_changed = False

        if account_instance.name != name:
            account_instance.name = name
            has_changed = True

        if account_instance.proxy != proxy:
            account_instance.proxy = proxy
            has_changed = True

        # if account_instance.twitter_token != twitter:
        #     account_instance.twitter_token = twitter
        #     account_instance.twitter_account_status = "UKNOWN"
        #     has_changed = True

        # if account_instance.discord_token != discord:
        #     account_instance.discord_token = discord
        #     has_changed = True

        # if account_instance.turbo_tap_invite_code != invite_code:
        #     account_instance.turbo_tap_invite_code = invite_code
        #     has_changed = True

        if has_changed:
            ImportToDB.edited.append(account_instance)
            db.merge(account_instance)
