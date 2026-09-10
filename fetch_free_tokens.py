#!/usr/bin/env python3
"""Generate a daily multi-source digest of free LLM API entry points."""

import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Set, Tuple
from urllib.parse import urlsplit, urlunsplit

import requests

SOURCES = [
    {
        "name": "awesome-free-llm-apis",
        "repo": "mnfst/awesome-free-llm-apis",
        "url": "https://github.com/mnfst/awesome-free-llm-apis",
    },
    {
        "name": "free-llm-api-resources",
        "repo": "jtig37/free-llm-api-resources",
        "url": "https://github.com/jtig37/free-llm-api-resources",
    },
    {
        "name": "FREE-LLM-API-Provider",
        "repo": "CYBIRD-D/FREE-LLM-API-Provider",
        "url": "https://github.com/CYBIRD-D/FREE-LLM-API-Provider",
    },
]

TARGET_MODELS = {
    "Kimi": ["kimi", "月之暗面", "moonshot"],
    "GLM": ["glm", "智谱", "chatglm", "zhipu", "bigmodel", "z.ai"],
    "DeepSeek": ["deepseek", "深度求索"],
    "Qwen": ["qwen", "通义", "tongyi", "alibaba"],
    "GPT / OpenAI": ["gpt", "openai"],
    "Gemini": ["gemini"],
    "Llama": ["llama"],
    "Mistral": ["mistral", "ministral", "codestral"],
    "Gemma": ["gemma"],
    "Claude": ["claude", "anthropic"],
}

HISTORY_FILE = Path("data/digest_history.json")

# Curated details make free-tier terms easier to understand than upstream links alone.
DEFAULT_PLATFORM_DETAILS = {
    "free_quota": "未能确认长期免费额度",
    "quota_unit": "请以平台官网为准",
    "key_url": "",
    "key_location": "请自行访问平台官网",
    "pricing_url": "请自行访问平台官网",
    "notes": "可能需要注册、实名认证或绑定支付方式；未确认前请谨慎操作",
}
PLATFORM_DETAILS = {
    "https://developers.cloudflare.com/workers-ai/platform/pricing/#llm-model-pricing": {
        "free_quota": "免费版每日约 10,000 Neurons，用完后需付费",
        "quota_unit": "Neurons，不是直接显示 token",
        "key_url": "https://dash.cloudflare.com/profile/api-tokens",
        "key_location": "Cloudflare Dashboard → API Tokens",
        "pricing_url": "https://developers.cloudflare.com/workers-ai/platform/pricing/#llm-model-pricing",
        "notes": "需要 Account ID + API Token",
    },
}
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FreeTokenBot/2.0)",
    "Accept": "text/plain,text/markdown",
}


class Platform(NamedTuple):
    name: str
    key_url: str
    source: str
    models: tuple[str, ...]


def normalize_url(url: str) -> str:
    """Normalize a URL for stable history comparison."""
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def canonical_url(url: str) -> str:
    """Collapse known duplicate platform links into one canonical entry."""
    normalized = normalize_url(url)
    if normalized.startswith("https://developers.cloudflare.com/workers-ai") or normalized == (
        "https://dash.cloudflare.com/profile/api-tokens"
    ):
        return "https://developers.cloudflare.com/workers-ai/platform/pricing/#llm-model-pricing"
    return normalized


def strip_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def fetch_github_readme(repo: str) -> str:
    """Fetch a README through the GitHub API, then raw.githubusercontent.com."""
    api_url = f"https://api.github.com/repos/{repo}/readme"
    headers = dict(HTTP_HEADERS)
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    urls = [api_url]
    urls.extend(
        f"https://raw.githubusercontent.com/{repo}/{branch}/README.md"
        for branch in ("main", "master")
    )

    for url in urls:
        try:
            request_headers = dict(headers)
            if "api.github.com" in url:
                request_headers["Accept"] = "application/vnd.github.raw"
            response = requests.get(url, headers=request_headers, timeout=20)
            if response.status_code == 200 and response.text.strip():
                return response.text
            print(f"获取 {url} 失败：HTTP {response.status_code}")
        except requests.RequestException as error:
            print(f"获取 {url} 失败：{error}")
    return ""


