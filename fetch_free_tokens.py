#!/usr/bin/env python3
"""每天抓取主流 AI 模型的免费 token 资讯，生成 HTML 邮件"""

import os
import re
import json
from datetime import datetime
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

# 目标模型关键词
TARGET_MODELS = {
    'kimi': ['kimi', '月之暗面', 'moonshot'],
    'GLM': ['glm', '智谱', 'chatglm', 'bigmodel'],
    'DeepSeek': ['deepseek', '深度求索'],
    'Qwen': ['qwen', '通义', 'tongyi', 'alibaba'],
}


def fetch_github_readme(repo: str) -> str:
    """从 GitHub 获取仓库 README"""
    url = f"https://raw.githubusercontent.com/{repo}/main/README.md"
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; FreeTokenBot/1.0)',
        'Accept': 'text/plain,text/markdown'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        print(f"Failed to fetch {repo}: {e}")
    return ""


def fetch_github_readme_alt(repo: str) -> str:
    """尝试从 master 分支获取 README"""
    url = f"https://raw.githubusercontent.com/{repo}/master/README.md"
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; FreeTokenBot/1.0)',
        'Accept': 'text/plain,text/markdown'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        print(f"Failed to fetch {repo}: {e}")
    return ""


def search_github_repos(query: str, token: str = None) -> List[Dict]:
    """搜索 GitHub 上包含免费 token 信息的仓库"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; FreeTokenBot/1.0)',
        'Accept': 'application/vnd.github.v3+json'
    }
    if token:
        headers['Authorization'] = f'token {token}'
    
    url = "https://api.github.com/search/repositories"
    params = {
        'q': f'{query} free token',
        'sort': 'updated',
        'order': 'desc',
        'per_page': 5
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return data.get('items', [])
    except Exception as e:
        print(f"GitHub search failed for '{query}': {e}")
    return []


def extract_model_sections(readme: str) -> Dict[str, str]:
    """从 README 中提取各模型相关段落"""
    sections = {}
    
    for model_name, keywords in TARGET_MODELS.items():
        lines = readme.split('\n')
        relevant_lines = []
        in_section = False
        
        for line in lines:
            line_lower = line.lower()
            # 检查是否命中关键词
            if any(kw.lower() in line_lower for kw in keywords):
                in_section = True
                relevant_lines.append(line)
            elif in_section:
                # 如果遇到新的标题级别，停止收集
                if re.match(r'^#{1,4}\s', line):
                    # 检查是否仍然是同级或子级
                    if not any(kw.lower() in line_lower for kw in keywords):
                        in_section = False
                        if relevant_lines:
                            relevant_lines.append('')
                        continue
                if in_section:
                    relevant_lines.append(line)
        
        if relevant_lines:
            sections[model_name] = '\n'.join(relevant_lines).strip()
    
    return sections


def generate_html_email(sections: Dict[str, str], sources: List[str]) -> str:
    """生成 HTML 格式的邮件正文"""
    date_str = datetime.now().strftime('%Y年%m月%d日')
    
    cards_html = ''
    for model_name, content in sections.items():
        # 简单清理 markdown 标记
        clean_content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
        clean_content = re.sub(r'[*_~`]', '', clean_content)
        clean_content = clean_content.strip()[:500] + ('...' if len(clean_content) > 500 else '')
        
        cards_html += f"""
        <div style="background: #f8f9fa; border-left: 4px solid #6366f1; padding: 16px; margin: 12px 0; border-radius: 6px;">
            <h3 style="margin: 0 0 8px 0; color: #4f46e5; font-size: 18px;">🔹 {model_name}</h3>
            <pre style="white-space: pre-wrap; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; line-height: 1.6; color: #374151; margin: 0;">{clean_content}</pre>
        </div>
        """
    
    if not sections:
        cards_html = '<p style="color: #6b7280; font-style: italic;">今日暂无更新。</p>'
    
    sources_html = '<ul>' + ''.join(f'<li><a href="{s}" style="color: #6366f1;">{s}</a></li>' for s in sources) + '</ul>'
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; max-width: 700px; margin: 0 auto; padding: 20px; background: #ffffff; color: #1f2937;">
    <div style="text-align: center; margin-bottom: 24px;">
        <h1 style="color: #4f46e5; margin: 0; font-size: 28px;">🤖 每日免费 Token 资讯</h1>
        <p style="color: #6b7280; margin: 8px 0 0 0; font-size: 14px;">{date_str} · kimi / GLM / DeepSeek / Qwen</p>
    </div>
    
    <div style="background: #eef2ff; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
        <h2 style="color: #4338ca; margin: 0 0 12px 0; font-size: 20px;">📊 今日模型免费额度速览</h2>
        {cards_html}
    </div>
    
    <div style="border-top: 1px solid #e5e7eb; padding-top: 16px; margin-top: 24px;">
        <p style="color: #6b7280; font-size: 12px; margin: 0;">
            📡 数据来源：<br>
            {sources_html}
        </p>
        <p style="color: #9ca3af; font-size: 11px; margin: 12px 0 0 0; text-align: center;">
            自动生成于 GitHub Actions · 由 FreeTokenBot 驱动
        </p>
    </div>
</body>
</html>"""
    
    return html


def main():
    print(f"[{datetime.now()}] 开始抓取免费 token 资讯...")
    
    # 数据源
    sources = [
        'mnfst/awesome-free-llm-apis',
    ]
    source_urls = []
    all_sections = {}
    
    # 1. 从 awesome-free-llm-apis 抓取
    for repo in sources:
        print(f"正在获取 {repo} ...")
        readme = fetch_github_readme(repo) or fetch_github_readme_alt(repo)
        if readme:
            source_urls.append(f"https://github.com/{repo}")
            sections = extract_model_sections(readme)
            for model, content in sections.items():
                if model not in all_sections or len(content) > len(all_sections[model]):
                    all_sections[model] = content
    
    # 2. 用 GitHub API 搜索最新相关仓库
    github_token = os.environ.get('GITHUB_TOKEN')
    for model_name in TARGET_MODELS:
        repos = search_github_repos(model_name, github_token)
        for repo_data in repos:
            full_name = repo_data.get('full_name', '')
            if full_name and f"github.com/{full_name}" not in source_urls:
                source_urls.append(f"https://github.com/{full_name}")
    
    # 3. 生成 HTML 邮件
    html_content = generate_html_email(all_sections, source_urls[:8])
    
    # 4. 写入文件供 action-send-mail 使用
    with open('email_body.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 完成！共找到 {len(all_sections)} 个模型的资讯，{len(source_urls)} 个数据源")
    print(f"📄 邮件正文已写入 email_body.html")
    
    # 输出摘要到 stdout（方便调试）
    for model, content in all_sections.items():
        preview = content[:100].replace('\n', ' ')
        print(f"  {model}: {preview}...")


if __name__ == '__main__':
    main()
