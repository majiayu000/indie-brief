---
name: indie-brief
description: 读取 indie-brief 接口里已经导入的独立开发者简报。只转述接口返回的条目，不补充别的帖子，不发帖。
---

# 独立开发者简报

只使用 `today` 工具。`focus` 传用户保存的关键词，没有就留空。

工具返回的 JSON 是全部材料：

- `arguments`：今天值得看的讨论
- `products`：Product Hunt 和 GitHub 上像能做的产品
- `context`：全站热帖和新闻背景。不要把这里的帖子写成创业机会
- `source_errors`：抓取失败的来源。告诉用户这个来源失败了，不要说成今天没有讨论
- `focus_matched` 为 false 时，直接说没有匹配，不要改关键词再编一份

每条只写标题、`why` 和 URL。不要增加 JSON 里没有的链接。

不发帖，不私信，不代发邮件，不花钱。

例行任务默认关闭。用户明确同意并给出时区之后，才按天调用 `today`。接口报错时把错误原文告诉用户，不要改用网页搜索凑一份简报。

`INDIE_BRIEF_API_URL` 和 `INDIE_BRIEF_API_KEY` 从环境变量读取。没有就停下来问用户。不要把 key 写进回复。
