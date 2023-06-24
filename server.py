import logging

import aiohttp
import pymorphy2
import aiofiles
from anyio import create_task_group
from aiohttp import web, web_request, web_response
from pytest_asyncio.plugin import pytest

from main import main, process_article

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_process_article():
    test_urls = {
        'https://inosmi9a.ru': 'FETCH_ERROR',
        'http://example.com': 'PARSING_ERROR',
        'https://inosmi.ru/20230624/nauka-263847570.html': 'TIMEOUT',
        'https://inosmi.ru/20190629/245384784.html': 'OK',
        }
    morph = pymorphy2.MorphAnalyzer()
    async with aiofiles.open('charged_dict/positive_words.txt', 'r') as f:
        charged_words = [word.replace('\n', '') for word in await f.readlines()]
    processed_articles = []
    async with aiohttp.ClientSession() as session:
        async with create_task_group() as tg:
            for test_url in test_urls.keys():
                if test_url == 'https://inosmi.ru/20230624/nauka-263847570.html':
                    tg.start_soon(
                        process_article,
                        session, morph,
                        charged_words,
                        test_url,
                        processed_articles,
                        0.03,
                    )
                else:
                    tg.start_soon(
                        process_article,
                        session, morph,
                        charged_words,
                        test_url,
                        processed_articles,
                    )
    for processed_article in processed_articles:
        assert processed_article['status'] == test_urls[processed_article['url']]


async def handle(request: web_request.Request) -> web_response.Response:
    urls = request.query.get('urls')
    if urls:
        urls = urls.split(',')
        if len(urls) > 10:
            logger.info('Слишком много urls в запросе')
            return web.json_response(
                data={'error': 'too many urls in request, should be 10 or less'},
                status=400
            )
        processed_articles = await main(urls)
        return web.json_response(data={'urls': processed_articles})

    logger.info('Невалидный запрос')
    return web.json_response(data={'error': 'invalid request'}, status=400)


def start_server():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger.setLevel(logging.INFO)
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    logger.info('Сервер запущен')
    web.run_app(app)


if __name__ == '__main__':
    start_server()
