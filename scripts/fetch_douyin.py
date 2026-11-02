#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音分享链接解析器：短链 -> 真实作品页 -> 原图/封面 + 文案 + 标签。

用法:
    python fetch_douyin.py "9.25 复制打开抖音… https://v.douyin.com/xxxx/ xxx:/" -o material
    python fetch_douyin.py https://v.douyin.com/xxxx/ --no-download

原理:
    1) 用移动端 UA 跟随 302，拿到 iesdouyin 分享页真实地址（含作品 id 与类型 note/video）
    2) 用搜索引擎 UA (Googlebot/Baiduspider) 重请求 —— 普通浏览器 UA 会被要求"在抖音内观看"
    3) SSR 版页面会内联所有原图的签名 URL；按出现顺序去重下载

只依赖标准库。仅供个人学习与素材整理，请遵守平台规则与著作权。
"""
import argparse
import html as htmllib
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
SPIDER_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"

SHORT_RE = re.compile(r"https?://v\.douyin\.com/[A-Za-z0-9_\-]+/?")
ID_RE = re.compile(r"/(?:share/)?(note|video|slides)/(\d{8,})")
IMG_RE = re.compile(r"https://p[0-9a-z\-]*\.douyinpic\.com/[^\"'\s\\)]+aweme-images[^\"'\s\\)]*")


def fetch(url, ua=SPIDER_UA, referer=None, timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        **({"Referer": referer} if referer else {}),
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        return r.geturl(), raw


def extract_link(text):
    m = SHORT_RE.search(text or "")
    if m:
        return m.group(0)
    m = re.search(r"v\.douyin\.com/[A-Za-z0-9_\-]+", text or "")
    if m:
        return "https://" + m.group(0)
    return None


def resolve(short_url):
    """跟随跳转，返回 (final_url, kind, item_id)"""
    try:
        final, _ = fetch(short_url, ua=MOBILE_UA)
    except urllib.error.HTTPError as e:
        final = e.headers.get("Location") or short_url
    except Exception as e:
        sys.exit(f"[!] 解析短链失败: {e}")
    m = ID_RE.search(final)
    if not m:
        sys.exit(f"[!] 未能从跳转地址里识别作品 id: {final[:160]}")
    return final, m.group(1), m.group(2)


def parse_meta(page):
    out = {}
    m = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]*)"', page)
    if m:
        out["description_meta"] = htmllib.unescape(m.group(1))
    m = re.search(r"<title>(.*?)</title>", page, re.S)
    if m:
        out["title"] = htmllib.unescape(m.group(1)).strip()
    m = re.search(r'rel="canonical"\s+href="([^"]+)"', page)
    if m:
        out["canonical"] = m.group(1)

    desc = out.get("description_meta", "")
    # 形如：<文案> - <作者>于<日期>发布在抖音，已经收获了N个喜欢…
    m = re.match(r"^(.*?)\s*-\s*(.+?)于(\d{8})发布在抖音，已经收获了([\d.]+[万亿]?)个喜欢", desc)
    if m:
        out["caption"] = m.group(1).strip()
        out["author"] = m.group(2).strip()
        out["date"] = m.group(3)
        out["likes"] = m.group(4)
    tags = re.findall(r"#([^\s#]+)", out.get("caption") or desc)
    out["tags"] = tags
    if out.get("caption"):
        # 标签从正文里剔除，只留纯文案
        out["caption_clean"] = re.sub(r"#[^\s#]+", "", out["caption"]).strip(" ：:，,")
    return out


def collect_images(page):
    """按出现顺序收集原图，用图片 id 去重（同一图有 webp/多尺寸变体）"""
    seen, urls = set(), []
    for m in IMG_RE.finditer(page):
        u = htmllib.unescape(m.group(0))
        km = re.search(r"tos-cn-i-[0-9a-z]+/([^~]+)", u)
        key = km.group(1) if km else u
        if key in seen:
            continue
        seen.add(key)
        urls.append((key, u))
    return urls


def collect_video(page):
    """视频类：尽力抓封面与直链（直链常带时效签名，可能失效）"""
    out = {}
    m = re.search(r'"cover"\s*:\s*"([^"]+)"', page)
    if m:
        out["cover"] = m.group(1).replace("\\u002F", "/")
    m = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', page)
    if m and "cover" not in out:
        out["cover"] = htmllib.unescape(m.group(1))
    m = re.search(r'"playApi"\s*:\s*"([^"]+)"', page)
    if m:
        out["play_api"] = m.group(1).replace("\\u002F", "/")
    m = re.search(r'<video[^>]+src="([^"]+)"', page)
    if m:
        out["video_src"] = htmllib.unescape(m.group(1))
    return out


def download(url, path, referer="https://www.douyin.com/"):
    req = urllib.request.Request(url, headers={"User-Agent": SPIDER_UA, "Referer": referer})
    with urllib.request.urlopen(req, timeout=40) as r:
        data = r.read()
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def main():
    ap = argparse.ArgumentParser(description="抖音分享链接 -> 原图 + 文案")
    ap.add_argument("text", help="分享文案或短链")
    ap.add_argument("-o", "--out", default="material", help="输出目录")
    ap.add_argument("--no-download", action="store_true", help="只解析元信息，不下载图片")
    args = ap.parse_args()

    link = extract_link(args.text)
    if not link:
        sys.exit("[!] 没找到 v.douyin.com 短链，请把分享文案整段贴进来")

    print(f"[1/4] 解析短链: {link}")
    final, kind, item_id = resolve(link)
    print(f"      类型={kind}  id={item_id}")
    print(f"      落地页={final[:120]}...")

    print("[2/4] 用搜索引擎 UA 请求分享页 ...")
    page = ""
    candidates = [
        f"https://www.iesdouyin.com/share/{kind}/{item_id}/",
        f"https://www.douyin.com/{kind}/{item_id}",
    ]
    for url in candidates:
        try:
            _, raw = fetch(url)
            text = raw.decode("utf-8", "ignore")
            if len(text) > 8000 and ("douyinpic" in text or "description" in text):
                page, final = text, url
                break
        except Exception as e:
            print(f"      × {url} -> {e}")
        time.sleep(0.4)
    if not page:
        sys.exit("[!] 三个入口都拿不到 SSR 数据，可能作品已删除/私密，或需要登录")

    meta = parse_meta(page)
    meta["kind"] = kind
    meta["item_id"] = item_id
    meta["share_url"] = link
    meta["final_url"] = final

    os.makedirs(args.out, exist_ok=True)
    saved = []

    if kind in ("note", "slides"):
        imgs = collect_images(page)
        meta["image_count"] = len(imgs)
        print(f"[3/4] 找到 {len(imgs)} 张原图")
        if not args.no_download:
            for i, (k, u) in enumerate(imgs, 1):
                ext = ".webp" if "webp" in u else ".jpg"
                fn = os.path.join(args.out, f"{i:02d}{ext}")
                try:
                    n = download(u, fn)
                    saved.append(fn)
                    print(f"      {fn}  {n/1024:.0f} KB")
                except Exception as e:
                    print(f"      × 第 {i} 张失败: {e}")
    else:
        v = collect_video(page)
        meta.update(v)
        print("[3/4] 视频类：只取封面，视频流请用客户端或 ffmpeg 抽帧")
        if v.get("cover") and not args.no_download:
            fn = os.path.join(args.out, "cover.jpg")
            try:
                download(v["cover"], fn)
                saved.append(fn)
            except Exception as e:
                print(f"      × 封面下载失败: {e}")

    meta["files"] = saved
    with open(os.path.join(args.out, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("[4/4] 元信息")
    for k in ("author", "date", "likes", "caption_clean"):
        if meta.get(k):
            print(f"      {k}: {meta[k]}")
    if meta.get("tags"):
        print(f"      tags: {' '.join('#'+t for t in meta['tags'])}")
    print(f"\n完成 -> {os.path.abspath(args.out)}")


if __name__ == "__main__":
    main()
