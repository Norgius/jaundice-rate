from aiohttp import web, web_request

from main import main


async def handle(request: web_request.Request):
    urls = request.query.get('urls')
    if urls:
        urls = urls.split(',')
        if len(urls) > 10:
            return web.json_response(
                data={'error': 'too many urls in request, should be 10 or less'},
                status=400
            )
        processed_articles = await main(urls=urls)
        return web.json_response(data={'urls': processed_articles})

    return web.json_response(data={'error': 'invalid request'}, status=400)


app = web.Application()
app.add_routes([web.get('/', handle)])


if __name__ == '__main__':
    web.run_app(app)
