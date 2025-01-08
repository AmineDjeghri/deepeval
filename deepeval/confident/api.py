from typing import Optional
import aiohttp
import requests
from enum import Enum

from deepeval.key_handler import KEY_FILE_HANDLER, KeyValues

DEEPEVAL_BASE_URL = "https://deepeval.confident-ai.com"
API_BASE_URL = "https://api.confident-ai.com"


class HttpMethods(Enum):
    GET = "GET"
    POST = "POST"
    DELETE = "DELETE"
    PUT = "PUT"


class Endpoints(Enum):
    DATASET_ENDPOINT = "/v1/dataset"
    TEST_RUN_ENDPOINT = "/v1/test-run"
    EVENT_ENDPOINT = "/v1/event"
    FEEDBACK_ENDPOINT = "/v1/feedback"
    PROMPT_ENDPOINT = "/v1/prompt"
    EVALUATE_ENDPOINT = "/evaluate"
    GUARD_ENDPOINT = "/guard"
    MULTIPLE_GUARD_ENDPOINT = "/guard-multiple"
    BASELINE_ATTACKS_ENDPOINT = "/generate-baseline-attacks"


class Api:
    def __init__(self, api_key: Optional[str] = None, base_url=None):
        if api_key is None:
            # get API key if none is supplied after you log in
            api_key = KEY_FILE_HANDLER.fetch_data(KeyValues.API_KEY)

        if not api_key:
            raise ValueError("Please provide a valid Confident AI API Key.")

        self.api_key = api_key
        self._headers = {
            "Content-Type": "application/json",
            # "User-Agent": "Python/Requests",
            "CONFIDENT_API_KEY": api_key,
        }
        self.base_api_url = base_url or API_BASE_URL

    @staticmethod
    def _http_request(
        method: str, url: str, headers=None, json=None, params=None
    ):
        session = requests.Session()
        return session.request(
            method=method,
            url=url,
            headers=headers,
            json=json,
            params=params,
            verify=True,  # SSL verification is always enabled
        )

    def send_request(
        self, method: HttpMethods, endpoint: Endpoints, body=None, params=None
    ):
        url = f"{self.base_api_url}{endpoint.value}"
        res = self._http_request(
            method=method.value,
            url=url,
            headers=self._headers,
            json=body,
            params=params,
        )

        if res.status_code == 200:
            try:
                return res.json()
            except ValueError:
                return res.text
        elif res.status_code == 409 and body:
            message = res.json().get("message", "Conflict occurred.")

            # Prompt the user for action
            user_input = (
                input(
                    f"{message} Would you like to overwrite it? [y/N] or change the alias [c]: "
                )
                .strip()
                .lower()
            )

            if user_input == "y":
                body["overwrite"] = True
                return self.send_request(method, endpoint, body)
            elif user_input == "c":
                new_alias = input("Enter a new alias: ").strip()
                body["alias"] = new_alias
                return self.send_request(method, endpoint, body)
            else:
                print("Aborted.")
                return None
        else:
            raise Exception(res.json().get("error", res.text))

    async def a_send_request(
        self, method: HttpMethods, endpoint: Endpoints, body=None, params=None
    ):
        url = f"{self.base_api_url}{endpoint.value}"
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method=method.value,
                url=url,
                headers=self._headers,
                json=body,
                params=params,
                ssl=True,  # SSL verification enabled
            ) as res:
                if res.status == 200:
                    try:
                        return await res.json()
                    except aiohttp.ContentTypeError:
                        return await res.text()
                elif res.status == 409 and body:
                    message = (await res.json()).get(
                        "message", "Conflict occurred."
                    )

                    user_input = (
                        input(
                            f"{message} Would you like to overwrite it? [y/N] or change the alias [c]: "
                        )
                        .strip()
                        .lower()
                    )

                    if user_input == "y":
                        body["overwrite"] = True
                        return await self.a_send_request(method, endpoint, body)
                    elif user_input == "c":
                        new_alias = input("Enter a new alias: ").strip()
                        body["alias"] = new_alias
                        return await self.a_send_request(method, endpoint, body)
                    else:
                        print("Aborted.")
                        return None
                else:
                    error_message = await res.json().get(
                        "error", await res.text()
                    )
                    raise Exception(error_message)