def markdown_sections(readme: str) -> List[Tuple[str, str, str]]:
    """Parse `### [title](url)` sections from a Markdown README."""
    sections: List[Tuple[str, str, str]] = []
    current: Tuple[str, str, str] | None = None

    for line in readme.splitlines():
        match = re.match(r"^### \[([^\]]+)\]\(([^)]+)\)", line)
        if match:
            if current:
                sections.append(current)
            title, url = match.groups()
            current = (strip_html(title), url, "")
            continue

        if current:
            if line.startswith("## ") and not line.startswith("### "):
                sections.append(current)
                current = None
                continue
            current = (current[0], current[1], current[2] + line + "\n")

    if current:
        sections.append(current)
    return sections


def model_matches(value: str, keywords: Iterable[str]) -> bool:
    value = value.lower()
    return any(keyword.lower() in value for keyword in keywords)


def parse_awesome(readme: str, source_name: str) -> List[Platform]:
    results: List[Platform] = []
    for name, url, body in markdown_sections(readme):
        for line in body.splitlines():
            if not line.startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 4 or set(cells[0]) <= {"-", " ", ":"}:
                continue
            matched_models = tuple(
                model_name
                for model_name, keywords in TARGET_MODELS.items()
                if model_matches(cells[0], keywords)
            )
            if matched_models:
                results.append(Platform(name, url, source_name, matched_models))
                break
    return results


def parse_jtig(readme: str, source_name: str) -> List[Platform]:
    """Parse the provider/model HTML table in jrtig37/free-llm-api-resources."""
    results: List[Platform] = []
    current_name = ""
    current_url = ""

    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", readme, flags=re.I | re.S):
        links = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', row, flags=re.I | re.S)
        if links:
            current_url, link_text = links[0]
            current_name = strip_html(link_text)
        if not current_name or not current_url:
            continue

        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.I | re.S)
        cell_text = " ".join(strip_html(cell) for cell in cells)
        if not cell_text or set(cell_text) <= {"-", " ", ":"}:
            continue
        matched_models = tuple(
            model_name
            for model_name, keywords in TARGET_MODELS.items()
            if model_matches(cell_text, keywords)
        )
        if matched_models:
            results.append(Platform(current_name, current_url, source_name, matched_models))
    return results


def parse_cybird(readme: str, source_name: str) -> List[Platform]:
    """Parse Markdown platform sections and model tables."""
    results: List[Platform] = []
    current_name = ""
    current_url = ""
    current_body: List[str] = []

    def flush() -> None:
        nonlocal current_body, current_name
        body = "\n".join(current_body)
        current_body = []
        if not current_name or not current_url:
            return
        if current_name.startswith("~~") and current_name.endswith("~~"):
            return
        current_name = current_name.replace("~~", "").strip()
        matched_models: tuple[str, ...] = ()
        body_text = strip_html(body)
        for model_name, keywords in TARGET_MODELS.items():
            if model_matches(body_text, keywords):
                matched_models += (model_name,)
        if not matched_models:
            for line in body.splitlines():
                if not line.startswith("|"):
                    continue
                cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
                if len(cells) < 2 or set(cells[0]) <= {"-", " ", ":"}:
                    continue
                matched_models += tuple(
                    model_name
                    for model_name, keywords in TARGET_MODELS.items()
                    if model_matches(cells[0], keywords)
                )
                if matched_models:
                    break
        if matched_models:
            results.append(Platform(current_name, current_url, source_name, matched_models))

    for line in readme.splitlines():
        if line.startswith("### "):
            flush()
            current_name = strip_html(line[4:])
            current_url = ""
            continue

        if current_name:
            if line.startswith("## ") and not line.startswith("### "):
                flush()
                current_name = ""
                current_url = ""
                continue
            if not current_url:
                match = re.search(r"https?://[^\s<>)\]]+", line)
                if match:
                    current_url = match.group(0).rstrip(".,;，。；")
            current_body.append(line)

    flush()
    return results


PARSERS = {
    "mnfst/awesome-free-llm-apis": parse_awesome,
    "jtig37/free-llm-api-resources": parse_jtig,
    "CYBIRD-D/FREE-LLM-API-Provider": parse_cybird,
}


