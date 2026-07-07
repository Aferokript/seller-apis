import io
import logging.config
import os
import re
import zipfile
from environs import Env

import pandas as pd
import requests

logger = logging.getLogger(__file__)


def get_product_list(last_id, client_id, seller_token):
    """Получить список товаров магазина озон

    Функция отправляет через API запрос и получает список всех товаров с пагинацией

    Args:
        last_id (int): Id Последнего товара
        client_id (int): Id Клиента
        seller_token (str): API-Токен продавца

    Returns:
       dict: Словарь с ценами на товар

    Raises:
        TypeError: Аргументы должны быть в формате int
        Requests.exceptions.HTTPError: При ошибке HTTP запроса

    Examples:
        product = get_product_list(last_id, client_id, seller_token)
        print(product)
        Список товаров

    """
    url = "https://api-seller.ozon.ru/v2/product/list"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {
        "filter": {
            "visibility": "ALL",
        },
        "last_id": last_id,
        "limit": 1000,
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    response_object = response.json()
    return response_object.get("result")


def get_offer_ids(client_id, seller_token):
    """Получить артикулы товаров магазина озон

    Функция возвращает арктикулы товаров на Озоне

    Args:
        client_id (int): Id Клиента
        seller_token (str): API_Токен продавца

    Returns:
        list: Арктикулы всех товаров

    Raises:
        TypeError: Аргументы должны быть в формате int
        Requests.exceptions.HTTPError: При ошибке HTTP запроса функцией get_product_list

    Examples:
        articticles = get_offer_ids(client_id, seller_token)
        print(articles)
        Список с арктикулами товаров

    """

    last_id = ""
    product_list = []
    while True:
        some_prod = get_product_list(last_id, client_id, seller_token)
        product_list.extend(some_prod.get("items"))
        total = some_prod.get("total")
        last_id = some_prod.get("last_id")
        if total == len(product_list):
            break
    offer_ids = []
    for product in product_list:
        offer_ids.append(product.get("offer_id"))
    return offer_ids


def update_price(prices: list, client_id, seller_token):
    """Обновить цены товаров

    Функция позволяет обновить цену на товар в вашем магазине
    Цена передается списком словарей

    Args:
        prices (list): Список с товарами и ценами
        client_id (int): Id-Клиента
        seller_token (int): API-Токен продавца

    Returns:
        dict: Словарь с результатами операции

    Raises:
        TypeError: Аргументы должны быть в формате int
        Requests.exceptions.HTTPError: При ошибке HTTP запроса функцией get_product_list

    Examples:
        prices = [
           {"product_id": 12345678, "price": "1990.00"}
        watch = update_price(prices, client_id, seller_token)

    """
    url = "https://api-seller.ozon.ru/v1/product/import/prices"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {"prices": prices}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def update_stocks(stocks: list, client_id, seller_token):
    """Обновить остатки товаров в магазине Ozon

        Отправляет запрос на обновление остатков для указанных товаров.
        Процесс выполняется асинхронно — остатки не обновляются мгновенно.

        Args:
            stocks: Список словарей с данными о товарах и остатках.
            client_id: Идентификатор клиента из личного кабинета Ozon.
            seller_token: API-токен продавца.

        Returns:
            Словарь с результатом операции.
            Содержит информацию о статусе обновления.

        Raises:
            Exception: При ошибках выполнения запроса или неверном формате данных.

        Examples:
            stocks = []
            update_stocks(stocks, client_id, seller_token)

        """
    url = "https://api-seller.ozon.ru/v1/product/import/stocks"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {"stocks": stocks}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def download_stock():
    """Создать список остатков для загрузки в Ozon

        Сопоставляет остатки из файла Casio с артикулами на Ozon.
        Преобразует значения количества в формат, понятный для Ozon.

        Args:
            watch_remnants: Список словарей с данными о товарах из Casio.
                            Ожидается, что каждый словарь содержит ключи "Код" и "Количество".
            offer_ids: Список артикулов товаров, загруженных на Ozon.

        Returns:
            Список словарей. Каждый словарь содержит:
                - offer_id: артикул товара (строка)
                - stock: количество на складе (целое число)

        Examples:
            Функция изменяет переданный список offer_ids.
        """
    casio_url = "https://timeworld.ru/upload/files/ostatki.zip"
    session = requests.Session()
    response = session.get(casio_url)
    response.raise_for_status()
    with response, zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(".")
    # Создаем список остатков часов:
    excel_file = "ostatki.xls"
    watch_remnants = pd.read_excel(
        io=excel_file,
        na_values=None,
        keep_default_na=False,
        header=17,
    ).to_dict(orient="records")
    os.remove("./ostatki.xls")  # Удалить файл
    return watch_remnants


def create_stocks(watch_remnants, offer_ids):
    """Создать список остатков для обновления на Ozon

        Функция сопоставляет остатки из файла Casio с артикулами на Ozon.
        Товары, которых нет в файле Casio, получают остаток 0.

        Args:
            watch_remnants (list): Список словарей с остатками из Casio.
            offer_ids (list): Список артикулов товаров, загруженных на Ozon

        Returns:
            list: Список словарей с остатками для Ozon:
                - offer_id (str): Артикул товара
                - stock (int): Количество на складе (0, 100 или точное число)

        Examples:
            Функция изменяет переданный список offer_ids (удаляет обработанные артикулы).

        """
    stocks = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            count = str(watch.get("Количество"))
            if count == ">10":
                stock = 100
            elif count == "1":
                stock = 0
            else:
                stock = int(watch.get("Количество"))
            stocks.append({"offer_id": str(watch.get("Код")), "stock": stock})
            offer_ids.remove(str(watch.get("Код")))
    for offer_id in offer_ids:
        stocks.append({"offer_id": offer_id, "stock": 0})
    return stocks


def create_prices(watch_remnants, offer_ids):
    """Создать список цен для загрузки в Ozon

        Сопоставляет цены из файла Casio с артикулами на Ozon.
        Возвращает список словарей с ценами для дальнейшей загрузки.

        Args:
            watch_remnants: Список словарей с данными из Casio.
            offer_ids: Список артикулов товаров на Ozon.

        Returns:
            Список словарей с данными о ценах.
            Структура определяется API Ozon.

        Raises:
            Exception: При ошибках форматирования или неверных данных.

        Examples:
             watch_remnants = [{"Код": "CASIO-001", "Цена": "5'900.00"}]
             offer_ids = ["CASIO-001"]
             create_prices(watch_remnants, offer_ids)
             [{'offer_id': 'CASIO-001', 'price': '5900', 'currency_code': 'RUB',
             'auto_action_enabled': 'UNKNOWN', 'old_price': '0'}]

         Если товара нет в offer_ids:

         create_prices([{"Код": "CASIO-999", "Цена": "1000"}], ["CASIO-001"])
        """

    prices = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            price = {
                "auto_action_enabled": "UNKNOWN",
                "currency_code": "RUB",
                "offer_id": str(watch.get("Код")),
                "old_price": "0",
                "price": price_conversion(watch.get("Цена")),
            }
            prices.append(price)
    return prices


def price_conversion(price: str) -> str:
    """Преобразовать цену

    Функция форматирует товар цены, убирая лишние символы и делает цену читабельной

    Args:
         price (str): Цена товара

    Returns:
        str: Отформатированая цена товара

    Raises:
           TypeError: Формат цены должен быть str

    Examples:
             price_of_phone = 5'900.00
             price_conversion(price_of_phone)
             5900
    """

    return re.sub("[^0-9]", "", price.split(".")[0])


def divide(lst: list, n: int):
    """Разделить список на части по n элементов

       Args:
           lst: Список для разделения
           n: Максимальный размер одной части

       Yields:
           Часть списка размером не более n элементов

       Raises:
           TypeError: Если lst не список или n не число

       Examples:
           list(divide([1, 2, 3, 4, 5], 2))
           [[1, 2], [3, 4], [5]]
    """
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


async def upload_prices(watch_remnants, client_id, seller_token):
    """Загрузить цены товаров в Ozon

        Получает артикулы с Ozon, создаёт список цен и отправляет их частями.
        Цены отправляются порциями по 1000 товаров (ограничение API).

        Args:
            watch_remnants: Список словарей с данными из Casio
            client_id: ID клиента Ozon
            seller_token: API-токен продавца

        Returns:
            Список отправленных цен

        Raises:
            Exception: При ошибках получения артикулов или отправки цен

        Examples:
           watch_remnants = [{"Код": "CASIO-001", "Цена": "5900"}]
            prices = await upload_prices(watch_remnants, 123456, "token")
            len(prices)
            1
    """
    offer_ids = get_offer_ids(client_id, seller_token)
    prices = create_prices(watch_remnants, offer_ids)
    for some_price in list(divide(prices, 1000)):
        update_price(some_price, client_id, seller_token)
    return prices


async def upload_stocks(watch_remnants, client_id, seller_token):
    """Загрузить остатки товаров в Ozon

        Получает артикулы с Ozon, создаёт список остатков и отправляет их частями.
        Остатки отправляются порциями по 100 товаров (ограничение API).

        Args:
            watch_remnants: Список словарей с данными из Casio
            client_id: ID клиента Ozon
            seller_token: API-токен продавца

        Returns:
            Кортеж (not_empty, stocks):
                - not_empty: товары с ненулевым остатком
                - stocks: все отправленные остатки

        Raises:
            Exception: При ошибках получения артикулов или отправки остатков

        Examples:
             watch_remnants = [{"Код": "CASIO-001", "Количество": 15}]
             not_empty, stocks = await upload_stocks(watch_remnants, 123456, "token")
             len(not_empty)  # Только с ненулевым остатком
            1
            len(stocks)  # Все остатки
            1
    """
    offer_ids = get_offer_ids(client_id, seller_token)
    stocks = create_stocks(watch_remnants, offer_ids)
    for some_stock in list(divide(stocks, 100)):
        update_stocks(some_stock, client_id, seller_token)
    not_empty = list(filter(lambda stock: (stock.get("stock") != 0), stocks))
    return not_empty, stocks


def main():
    env = Env()
    seller_token = env.str("SELLER_TOKEN")
    client_id = env.str("CLIENT_ID")
    try:
        offer_ids = get_offer_ids(client_id, seller_token)
        watch_remnants = download_stock()
        # Обновить остатки
        stocks = create_stocks(watch_remnants, offer_ids)
        for some_stock in list(divide(stocks, 100)):
            update_stocks(some_stock, client_id, seller_token)
        # Поменять цены
        prices = create_prices(watch_remnants, offer_ids)
        for some_price in list(divide(prices, 900)):
            update_price(some_price, client_id, seller_token)
    except requests.exceptions.ReadTimeout:
        print("Превышено время ожидания...")
    except requests.exceptions.ConnectionError as error:
        print(error, "Ошибка соединения")
    except Exception as error:
        print(error, "ERROR_2")


if __name__ == "__main__":
    main()
