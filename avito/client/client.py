import datetime
import backoff

from typing import List
from loguru import logger
from pydantic import BaseModel

from avito.settings import AVITOSettings


class Avito:
    # Отправка запросов в API
    # Авторизация
    # Обработка ошибок
    BASE_URL = "https://api.avito.ru/"

    def __init__(self) -> None:
        self._token = None
        self.settings = AVITOSettings()

    def get_access_token(self):
        response = r.post(
            f"{self.BASE_URL}token",
            params={
                "client_id": self.settings.AVITO_CLIENT_ID,
                "client_secret": self.settings.AVITO_SECRET,
                "grant_type": "client_credentials",
            },
        )
        if not response.ok:
            logger.warning(r.json())
            assert (
                False
            ), f"Запрос авторизации прошел с ошибкой {response.status_code}/n"
        return response.json()["access_token"]

    def get_headers(self):
        if not self._token:
            self._token = self.get_access_token()

        return {"Authorization": f"Bearer {self._token}"}

    def get_avito_ids(self, products):
        response = self.make_request(
            "autoload/v2/items/avito_ids",
            method="GET",
            params={"query": ",".join((product.sku for product in products))},
        )
        return response["items"]

    def get_statistic(self, date_from=None, date_to=None) -> str:
        response = self.make_request(
            f"stats/v1/accounts/{self.settings.AVITO_USER_ID}/items",
            method="POST",
            params={
                "dateFrom": (
                    date_from or datetime.datetime.now() - datetime.timedelta(days=1)
                ).strftime("%Y-%m-%d"),
                "dateTo": (date_to or datetime.datetime.now()).strftime("%Y-%m-%d"),
                "fields": ["uniqViews", "uniqContacts", "uniqFavorites"],
                "periodGrouping": "day",
            },
        )
        result = []
        for item in response["result"].get("items", []):
            result.append(
                AvitoStatsItem(
                    avito_id=item["itemId"],
                    points=[
                        AvitoStatsPoint(
                            date=point["date"],
                            contacts=point["uniqContacts"],
                            favorites=point["uniqContacts"],
                            views=point["uniqContacts"],
                        )
                        for point in item["stats"]
                    ],
                )
            )

        return result

    @backoff.on_exception(
        backoff.expo,
        (
            r.ReadTimeout,
            r.ConnectTimeout,
            r.Timeout,
            r.JSONDecodeError,
            r.ConnectionError,
        ),
        max_tries=8,
    )
    def make_request(self, path, *, method, params=None):
        _path = f"{self.BASE_URL}{path}"
        _params = (
            dict(params=params) or {}
            if method.upper() == "GET"
            else dict(json=params) or {}
        )

        _r = r.request(
            method,
            _path,
            headers=self.get_headers(),
            timeout=10.0,
            **_params,
        )
        if not _r.ok:
            if r.status_codes == 401:
                self._token = None
            logger.warning(_r.json())
            assert (
                False
            ), f"Запрос {method.upper()} {_path} прошел с ошибкой {_r.status_code}/n"
        return _r.json()


class AvitoStatsPoint(BaseModel):
    date: datetime.date
    contacts: int
    favorites: int
    views: int


class AvitoStatsItem(BaseModel):
    avito_id: int
    points: List[AvitoStatsPoint]