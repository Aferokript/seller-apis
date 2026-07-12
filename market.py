import datetime
import logging.config
from environs import Env
from seller import download_stock

import requests

from seller import divide, price_conversion

logger = logging.getLogger(__file__)


def get_product_list(page, campaign_id, access_token):
    '''Получить список товаров

    Функция делает запрос к API яндекс маркета и в ответ получает список товаров
    Урл строится из идентификатора вашего магазина ( campaign_id ), API-Токена и пагинации

    Args:
        page (str): Пагинация, с какого места выдавать следующую порцию товаров
        campaign_id (str): Id Компании
        access_token (str): API_Token продавца

    Returns:
        list: список с товарами

    Raises:
        TypeError: Аргументы должны быть в формате int
        requests.exceptions.HTTPError: При ошибке HTTP запроса
    Example:

        get_product_list(page, campaign_id, access_token')
        список товаров.

    '''

    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {
        "page_token": page,
        "limit": 200,
    }
    url = endpoint_url + f"campaigns/{campaign_id}/offer-mapping-entries"
    response = requests.get(url, headers=headers, params=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object.get("result")


def update_stocks(stocks, campaign_id, access_token):
    ''' Обновляет товар

    Функция обновляет остатки товара

    Args:
        stocks (list): Список товаров
        campaign_id (str): Ваш идентификатор продавца
        access_token (str): API-Токен продавца

    Returns:
        dict: Результат операции

    Raises:
        TypeError: stocks не является списком. Остальные аргументы должны быть в формате int
        requests.exceptions.HTTPError: При ошибке HTTP запроса

    Example:
        update_stocks(list, campaign_id )
        Результат операции

    '''

    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {"skus": stocks}
    url = endpoint_url + f"campaigns/{campaign_id}/offers/stocks"
    response = requests.put(url, headers=headers, json=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object


def update_price(prices, campaign_id, access_token):
    '''Обновляет цену

    Функция обновляет цену товара

    Args:
        prices (list): Список товаров и цен
        campaign_id (str): Ваш идентификатор продавца
        access_token (str): Ваш API-Токен

    Returns:
        dict: Результат операции

    Raises:
        TypeError: prices не является списком. Остальные аргументы должны быть в формате int
        requests.exceptions.HTTPError: При ошибке HTTP запроса

    Example:
        update_price(list, campaign_id, access_token)
        Результат операции

    '''

    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {"offers": prices}
    url = endpoint_url + f"campaigns/{campaign_id}/offer-prices/updates"
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object


def get_offer_ids(campaign_id, market_token):
    """Получить артикулы товаров Яндекс маркета

    Функция принимает идентификатор продавца, по нему находит товары и возвращает их арктикулы

    Args:
        campaign_id (str): Идентификатор продавца
        market_token (str): Токен подтверждения прав

    Returns:
        list: Список с арктикулами товаров

    Raises:
        TypeError: prices не является списком или market_token не является строкой
        requests.exceptions.HTTPError: При ошибке HTTP запроса

    Example:
        get_offer_ids(campaign_id, market_token)
        Список с арктикулами товаров

    """

    page = ""
    product_list = []
    while True:
        some_prod = get_product_list(page, campaign_id, market_token)
        product_list.extend(some_prod.get("offerMappingEntries"))
        page = some_prod.get("paging").get("nextPageToken")
        if not page:
            break
    offer_ids = []
    for product in product_list:
        offer_ids.append(product.get("offer").get("shopSku"))
    return offer_ids


def create_stocks(watch_remnants, offer_ids, warehouse_id):
    '''Уберем то, что не загружено в market

    Функция создает список, генерирует время для API, проходится по словарю
    и в случае успеха добавляет товары

    Args:
        watch_remnants (list): список с товаром
        offer_ids (int) идентификатор продавца
        warehouse_id (str) числовой идентификатор склада

    Returns:
        list: список того что не загружено

    Raises:
        TypeError: watch_remnants пустой или не является списком. Остальные аргументы в формате int
        requests.exceptions.HTTPError: При ошибке HTTP запроса

    Example:
        create_stocks(watch_remnants, offer_ids, warehouse_id)
        Список того что не загружно в market

    '''

    stocks = list()
    date = str(datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z")
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            count = str(watch.get("Количество"))
            if count == ">10":
                stock = 100
            elif count == "1":
                stock = 0
            else:
                stock = int(watch.get("Количество"))
            stocks.append(
                {
                    "sku": str(watch.get("Код")),
                    "warehouseId": warehouse_id,
                    "items": [
                        {
                            "count": stock,
                            "type": "FIT",
                            "updatedAt": date,
                        }
                    ],
                }
            )
            offer_ids.remove(str(watch.get("Код")))

    for offer_id in offer_ids:
        stocks.append(
            {
                "sku": offer_id,
                "warehouseId": warehouse_id,
                "items": [
                    {
                        "count": 0,
                        "type": "FIT",
                        "updatedAt": date,
                    }
                ],
            }
        )
    return stocks


def create_prices(watch_remnants, offer_ids):
    '''Задать цену товару

    Функция задает цену вашим товарам

    Args:
        watch_remnants (list): Список товаров
        offer_ids (list): Список уже существующих товаров

    Returns:
        list: Список с товарами которые мы загрузили

    Raises:
        TypeError: watch_remnants пустой или не является списком. Остальные аргументы в формате int
        requests.exceptions.HTTPError: При ошибке HTTP запроса

    Example:
        create_prices(watch_remnants, offer_ids)
        список товаров которым задали цену

    '''

    prices = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            price = {
                "id": str(watch.get("Код")),
                "price": {
                    "value": int(price_conversion(watch.get("Цена"))),
                    "currencyId": "RUR",
                },
            }
            prices.append(price)
    return prices


async def upload_prices(watch_remnants, campaign_id, market_token):
    """Загрузить цены товаров в Яндекс Маркет

    Функция получает список товаров, фильтрует те, которые уже есть на маркетплейсе,
    и отправляет их цены в API Яндекс Маркета. Отправка происходит порциями по 500 товаров.

    Args:
        watch_remnants (list): Список товаров с ключами "Код" и "Цена"
        campaign_id (str): ID кампании
        market_token (str): Токен магазина

    Returns:
        list: Отправленные цены

    Raises:
        requests.exceptions.HTTPError: При ошибке HTTP запроса

    Example:
     upload_prices(watch_remnants, campaign_id, market_token)
    """
    offer_ids = get_offer_ids(campaign_id, market_token)
    prices = create_prices(watch_remnants, offer_ids)
    for some_prices in list(divide(prices, 500)):
        update_price(some_prices, campaign_id, market_token)
    return prices


async def upload_stocks(watch_remnants, campaign_id, market_token, warehouse_id):
    """Загрузить остатки товаров в Яндекс Маркет

    Функция получает список товаров, фильтрует те, которые уже есть на маркетплейсе,
    и отправляет их остатки в API Яндекс Маркета. Отправка происходит порциями по 2000 товаров.
    Возвращает два списка: товары с ненулевым остатком и все отправленные остатки.

    Args:
        watch_remnants (list): Список товаров с ключами "Код" и "Количество"
        campaign_id (str): ID кампании
        market_token (str): API-токен
        warehouse_id (str): ID склада

    Returns:
        tuple: (товары с ненулевым остатком, все отправленные остатки)

    Raises:
        requests.exceptions.HTTPError: При ошибке HTTP запроса

    Example:
       upload_stocks(watch_remnants, campaign_id, market_token, warehouse_id))
    """

    offer_ids = get_offer_ids(campaign_id, market_token)
    stocks = create_stocks(watch_remnants, offer_ids, warehouse_id)
    for some_stock in list(divide(stocks, 2000)):
        update_stocks(some_stock, campaign_id, market_token)
    not_empty = list(
        filter(lambda stock: (stock.get("items")[0].get("count") != 0), stocks)
    )
    return not_empty, stocks

def main():
    env = Env()
    market_token = env.str("MARKET_TOKEN")
    campaign_fbs_id = env.str("FBS_ID")
    campaign_dbs_id = env.str("DBS_ID")
    warehouse_fbs_id = env.str("WAREHOUSE_FBS_ID")
    warehouse_dbs_id = env.str("WAREHOUSE_DBS_ID")

    watch_remnants = download_stock()
    try:
        # FBS
        offer_ids = get_offer_ids(campaign_fbs_id, market_token)
        # Обновить остатки FBS
        stocks = create_stocks(watch_remnants, offer_ids, warehouse_fbs_id)
        for some_stock in list(divide(stocks, 2000)):
            update_stocks(some_stock, campaign_fbs_id, market_token)
        # Поменять цены FBS
        upload_prices(watch_remnants, campaign_fbs_id, market_token)

        # DBS
        offer_ids = get_offer_ids(campaign_dbs_id, market_token)
        # Обновить остатки DBS
        stocks = create_stocks(watch_remnants, offer_ids, warehouse_dbs_id)
        for some_stock in list(divide(stocks, 2000)):
            update_stocks(some_stock, campaign_dbs_id, market_token)
        # Поменять цены DBS
        upload_prices(watch_remnants, campaign_dbs_id, market_token)
    except requests.exceptions.ReadTimeout:
        print("Превышено время ожидания...")
    except requests.exceptions.ConnectionError as error:
        print(error, "Ошибка соединения")
    except Exception as error:
        print(error, "ERROR_2")


if __name__ == "__main__":
    main()

