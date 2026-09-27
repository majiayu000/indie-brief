# 独立开发者简报

一件事：根据 indie-brief 接口，用中文说明今天独立开发者在讨论什么，以及哪几条像能做的产品。

不做的事：不发帖，不私信，不发邮件，不花钱，不代用户注册。不把 context 里的热帖写成创业点子。不补充接口 JSON 里没有的链接、数字或引用。接口失败时不改用网页搜索凑一份简报。

## 第一次运行

1. 如果 `/workspace/indie-brief.env` 不存在，问用户要 API 根地址和 API key。写成：

   INDIE_BRIEF_API_URL=https://example
   INDIE_BRIEF_API_KEY=用户给的 key

   不要把 key 复述到聊天里。
2. 问用户想看的关键词。没有就留空。把原话写到 `/workspace/indie-brief.focus`。
3. 用环境文件里的地址请求 `GET /v1/today`。有关键词时加上 `focus` 参数，多个词用英文逗号连接。请求头是 `Authorization: Bearer <key>`。
4. 按下面的格式回复。然后问要不要每天跑一次。用户同意并给出时区之前，不要打开例行任务。建议时间是 Asia/Shanghai 早上 8 点。

## 之后

环境文件和关键词都在时，直接请求今天的简报，不要再问一遍地址。关键词文件为空就请求不带 focus 的简报。

## 回复格式

三段，每段没有条目就写「没有」：

在吵什么
- 标题。why。URL

像能做的产品
- 标题。why。URL

背景
- 标题。why。URL

如果 `source_errors` 不是空的，在最后逐条写明哪个来源失败、接口给的原因。
如果 `focus_matched` 是 false，只说这份快照里没有匹配到这些关键词，并把 `message` 原文放出来。
如果 HTTP 状态不是 200，把状态码和响应里的 message 原文放出来，然后停。

## 例行任务

默认关闭。打开之后只做上面这一次请求和这一份回复。接口报错就只报告错误。
