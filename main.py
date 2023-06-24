import asyncio
import logging
from typing import Union
from enum import Enum
from time import monotonic

import aiohttp
import pymorphy2
import aiofiles
import async_timeout
from anyio import create_task_group

from adapters.exceptions import ArticleNotFound
from adapters.inosmi_ru import sanitize
from text_tools import split_by_words, calculate_jaundice_rate

logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'
    PARSING_ERROR = 'PARSING_ERROR'
    TIMEOUT = 'TIMEOUT'


async def fetch(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def process_article(session: aiohttp.client.ClientSession,
                          morph: pymorphy2.analyzer.MorphAnalyzer,
                          charged_words: list[str],
                          url: str,
                          processed_articles: list,
                          timeout: Union[int, float] = 3):
    try:
        async with async_timeout.timeout(timeout):
            html = await fetch(session, url)
        text = sanitize(html, True)

        start = monotonic()
        async with split_by_words(morph, text) as words:
            words_count = len(words)
            score = calculate_jaundice_rate(words, charged_words)
        status = ProcessingStatus.OK.value
        analysis_time = monotonic() - start
        logger.info(f'Анализ закончен за {analysis_time} сек')

    except aiohttp.ClientError:
        status = ProcessingStatus.FETCH_ERROR.value
        words_count, score = None, None
    except ArticleNotFound:
        status = ProcessingStatus.PARSING_ERROR.value
        words_count, score = None, None
    except asyncio.exceptions.TimeoutError:
        status = ProcessingStatus.TIMEOUT.value
        words_count, score = None, None

    results = {
        'url': url,
        'status': status,
        'words_count': words_count,
        'score': score,
    }
    processed_articles.append(results)


async def main(urls: list[str]) -> dict:
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger.setLevel(logging.INFO)
    processed_articles = []
    morph = pymorphy2.MorphAnalyzer()
    async with aiofiles.open('charged_dict/positive_words.txt', 'r') as f:
        charged_words = [word.replace('\n', '') for word in await f.readlines()]
    async with aiohttp.ClientSession() as session:
        async with create_task_group() as tg:
            for url in urls:
                tg.start_soon(
                    process_article,
                    *(session, morph, charged_words, url, processed_articles,)
                )
    return processed_articles
