#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_slides.py — 从「已渲染的 slides 页面 DOM」里按顺序抽出全部画面并下载。

为什么需要它：
  slides（多段小视频 / 图文+视频混合）页面是 React SPA，curl 只能拿到空壳。
  必须先让无头浏览器渲染出真实 DOM：

    chrome --headless=new --disable-gpu --virtual-time-budget=15000 \
      --user-agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148" \
      --window-size=430,932 --dump-dom "https://v.douyin.com/xxxx/" > dom.html

  再用本脚本解析 dom.html。注意：
  1) 视频域名不固定（v5-default / v11-default / v26-default ...），不要写死；
  2) 一个作品可能是「图文 + 视频混合」，必须按 DOM 顺序同时抽 <video src> 与 <img src>；
  3) 图片去掉 `~tplv-...` 模板参数通常拿不到无水印原图，直接用水印版即可（分辨率已够读丝印/字幕）。

用法：
  python extract_slides.py dom.html -o ./material
输出：
  material/items.json      有序清单 [{index, type, url, file}]
  material/01.mp4|jpg ...   按画面顺序编号（不是按类型各自编号）
"""
import argparse
import html as htmllib
import json
import os
import re
import sys
import urllib.request

HDR = {
    "User-Agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                   "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"),
    "Referer": "https://www.douyin.com/",
}


def parse_items(dom: str):
    """按 DOM 顺序返回 [{type, url}]，同时兼容 video 与 image。"""
    parts = re.split(r'<div class="aweme-slides-swiper-item"', dom)
    items = []
    for chunk in parts[1:]:
        head = chunk[:2000]
        v = re.search(r'<video[^>]*src="(https?://[^"]+)"', head)
        if v:
            items.append({"type": "video", "url": htmllib.unescape(v.group(1))})
            continue
        # 图文项：取第一个图片（poster / gallery img 均可）
        for m in re.finditer(r'<img[^>]*src="(https?://[^"]+)"', head):
            u = htmllib.unescape(m.group(1))
            if any(k in u for k in ("douyinpic", "byteimg", "tos-cn", "bytetos")):
                items.append({"type": "image", "url": u})
                break
    # 兜底：没有 swiper 结构时，直接按出现顺序抓 video/img
    if not items:
        for m in re.finditer(r'<(video|img)[^>]*src="(https?://[^"]+)"', dom):
            u = htmllib.unescape(m.group(2))
            if "douyinpic" in u or "365yg" in u or "/video/tos/" in u:
                items.append({"type": "video" if m.group(1) == "video" else "image", "url": u})
    # 去重（同一条目可能因懒加载重复出现）
    seen, out = set(), []
    for it in items:
        if it["url"] in seen:
            continue
        seen.add(it["url"])
        out.append(it)
    return out


def meta(dom: str):
    d = {}
    m = re.search(r'name="description" content="(.*?)"', dom)
    if m:
        d["desc"] = htmllib.unescape(m.group(1))
    m = re.search(r"<title>(.*?)</title>", dom)
    if m:
        d["title"] = htmllib.unescape(m.group(1))
    return d


def fetch(url, timeout=120):
    req = urllib.request.Request(url, headers=HDR)
    return urllib.request.urlopen(req, timeout=timeout).read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dom", help="--dump-dom 保存下来的 HTML")
    ap.add_argument("-o", "--out", default="./material")
    ap.add_argument("--no-download", action="store_true")
    args = ap.parse_args()

    dom = open(args.dom, encoding="utf-8", errors="ignore").read()
    items = parse_items(dom)
    if not items:
        sys.exit("未解析到任何画面：确认 DOM 是浏览器渲染后的（含 aweme-slides-swiper-item 或 <video src>）")

    os.makedirs(args.out, exist_ok=True)
    n_img = sum(1 for i in items if i["type"] == "image")
    print(f"共 {len(items)} 个画面：{len(items) - n_img} 视频 + {n_img} 图片")
    print(json.dumps(meta(dom), ensure_ascii=False))

    for idx, it in enumerate(items, 1):
        ext = "mp4" if it["type"] == "video" else "jpg"
        fn = os.path.join(args.out, f"{idx:02d}.{ext}")
        it["index"] = idx
        it["file"] = os.path.basename(fn)
        if args.no_download:
            continue
        if os.path.exists(fn) and os.path.getsize(fn) > 3000:
            print(f"  {idx:02d} {it['type']} 已存在，跳过")
            continue
        try:
            data = fetch(it["url"])
            if len(data) < 3000:
                print(f"  {idx:02d} {it['type']} 内容过小（{len(data)}B），可能已过期")
                continue
            open(fn, "wb").write(data)
            print(f"  {idx:02d} {it['type']} {len(data)/1024:.0f} KB")
        except Exception as e:
            print(f"  {idx:02d} {it['type']} 失败：{e}")

    with open(os.path.join(args.out, "items.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    print(f"清单已写入 {os.path.join(args.out, 'items.json')}")


if __name__ == "__main__":
    main()
