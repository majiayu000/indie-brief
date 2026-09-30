# indie-brief

只读的独立开发者简报。它把 TrendHunter 的一份快照收成三栏：讨论、产品、背景。Grok Bot 模板只转述这个接口返回的内容。

全站热度、HN 评论和 GitHub star 不是同一个尺度，所以按来源配额取，不把一条高分 Reddit 热帖排进「在吵什么」。

## 跑起来

需要 Python 3.12+、[uv](https://docs.astral.sh/uv/getting-started/installation/) 和一份 TrendHunter 简报快照；仓库不附带线上数据。

```bash
git clone https://github.com/majiayu000/indie-brief.git
cd indie-brief
uv sync
uv run indie-brief key
uv run indie-brief import-dir /path/to/trendhunter/apps/crawler/data/briefs
uv run indie-brief serve
```

`indie-brief key` 把一把 `ib_` 开头的 key 追加到 `data/keys`，这个目录不会进 Git。也可以用环境变量 `INDIE_BRIEF_API_KEYS`，多把 key 用逗号分隔。

没有 key 时服务拒绝启动。没有快照时 `GET /v1/today` 返回 404，不会用别的内容填。

```bash
curl -s -H "Authorization: Bearer ib_你的key" "http://127.0.0.1:8787/v1/today?focus=billing,付费"
```

默认只听 `127.0.0.1:8787`。要给 Grok Bot 的云电脑调用，把服务放到它能访问的地址上，再设 `INDIE_BRIEF_HOST=0.0.0.0`。本机的 `127.0.0.1` 云电脑访问不到。

容器：

```bash
docker build -t indie-brief .
docker run --rm -p 8787:8787 \
  -e INDIE_BRIEF_API_KEYS=ib_你的key \
  -v indie-brief-data:/data \
  indie-brief
```

快照仍要用 `import` 写进这个 volume。镜像里没有 TrendHunter 的数据。

## 在 Grok Bot 里用

新建一个 Bot，把 [Bot 模板](template/BOT.md)的正文交给它。第一次运行时它会问 API 地址和 key，并写到自己电脑上的 `/workspace/indie-brief.env`。例行任务默认关着，要你同意并给时区才每天跑。

本机 Grok Build 可以装插件。先让命令出现在 `PATH` 上：

```bash
uv tool install --editable .
```

环境变量要有 `INDIE_BRIEF_API_URL` 和 `INDIE_BRIEF_API_KEY`。插件目录是 [plugin/](plugin/)，使用说明在 [indie-brief 技能](plugin/skills/indie-brief/SKILL.md)。

官方模板市场是策展上架，这个仓库不会自动出现在那里。收费目前就是你自己发 key。这里没有支付页面。

## 接口

`GET /health` 不需要 key。

`GET /v1/today?focus=词1,词2` 需要 `Authorization: Bearer <key>`。

返回的 `arguments`、`products`、`context` 都来自已导入的快照。`focus` 对不上时三个列表是空的，`focus_matched` 为 false，同时仍返回 `source_errors`。
