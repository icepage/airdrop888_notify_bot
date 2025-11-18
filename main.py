import re
from config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_PASSWORD,
    REDIS_GUID_PREFIX,
    REDIS_GUID_TTL,
    wecom_url,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID
)
import feedparser
from loguru import logger
import redis
import time
from utils.consts import status_key, exception_key_ttl
from utils.tools import (
    send_wecom
)
import requests
import traceback
from bs4 import BeautifulSoup
from html import unescape

# 定义需要过滤的关键词
FILTER_KEYWORDS = ["新空投通知", "空投预报", "空投即将开始", "空投更新"]

# 图标映射表 - 将原始图标替换为新图标
EMOJI_MAPPING = {
    "🚀": "✈️",
    "📛": "🏷️",
    "📅": "📆",
    "⚡": "💫",
    "📡": "📢",
    "⏰": "🕐",
    "🎯": "🎪",
    "📊": "📈",
    "💵": "💰",
    "💎": "💠",
    "📄": "📃",
    "🔗": "🔐",
    "🔥": "⭐",
    "⚠️": "🔔",
}

def replace_emojis(text):
    """替换文本中的emoji"""
    for old_emoji, new_emoji in EMOJI_MAPPING.items():
        text = text.replace(old_emoji, new_emoji)
    return text


def html_to_telegram_html(html_content):
    """
    将HTML内容转换为Telegram支持的HTML格式

    Telegram支持的HTML标签：
    - <b>, <strong> : 粗体
    - <i>, <em> : 斜体
    - <u>, <ins> : 下划线
    - <s>, <strike>, <del> : 删除线
    - <code> : 等宽字体
    - <pre> : 预格式化文本
    - <a href=""> : 链接
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # 替换不支持的标签
    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        tag.name = 'b'

    # 处理br标签
    for br in soup.find_all('br'):
        br.replace_with('\n')

    # 处理链接
    for a in soup.find_all('a'):
        href = a.get('href', '')
        if href:
            # 确保链接格式正确
            a['href'] = href

    # 移除不支持的标签，但保留内容
    for tag in soup.find_all(['div', 'p', 'span']):
        tag.unwrap()

    # 获取处理后的HTML
    result = str(soup)

    # 清理多余的换行
    result = re.sub(r'\n{3,}', '\n\n', result)

    # 解码HTML实体
    result = unescape(result)

    return result.strip()

def filter_and_modify_rss(feed_entries):
    """
    过滤RSS条目并修改内容

    参数:
        feed_entries: feedparser解析后的entries列表

    返回:
        list: 过滤并修改后的条目列表
    """
    filtered_entries = []

    for entry in feed_entries:
        title = entry.get("title", "")

        # 检查title是否包含需要过滤的关键词
        should_filter = any(keyword in title for keyword in FILTER_KEYWORDS)

        if should_filter:
            # 修改description内容
            description = entry.get("description", "")

            # 1. 替换URL
            modified_description = description.replace(
                "https://alpha123.uk",
                "https://airdrop888.top"
            )

            # 2. 替换emoji图标
            modified_description = replace_emojis(modified_description)

            # 3. 转换为Telegram支持的HTML格式
            modified_description = html_to_telegram_html(modified_description)

            # 创建修改后的条目副本
            modified_entry = entry.copy()
            modified_entry['description'] = modified_description

            filtered_entries.append(modified_entry)

    return filtered_entries


def forward_to_channel(entry, telegram_bot_token, telegram_chat_id, proxies: str=None):
    """
    将修改后的内容转发到Telegram频道

    参数:
        entry: RSS条目对象
        telegram_bot_token: Telegram Bot Token
        telegram_chat_id: 目标频道的Chat ID

    返回:
        bool: 发送是否成功
    """
    try:
        # 直接使用修改后的HTML description
        message = entry.get('description', '').strip()

        # 如果消息为空，跳过
        if not message:
            print("消息内容为空，跳过发送")
            return False

        # 发送到Telegram
        telegram_api_url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": telegram_chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }

        response = requests.post(telegram_api_url, json=payload, proxies=proxies, timeout=10)
        response.raise_for_status()

        return response.json().get('ok', False)

    except Exception as e:
        traceback.print_exc()

try:
    # 引入代理
    from config import proxy
except ImportError:
    logger.info("未配置代理")
    proxy = None


# 初始化 Redis 客户端
redis_client = redis.StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    password=REDIS_PASSWORD,
    decode_responses=True
)

def fetch_and_process(rss_url, proxies: str=None):

    if proxies:
        response = requests.get(rss_url, proxies=proxies, timeout=10)
        response.raise_for_status()

        # 使用 feedparser 解析内容
        feed = feedparser.parse(response.content)
    else:
        feed = feedparser.parse(rss_url)

    if not hasattr(feed, 'entries') or not feed.entries:
        logger.info("未获取到RSS条目")
        return

    # 过滤并修改RSS条目
    filtered_entries = filter_and_modify_rss(feed.entries)
    logger.info(f"过滤后获得 {len(filtered_entries)} 条符合条件的消息")

    for entry in filtered_entries:
        logger.info(entry)
        guid = entry.get("id")
        if not id:
            continue

        redis_key = f"{REDIS_GUID_PREFIX}{guid}"
        if redis_client.exists(redis_key):
            logger.info(guid+"已执行过, 跳过")
            continue

        logger.info(f"检测到新消息：{entry.get('title', 'N/A')}")
        # 转发到Telegram频道
        success = forward_to_channel(entry, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, proxies=proxies)

        if success:
            logger.info(f"执行完成, 开始写入缓存")
            # 写入Redis缓存
            redis_client.set(redis_key, "1", ex=REDIS_GUID_TTL)
        else:
            logger.info(f"消息转发失败")

        # 避免请求过快
        time.sleep(2)

def main():
    try:
        redis_client.set(status_key, 1)
        from config import rss_url
        fetch_and_process(rss_url, proxies=proxy)
    except Exception as e:
        traceback.print_exc()
        exception_key = str(e)[:20]
        if not redis_client.get(exception_key):
            redis_client.set(exception_key, "1", ex=exception_key_ttl)
            send_wecom(wecom_url, f"执行任务失败，失败原因为{exception_key}")
    finally:
        redis_client.set(status_key, 0)

if __name__ == "__main__":
    main()