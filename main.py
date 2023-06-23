from enum import Enum
from adapters.exceptions import ArticleNotFound

import aiohttp
import asyncio
import pymorphy2
import aiofiles
from anyio import create_task_group

from adapters.inosmi_ru import sanitize
from text_tools import split_by_words, calculate_jaundice_rate

TEST_ARTICLES = [
        'https://inosmi.ru/20230619/raketa-263752174.html',
        'https://inosmi.ru/20190629/245384784.html',
        'https://inosmi.ru/20221231/nauka-259263272.html',
        'http://example.com',
        'https://inosmi.ru/20230611/antropologiya-263558745.html',
        'https://inosmi.ru/20230521/egipet-262991012.html'
]


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'


async def fetch(session: aiohttp.ClientSession, url: str):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def process_article(session, morph, charged_words, url, processed_articles):
    try:
        html = await fetch(session, url)
        status = ProcessingStatus.OK.value
        text = sanitize(html, True)
        words = split_by_words(morph, text)
        words_count = len(words)
        score = calculate_jaundice_rate(words, charged_words)
    except (aiohttp.ClientError, ArticleNotFound):
        status = ProcessingStatus.FETCH_ERROR.value
        words_count, score = None, None
    results = {
        'url': url,
        'status': status,
        'words_count': words_count,
        'score': score
    }
    processed_articles.append(results)


async def main():
    processed_articles = []
    morph = pymorphy2.MorphAnalyzer()
    async with aiofiles.open('charged_dict/positive_words.txt', 'r') as f:
        charged_words = [word.replace('\n', '') for word in await f.readlines()]
    async with aiohttp.ClientSession() as session:
        async with create_task_group() as tg:
            for url in TEST_ARTICLES:
                tg.start_soon(
                    process_article,
                    *(session, morph, charged_words, url, processed_articles)
                )
    print(processed_articles)


asyncio.run(main())
