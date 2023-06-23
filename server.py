from aiohttp import web, web_request


async def handle(request: web_request.Request):
    urls = request.query.get('urls')
    if urls:
        urls = urls.split(',')
        return web.json_response(data={'urls': urls})
    name = request.match_info.get('name', "Anonymous")
    text = "Hello, " + name
    return web.Response(text=text)


app = web.Application()
app.add_routes([web.get('/', handle),
                web.get('/{name}', handle)])


if __name__ == '__main__':
    web.run_app(app)