def collect_platforms(source_results: List[Tuple[str, str, List[Platform]]]) -> Tuple[Dict[str, List[dict]], List[dict]]:
    by_model: Dict[str, List[dict]] = {name: [] for name in TARGET_MODELS}
    platform_by_url: Dict[str, dict] = {}
    active_source_names = {source["name"] for source in SOURCES}

    # A URL can appear under several models. Merge source attribution globally.
    for source_name, _, platforms in source_results:
        for platform in platforms:
            for model_name in platform.models:
                normalized = canonical_url(platform.key_url)
                key = f"{model_name}::{normalized}"
                if key not in platform_by_url:
                    platform_by_url[key] = {
                        "model": model_name,
                        "name": platform.name,
                        "key_url": canonical_url(platform.key_url),
                        "sources": set(),
                    }
                platform_by_url[key]["sources"].add(source_name)

    for item in platform_by_url.values():
        item["sources"] = sorted(
            source for source in item["sources"] if source in active_source_names
        )
        by_model[item["model"]].append(item)

    for platforms in by_model.values():
        platforms.sort(key=lambda item: (item["name"].lower(), normalize_url(item["key_url"])))

    source_summary = []
    for source_name, repo, platforms in source_results:
        source_summary.append(
            {
                "name": source_name,
                "repo": repo,
                "platform_entries": len(platforms),
                "ok": bool(platforms),
            }
        )
    return by_model, source_summary


def read_history() -> dict | None:
    if not HISTORY_FILE.exists():
        return None
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"读取历史记录失败：{error}")
        return None


def platform_urls(by_model: Dict[str, List[dict]]) -> Set[str]:
    return {canonical_url(item["key_url"]) for platforms in by_model.values() for item in platforms}


