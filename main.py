import asyncio
import signal
import sys

from sqlalchemy.exc import OperationalError

from core.cli import main_menu, load_presets
from core.account_manager import AccountManager
from core.db_utils.db import db
from core.init_settings import settings
from core.logger import get_logger
from utils.utils import time_until_target, read_toml

# Глобальная переменная для отслеживания состояния
shutdown_event = None


def handle_signal(signum, frame):
    """Обработчик сигнала для Windows"""
    if shutdown_event:
        shutdown_event.set()


async def shutdown(signal_, loop):
    """Корректное завершение программы при получении сигнала"""
    logger_ = get_logger(class_name='Main')
    logger_.info(f"Received exit signal {signal_.name}...")
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    for task in tasks:
        task.cancel()
    
    logger_.info(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()


async def main():
    global shutdown_event
    logger_ = get_logger(class_name='Main')
    
    # Создаем event для синхронизации завершения
    shutdown_event = asyncio.Event()
    
    # Устанавливаем обработчики сигналов
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Получаем текущий event loop
    loop = asyncio.get_running_loop()
    
    # Инициализируем менеджер аккаунтов
    account_manager = AccountManager()
    
    try:
        # Добавляем обработчики сигналов с учетом платформы
        if sys.platform != 'win32':
            # На Unix-системах используем add_signal_handler
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(shutdown(s, loop))
                )
        else:
            # На Windows используем стандартный signal.signal
            signal.signal(signal.SIGINT, handle_signal)
            signal.signal(signal.SIGTERM, handle_signal)

        
        while True:
            rerun_failed = False
            selected_preset = await main_menu()

            if selected_preset is None:
                logger_.info("Exiting application")
                break

            if selected_preset == "Continue":
                pass
            elif selected_preset == "Rerun Failed Actions":
                rerun_failed = True
            else:
                await account_manager.generate_new_routes_for_preset(selected_preset)

            if settings.delays.start_hour != 0 or settings.delays.start_minute != 0:
                while True:
                    seconds_remaining = time_until_target(settings.delays.start_time)
                    logger_.warning(f"⏰  Waiting until set start time: {settings.delays.start_time},"
                                    f" remaining {seconds_remaining} seconds")

                    if seconds_remaining <= 0:
                        break

                    sleep_time = min(seconds_remaining, 1800)
                    await asyncio.sleep(sleep_time)

                    if sleep_time == seconds_remaining:
                        break

            # start_loop = asyncio.get_running_loop()
            # start_loop.stop()
            #
            # signal.signal(signal.SIGINT, _interrupt_handler)
            # results = start_loop.run_until_complete(account_manager.launch(rerun_failed))

            # Запускаем основную задачу и мониторинг события завершения
            main_task = asyncio.create_task(account_manager.launch(rerun_failed))
            shutdown_task = asyncio.create_task(shutdown_event.wait())

            # Ждем либо завершения main_task, либо установки события shutdown_event
            done, pending = await asyncio.wait(
                [main_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            # Если первым завершился wait(), значит был получен сигнал
            if shutdown_event.is_set():
                logger_.info("Received shutdown signal, cancelling tasks...")
                main_task.cancel()
                try:
                    await main_task
                except asyncio.CancelledError:
                    logger_.info("Main task cancelled successfully")
                    return
            
    except asyncio.CancelledError:
        logger_.info("Main task cancelled")
        return
    except Exception as e:
        logger_.exception(f"An error occurred: {str(e)}")
    finally:
        # Восстанавливаем стандартные обработчики сигналов
        signal.signal(signal.SIGINT, signal.default_int_handler)
        signal.signal(signal.SIGTERM, signal.default_int_handler)
        # loop.remove_signal_handler(signal.SIGTERM)
        # loop.remove_signal_handler(signal.SIGINT)

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        # Этот код выполнится только если Ctrl+C был нажат до инициализации asyncio
        logger_ = get_logger(class_name='Main')
        logger_.info("Received keyboard interrupt before asyncio initialization")
