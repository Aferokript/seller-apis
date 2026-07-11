def get_product_list(last_id, client_id, seller_token):
    """Получить список товаров магазина озон

    Функция отправляет запрос к API Ozon и возвращает список товаров с пагинацией.

    Args:
        last_id (str): Id последнего товара
        client_id (str): Публичный идентификатор продавца
        seller_token (str): Api-токен продавца

    Returns:
        dict: Словарь с товарами

    Raises:
        TypeError: Аргументы должны быть в формате int
        requests.exceptions.HTTPError: При ошибке HTTP запроса

    Example:
        get_product_list(last_id, client_id, seller_token).
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

    Функция получает все товары и извлекает из них артикулы.

    Args:
        client_id (str): Id клиента
        seller_token (str): Публичный идентификатор продавца

    Returns:
        list: Артикулы всех товаров

    Raises:
        TypeError: Аргументы должны быть в формате int
        requests.exceptions.HTTPError: При ошибке HTTP запроса

    Examples:
        offer_ids = get_offer_ids(client_id, seller_token).
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

    Функция отправляет запрос на обновление цен для указанных товаров.

    Args:
        prices (list): Список с товарами и ценами
        client_id (str): Публичный идентификатор продавца
        seller_token (str): Api-токен продавца

    Returns:
        dict: Результат операции

    Raises:
        TypeError: Аргументы должны быть в формате int
        requests.exceptions.HTTPError: При ошибке HTTP запроса

    Examples:
        prices = [{"product_id": 12345678, "price": "1990.00"}]
        update_price(prices, client_id, seller_token).
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
    """Обновить остатки товаров

    Функция отправляет запрос на обновление остатков для указанных товаров.

    Args:
        stocks (list): Список с товарами и остатками
        client_id (str): Публичный идентификатор продавца
        seller_token (str): Api-токен продавца

    Returns:
        dict: Результат операции

    Raises:
        TypeError: Аргументы должны быть в формате int
        requests.exceptions.HTTPError: При ошибке HTTP запроса

    Examples:
        stocks = [{"offer_id": "CASIO-001", "stock": 15}]
        update_stocks(stocks, client_id, seller_token).
    """
    url = "https://api-seller.ozon.ru/v2/product/stocks"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {"stocks": stocks}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def download_stock():
    """Скачать файл остатков с сайта casio

    Функция скачивает zip-архив с сайта timeworld.ru, распаковывает и читает excel-файл.

    Returns:
        list: Список словарей с остатками

    Raises:
        requests.exceptions.HTTPError: При ошибке HTTP запроса
        FileNotFoundError: Если файл не найден

    Examples:
        watch_remnants = download_stock().
    """

    casio_url = "https://timeworld.ru/upload/files/ostatki.zip"
    session = requests.Session()
    response = session.get(casio_url)
    response.raise_for_status()
    with response, zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(".")
    excel_file = "ostatki.xls"
    watch_remnants = pd.read_excel(
        io=excel_file,
        na_values=None,
        keep_default_na=False,
        header=17,
    ).to_dict(orient="records")
    os.remove("./ostatki.xls")
    return watch_remnants


def create_stocks(watch_remnants, offer_ids):
    """Создать список остатков для загрузки в Ozon

    Функция сопоставляет остатки из Casio с артикулами на Ozon.

    Args:
        watch_remnants (list): Список словарей с остатками из Casio
        offer_ids (list): Список артикулов на Ozon

    Returns:
        list: Список словарей с остатками

    Raises:
        TypeError: Аргументы должны быть в формате list

    Examples:
        stocks = create_stocks(watch_remnants, offer_ids).
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

    Функция сопоставляет цены из Casio с артикулами на Ozon.

    Args:
        watch_remnants (list): Список словарей с ценами из Casio
        offer_ids (list): Список артикулов на Ozon

    Returns:
        list: Список словарей с ценами

    Raises:
        TypeError: Аргументы должны быть в формате list

    Examples:
        prices = create_prices(watch_remnants, offer_ids).
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

    Функция удаляет из цены все лишние символы, оставляя только цифры.

    Args:
        price (str): Цена товара

    Returns:
        str: Отформатированная цена

    Raises:
        TypeError: Формат цены должен быть str

    Examples:
        price_conversion("5'900.00").
    """

    return re.sub("[^0-9]", "", price.split(".")[0])


def divide(lst: list, n: int):
    """Разделить список на части

    Функция делит список на части заданного размера.

    Args:
        lst (list): Список
        n (int): Размер части

    Yields:
        list: Часть списка

    Raises:
        TypeError: Если lst не список или n не число

    Examples:
        list(divide([1, 2, 3, 4, 5], 2)).
    """

    for i in range(0, len(lst), n):
        yield lst[i : i + n]


async def upload_prices(watch_remnants, client_id, seller_token):
    """Загрузить цены в Ozon

    Функция получает артикулы, создает цены и отправляет их частями.

    Args:
        watch_remnants (list): Список словарей с ценами
        client_id (str): Публичный идентификатор продавца
        seller_token (str): Api-токен продавца

    Returns:
        list: Список отправленных цен

    Raises:
        Exception: При ошибках получения артикулов или отправки цен

    Examples:
        prices = await upload_prices(watch_remnants, client_id, seller_token).
    """

    offer_ids = get_offer_ids(client_id, seller_token)
    prices = create_prices(watch_remnants, offer_ids)
    for some_price in list(divide(prices, 1000)):
        update_price(some_price, client_id, seller_token)
    return prices


async def upload_stocks(watch_remnants, client_id, seller_token):
    """Загрузить остатки в Ozon

    Функция получает артикулы, создает остатки и отправляет их частями.

    Args:
        watch_remnants (list): Список словарей с остатками
        client_id (str): Публичный идентификатор продавца
        seller_token (str): Api-токен продавца

    Returns:
        tuple: (not_empty, stocks) - товары с остатком и все остатки

    Raises:
        Exception: При ошибках получения артикулов или отправки остатков

    Examples:
        not_empty, stocks = await upload_stocks(watch_remnants, client_id, seller_token).
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
        stocks = create_stocks(watch_remnants, offer_ids)
        for some_stock in list(divide(stocks, 100)):
            update_stocks(some_stock, client_id, seller_token)
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
