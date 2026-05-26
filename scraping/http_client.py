# scraping/http_client.py
import time
import logging
import requests

from fake_useragent import UserAgent
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from config.settings import REQUEST_DELAY_SECONDS

logger = logging.getLogger(__name__)


class HTTPClient:
    """
    Encapsula toda a lógica de fazer requisições HTTP de forma resiliente.

    Responsabilidade única: buscar o HTML de uma URL.
    Não sabe nada sobre parsing, modelos ou banco de dados.

    Padrão aplicado: Facade — esconde a complexidade de
    sessões, headers, retries e rate limiting atrás de
    uma interface simples: client.get(url) -> str.
    """

    def __init__(self):
        self._ua = UserAgent()
        self._session = requests.Session()
        self._configure_session()

    def _configure_session(self) -> None:
        """
        Configura headers padrão que simulam um browser real.
        Uma Session do requests reutiliza a conexão TCP (keep-alive),
        o que é mais eficiente e mais parecido com comportamento humano.
        """
        self._session.headers.update(
            {
                "User-Agent": self._ua.random,
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,image/webp,*/*;q=0.8"
                ),
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "DNT": "1",
            }
        )

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=3, max=20),
        retry=retry_if_exception_type(
            (requests.ConnectionError, requests.Timeout)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def get(self, url: str) -> str:
        """
        Busca o HTML de uma URL com retry automático.

        Rotaciona o User-Agent a cada requisição para
        dificultar a detecção de padrão pelo servidor.

        Returns:
            O HTML cru da página como string.

        Raises:
            requests.HTTPError: Para erros 4xx e 5xx após retries esgotados.
            requests.Timeout: Se o servidor não responder em tempo.
        """
        self._session.headers.update({"User-Agent": self._ua.random})

        logger.debug(f"[HTTPClient] GET {url}")

        response = self._session.get(url, timeout=15)
        response.raise_for_status()

        time.sleep(REQUEST_DELAY_SECONDS)

        return response.text

    def close(self) -> None:
        """Fecha a sessão HTTP e libera recursos de rede."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False