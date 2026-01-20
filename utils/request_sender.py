"""
This module is responsible for sending HTTP requests using the requests library.
It provides a class `RequestSender` that encapsulates the functionality for making GET and POST requests with custom headers and error handling.
The class also includes a method for adding URL parameters to requests.
"""

import ssl
import urllib3
import requests
import requests.adapters
from requests.models import PreparedRequest


class CustomHttpAdapter(requests.adapters.HTTPAdapter):
    """Transport adapter" that allows us to use custom ssl_context."""

    def __init__(self, pool_connections=10, pool_maxsize=10, **kwargs):
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.options |= 0x4
        self.ssl_context = ctx
        super().__init__(
            pool_connections=pool_connections, pool_maxsize=pool_maxsize, **kwargs
        )

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        self.poolmanager = urllib3.poolmanager.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=self.ssl_context,
            **pool_kwargs,
        )


class RequestSender:
    HEADERS = {
        "User-Agent": "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4489.128 Safari/537.36"
    }

    def __init__(self, timeout=20, max_connections=100):
        self.timeout = timeout
        self.headers = self.HEADERS
        self.prepared_request = PreparedRequest()
        self.session = requests.Session()
        adapter = CustomHttpAdapter(
            pool_connections=max_connections, pool_maxsize=max_connections
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update(self.headers)

    def __make_request(
        self,
        method,
        url,
        cookies=None,
        data=None,
        json=None,
        params=None,
        headers=None,
        allow_redirects=True,
        err_info=None,
    ):
        res = None
        headers = {**self.headers, **(headers or {})}

        try:
            if method == "post":
                res = self.session.post(
                    url=url,
                    headers=headers,
                    cookies=cookies,
                    data=data,
                    json=json,
                    params=params,
                    allow_redirects=allow_redirects,
                    timeout=self.timeout,
                )
            elif method == "get":
                res = self.session.get(
                    url=url,
                    headers=headers,
                    cookies=cookies,
                    params=params,
                    allow_redirects=allow_redirects,
                    timeout=self.timeout,
                )
            else:
                raise ValueError(f"Unsupported request method: {method}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}") from e

        if res is None:
            raise ValueError("No response (possibly due to invalid URL parameters)")
        try:
            res.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise Exception(err_info) from e if err_info else e
        return res

    def post(
        self,
        url,
        cookies=None,
        data=None,
        json=None,
        params=None,
        headers=None,
        allow_redirects=True,
        err_info=None,
    ):
        return self.__make_request(
            "post",
            url=url,
            cookies=cookies,
            data=data,
            json=json,
            params=params,
            headers=headers,
            allow_redirects=allow_redirects,
            err_info=err_info,
        )

    def get(
        self,
        url,
        cookies=None,
        params=None,
        headers=None,
        allow_redirects=True,
        err_info=None,
    ):
        return self.__make_request(
            "get",
            url=url,
            cookies=cookies,
            params=params,
            headers=headers,
            allow_redirects=allow_redirects,
            err_info=err_info,
        )

    def add_url_params(self, url, params):
        self.prepared_request.prepare_url(url, params)
        return self.prepared_request.url
