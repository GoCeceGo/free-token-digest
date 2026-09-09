#!/usr/bin/env python3
"""每日生成按模型分类的免费额度资讯链接邮件"""

import html
import re
from datetime import datetime
from typing import Dict, List, NamedTuple
import requests

SOURCE_REPO = "mnfst/awesome-free-llm-apis"
SOURCE_URL = f"https://github.com/{SOURCE_REPO}"

# 前四个是优先关注模型，后面是其他知名模型
TARGET_MODELS = {
    "Kimi": ["kimi", "月之暗面", "moonshot"],
    "GLM": ["glm", "智谱", "chatglm", "zhipu", "bigmodel"],
    "DeepSeek": ["deepseek", "深度求索"],
    "Qwen": ["qwen", "通义", "tongyi", "alibaba"],
    "GPT / OpenAI": ["gpt", "openai"],
    "Gemini": ["gemini"],
    "Llama": ["llama"],
    "Mistral": ["mistral", "ministral", "codestral"],
    "Gemma": ["gemma"],
    "Claude": ["claude", "anthropic"],
}


class Platform(NamedTuple):
    name: str
    key_url: str


def fetch_github_readme(repo: str) -> str:
    """从 GitHub 获取仓库 README，优先 main 分支，再尝试 master 分支。"""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; FreeTokenBot/1.0)",
        "Accept": "text/plain,text/markdown",
    }
    for branch in ("main", "master"):
        url = f"https://raw.githubusercontent.com/{repo}/{branch}/README.md"
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                return response.text
        except requests.RequestException as error:
            print(f"获取 {url} 失败：{error}")
    return ""


def parse_platform_sections(readme: str) -> List[Dict[str, str]]:
    """解析 README 中的 ### 平台小节。"""
    sections: List[Dict[str, str]] = []
    current: Dict[str, str] | None = None

    for line in readme.splitlines():
        match = re.match(r"^### \[([^\]]+)\]\(([^)]+)\)", line)
        if match:
            if current:
                sections.append(current)
            title, url = match.groups()
            current = {"title": title, "url": url, "body": ""}
            continue

        if current:
            if line.startswith("## ") and not line.startswith("### "):
                sections.append(current)
                current = None
                continue
            current["body"] += line + "\n"

    if current:
        sections.append(current)

    return sections


def model_matches(cell: str, keywords: List[str]) -> bool:
    cell_lower = cell.lower()
    return any(keyword.lower() in cell_lower for keyword in keywords)


def collect_platform_links(readme: str) -> Dict[str, List[Platform]]:
    """按目标模型收集包含免费额度表格的平台链接。"""
    links: Dict[str, List[Platform]] = {name: [] for name in TARGET_MODELS}
    seen: Dict[str, set[str]] = {name: set() for name in TARGET_MODELS}

    for section in parse_platform_sections(readme):
        platform_name = section["title"]
        for model_name, keywords in TARGET_MODELS.items():
            matched = False
            for line in section["body"].splitlines():
                if not line.startswith("|"):
                    continue
                cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
                if len(cells) < 5:
                    continue
                model_cell = cells[0]
                if set(model_cell) <= {"-", " ", ":"}:
                    continue
                if model_matches(model_cell, keywords):
                    matched = True
                    break

            if matched and platform_name not in seen[model_name]:
                links[model_name].append(
                    Platform(platform_name, section["url"])
                )
                seen[model_name].add(platform_name)

    return links


def render_email(links: Dict[str, List[Platform]]) -> str:
    """生成简洁的 HTML 邮件正文。"""
    date_text = datetime.now().strftime("%Y年%m月%d日")
    cards = []

    for model_name, platforms in links.items():
        if platforms:
            items = "".join(
                f"""
                <li style="margin: 8px 0;">
                    <span style="color: #4338ca; font-weight: 600;">{html.escape(platform.name)}</span>
                    <span style="color: #9ca3af;">·</span>
                    <a href="{html.escape(platform.key_url)}" style="color: #6366f1;">获取 API Key</a>
                </li>"""
                for platform in platforms
            )
            status = f"{len(platforms)} 个相关平台"
        else:
            items = '<li style="color: #6b7280;">今日未找到明确条目。</li>'
            status = "暂无条目"

        cards.append(
            f"""
            <div style="background: #f9fafb; border-left: 4px solid #6366f1; border-radius: 8px; padding: 16px; margin: 16px 0;">
                <h2 style="margin: 0 0 4px 0; font-size: 18px; color: #312e81;">{html.escape(model_name)}</h2>
                <p style="margin: 0 0 8px 0; font-size: 12px; color: #6b7280;">{html.escape(status)}</p>
                <ul style="margin: 0; padding-left: 20px; font-size: 14px; color: #374151;">{items}</ul>
            </div>"""
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif; max-width: 680px; margin: 0 auto; padding: 24px; background: #ffffff; color: #1f2937;">
    <h1 style="margin: 0; font-size: 24px; color: #4338ca;">每日免费 Token 额度入口</h1>
    <p style="margin: 8px 0 20px 0; font-size: 13px; color: #6b7280;">{date_text} · Kimi · GLM · DeepSeek · Qwen 及其他知名模型</p>

    <p style="margin: 0 0 8px 0; font-size: 14px; color: #374151;">
        以下为按模型汇总的免费额度相关平台。平台名称仅作展示；如需了解额度详情，请通过右侧“获取 API Key”访问平台官网，或自行访问平台官网查询。
    </p>

    {''.join(cards)}

    <p style="border-top: 1px solid #e5e7eb; margin-top: 24px; padding-top: 12px; font-size: 12px; color: #6b7280;">
        汇总来源：<a href="{SOURCE_URL}" style="color: #6366f1;">awesome-free-llm-apis</a>
    </p>
</body>
</html>"""


def main() -> None:
    print(f"[{datetime.now()}] 开始生成免费 Token 资讯链接...")

    readme = fetch_github_readme(SOURCE_REPO)
    if not readme:
        raise RuntimeError("无法获取上游 README，终止发送，避免发送空邮件")

    links = collect_platform_links(readme)
    email_html = render_email(links)

    with open("email_body.html", "w", encoding="utf-8") as file:
        file.write(email_html)

    print("✅ 完成！按模型分类的链接邮件已生成")
    for model_name, platforms in links.items():
        print(f"  {model_name}: {len(platforms)} 个平台")
        for platform in platforms:
            print(f"    - {platform.name}")


if __name__ == "__main__":
    main()
