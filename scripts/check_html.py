#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML 手册自检：结构闭合 / 单脚本 / 无外链依赖 / JS 语法 / 敏感信息 / 关键组件。

用法:
    python check_html.py "xxx_实操指导手册.html"

退出码 0 = 通过（可能有警告），1 = 有硬性问题。
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

TAGS = ["section", "table", "div", "details", "pre", "ul", "ol", "tbody", "thead", "tr", "td", "th", "p", "aside", "main", "header", "footer"]

SENSITIVE = [
    (r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{3,}", "疑似明文口令"),
    (r"(?i)(secret|token|api[_-]?key)\s*[:=]\s*['\"][^'\"]{6,}", "疑似明文密钥"),
    (r"0x4[A-Za-z0-9]{20,}", "疑似 Cloudflare Turnstile key"),
    (r"\b1[3-9]\d{9}\b", "疑似手机号"),
    (r"\b\d{17}[\dXx]\b", "疑似身份证号"),
]

REQUIRED_JS = ["localStorage", "addEventListener"]
REQUIRED_CSS_HINT = ["--accent", "@media"]


def strip_pre(code):
    """去掉明显是示例/占位的内容，避免误报"""
    code = re.sub(r"(?i)(xxxx+|your[_-]?key|示例|某账号|某明文口令|placeholder)", "", code)
    return code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    args = ap.parse_args()
    if not os.path.exists(args.path):
        sys.exit(f"[!] 文件不存在: {args.path}")

    raw = open(args.path, encoding="utf-8", errors="ignore").read()
    problems, warns, notes = [], [], []

    # 1) 基本体量
    notes.append(f"体积 {len(raw)/1024:.1f} KB，行数 {raw.count(chr(10))+1}")

    # 2) 标签闭合
    body = re.sub(r"<pre.*?</pre>", "", raw, flags=re.S)  # pre 里可能有转义标签
    for t in TAGS:
        o = len(re.findall(r"<" + t + r"(?=[\s>])", body))
        c = len(re.findall(r"</" + t + r">", body))
        if o != c:
            problems.append(f"标签不闭合 <{t}>: 开 {o} / 闭 {c}")

    # 3) 脚本与外链
    scripts = re.findall(r"<script([^>]*)>(.*?)</script>", raw, re.S)
    inline = [(a, b) for a, b in scripts if "src=" not in a]
    external = [a for a, _ in scripts if "src=" in a]
    if external:
        problems.append(f"存在外部脚本引用（手册要求零依赖）: {external[:3]}")
    if not inline:
        problems.append("没有内联 <script>，交互组件无法工作")
    notes.append(f"内联脚本 {len(inline)} 段")
    if re.search(r'<img[^>]+src="https?://', raw):
        warns.append("存在外链图片（离线打开会裂图）")
    if re.search(r'<link[^>]+href="http', raw):
        warns.append("存在外链样式/字体")

    # 4) JS 语法
    node = shutil.which("node")
    for i, (_, code) in enumerate(inline, 1):
        if not code.strip():
            continue
        if node:
            tmp = os.path.join(tempfile.gettempdir(), f"_chk_{os.getpid()}_{i}.js")
            open(tmp, "w", encoding="utf-8").write(code)
            r = subprocess.run([node, "--check", tmp], capture_output=True, text=True)
            os.remove(tmp)
            if r.returncode != 0:
                problems.append(f"内联脚本 #{i} 语法错误: {r.stderr.strip().splitlines()[:2]}")
            else:
                notes.append(f"内联脚本 #{i} 语法 OK")
        else:
            notes.append("未检测到 node，跳过 JS 语法检查")

    # 5) 关键组件
    for kw in REQUIRED_JS:
        if kw not in raw:
            warns.append(f"缺少交互关键词: {kw}")
    for kw in REQUIRED_CSS_HINT:
        if kw not in raw:
            warns.append(f"缺少样式关键词: {kw}")
    if "scroll-margin-top" not in raw and 'href="#s' in raw:
        warns.append("目录锚点跳转会被顶栏遮挡（建议给 section 加 scroll-margin-top）")

    # 6) 章节与锚点一致性
    sec_ids = re.findall(r'<section[^>]+id="([^"]+)"', raw)
    anchors = re.findall(r'href="#([^"]+)"', raw)
    missing = sorted({a for a in anchors if a.startswith("s") and a not in sec_ids})
    if missing:
        problems.append(f"目录里有失效锚点: {missing}")
    notes.append(f"章节 {len(sec_ids)} 个，锚点 {len(set(anchors))} 个")

    # 7) 敏感信息
    text = strip_pre(raw)
    for pat, label in SENSITIVE:
        hits = re.findall(pat, text)
        if hits:
            problems.append(f"{label} × {len(hits)}（请确认是示例占位而非真实凭据）")

    # 8) 排版卫生
    if raw.count("<h1") > 1:
        warns.append("出现多个 h1，建议只保留页面标题一个")
    if re.search(r"\.\.\.省略|略\)|<!--\s*TODO", raw):
        warns.append("存在省略/待补占位，交付前应补全")

    # 输出
    print("=" * 56)
    print(f"自检: {os.path.basename(args.path)}")
    print("=" * 56)
    for n in notes:
        print(f"  · {n}")
    for w in warns:
        print(f"  ! {w}")
    for p in problems:
        print(f"  ✗ {p}")
    print("-" * 56)
    if problems:
        print(f"结果: 未通过（{len(problems)} 项硬性问题，{len(warns)} 项警告）")
        return 1
    print(f"结果: 通过（{len(warns)} 项警告）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