def render_email(
    by_model: Dict[str, List[dict]],
    source_summary: List[dict],
    old_urls: Set[str] | None,
    first_run: bool,
) -> str:
    date_text = datetime.now(timezone.utc).astimezone().strftime("%Y年%m月%d日")
    current_urls = platform_urls(by_model)
    new_urls = set() if old_urls is None else current_urls - old_urls
    removed_urls = set() if old_urls is None else old_urls - current_urls
    all_platform_count = len(current_urls)
    cards = []

    for model_name, platforms in by_model.items():
        if platforms:
            items = []
            for platform in platforms:
                is_new = canonical_url(platform["key_url"]) in new_urls
                new_badge = (
                    '<span style="display:inline-block; margin-left:6px; padding:1px 6px; border-radius:999px; background:#dcfce7; color:#166534; font-size:11px; font-weight:700;">NEW</span>'
                    if is_new
                    else ""
                )
                sources = "、".join(html.escape(source) for source in platform["sources"])
                detail = PLATFORM_DETAILS.get(platform["key_url"], DEFAULT_PLATFORM_DETAILS)
                pricing_value = (
                    f'<a href="{html.escape(detail["pricing_url"])}" style="color:#6366f1;">pricing 链接</a>'
                    if detail["pricing_url"].startswith("http")
                    else detail["pricing_url"]
                )
                details = [
                    ("免费额度", detail["free_quota"]),
                    ("额度形式", detail["quota_unit"]),
                    ("获取 Key", detail["key_location"]),
                    ("计费说明", pricing_value),
                    ("注意事项", detail["notes"]),
                ]
                details_html = "".join(
                    f"""
                            <div style="margin-top: 4px; font-size: 12px; color: #4b5563;">
                                <span style="color:#6b7280;">{label}：</span>{value}
                            </div>"""
                    for label, value in details
                )
                items.append(
                    f"""
                    <li style="margin: 12px 0;">
                        <div>
                            <span style="color: #4338ca; font-weight: 600;">{html.escape(platform['name'])}</span>{new_badge}
                            <span style="color: #9ca3af;">·</span>
                            {f'<a href="{html.escape(detail["key_url"])}" style="color: #6366f1;">平台入口 / 获取 Key</a>' if detail["key_url"] else '<span style="color:#6b7280;">详情请自行访问平台官网</span>'}
                        </div>
                        {details_html}
                        <div style="margin-top: 4px; font-size:11px; color:#9ca3af;">来源：{sources}</div>
                    </li>"""
                )
            items_html = "".join(items)
            status = f"{len(platforms)} 个相关入口"
        else:
            items_html = '<li style="color: #6b7280;">今日未找到明确条目。</li>'
            status = "暂无条目"

        cards.append(
            f"""
            <div style="background: #f9fafb; border-left: 4px solid #6366f1; border-radius: 8px; padding: 16px; margin: 16px 0;">
                <h2 style="margin: 0 0 4px 0; font-size: 18px; color: #312e81;">{html.escape(model_name)}</h2>
                <p style="margin: 0 0 8px 0; font-size: 12px; color: #6b7280;">{html.escape(status)}</p>
                <ul style="margin: 0; padding-left: 20px; font-size: 14px; color: #374151;">{items_html}</ul>
            </div>"""
        )

    if first_run:
        change_text = "这是多来源版的首次运行，今天先建立基线；明天开始会明确标记新增入口。"
        change_color = "#92400e"
    elif new_urls or removed_urls:
        change_text = f"今日新增 {len(new_urls)} 个入口；移除 {len(removed_urls)} 个入口。"
        change_color = "#166534"
    else:
        change_text = "今日上游列表没有新增或移除入口。这类汇总源通常不会每天都有变化，邮件会继续保留全量入口，并从明天起标记变化。"
        change_color = "#4b5563"

    source_links = []
    for source in source_summary:
        source_repo = next(item["url"] for item in SOURCES if item["name"] == source["name"])
        state = "可用" if source["ok"] else "无匹配或异常"
        source_links.append(
            f'<a href="{html.escape(source_repo)}" style="color:#6366f1;">{html.escape(source["name"])}</a>'
            f'<span style="color:#9ca3af;">（{state}）</span>'
        )
    source_text = "、".join(source_links)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif; max-width: 680px; margin: 0 auto; padding: 24px; background: #ffffff; color: #1f2937;">
    <h1 style="margin: 0; font-size: 24px; color: #4338ca;">每日免费 Token 额度入口</h1>
    <p style="margin: 8px 0 20px 0; font-size: 13px; color: #6b7280;">{date_text} · {all_platform_count} 个去重入口 · Kimi / GLM / DeepSeek / Qwen 及其他模型</p>

    <div style="background:#eef2ff; border-left:4px solid #6366f1; padding:12px 14px; border-radius:8px; color:{change_color}; font-size:14px;">
        {change_text}
    </div>

    <p style="margin:16px 0 8px 0; font-size:14px; color:#374151;">以下条目按“免费额度、额度形式、获取 Key、计费说明、注意事项”展示；无法确认免费额度的平台会明确标注，避免误导。</p>
    {''.join(cards)}

    <p style="border-top: 1px solid #e5e7eb; margin-top: 24px; padding-top: 12px; font-size: 12px; color: #6b7280;">
        汇总来源：{source_text}
    </p>
</body>
</html>"""


def main() -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] 开始生成多来源免费 Token 资讯...")

    source_results: List[Tuple[str, str, List[Platform]]] = []
    for source in SOURCES:
        readme = fetch_github_readme(source["repo"])
        if not readme:
            print(f"⚠️ 未获取到 {source['name']}")
            source_results.append((source["name"], source["repo"], []))
            continue
        platforms = PARSERS[source["repo"]](readme, source["name"])
        source_results.append((source["name"], source["repo"], platforms))
        print(f"  来源 {source['name']}: 解析 {len(platforms)} 条候选记录")

    if not any(platforms for _, _, platforms in source_results):
        raise RuntimeError("所有来源均未解析到有效平台，终止发送，避免发送空邮件")

    by_model, source_summary = collect_platforms(source_results)
    old_history = read_history()
    old_urls = None if old_history is None else set(old_history.get("urls", []))
    first_run = old_history is None

    email_html = render_email(by_model, source_summary, old_urls, first_run)
    Path("email_body.html").write_text(email_html, encoding="utf-8")

    # Build a stable history after rendering, so tomorrow's run can compute changes.
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    history = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "urls": sorted(platform_urls(by_model)),
        "models": by_model,
    }
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("✅ 完成！多来源去重邮件已生成")
    for model_name, platforms in by_model.items():
        print(f"  {model_name}: {len(platforms)} 个入口")
        for platform in platforms:
            print(f"    - {platform['name']} ({', '.join(platform['sources'])})")


if __name__ == "__main__":
    main()
