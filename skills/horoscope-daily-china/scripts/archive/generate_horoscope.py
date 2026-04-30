# -*- coding: utf-8 -*-
"""
每日星座运势生成器 - 天行数据完整版 V1.0
修复：Emoji 显示 + 文字截断 + 底部留白
"""

import requests
import json
import os
import sys
import io
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import argparse
import random

# 设置 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 导入本地星座数据模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from constellation_data import (
    CONSTELLATIONS,
    get_constellation_info,
    calculate_compatibility,
    get_fortune_level,
    get_all_constellations,
)

# ==================== 配置 ====================
# 天行数据 API 配置
TIANAPI_KEY = "1a2e33859936815860a475f5bc929b4b"
TIANAPI_STAR_URL = "https://apis.tianapi.com/star/index"
TIANAPI_PAIR_URL = "https://apis.tianapi.com/xingzuo/index"  # 正确的配对 API 地址

# 星座简称映射（天行数据 API 需要简称）
CONSTELLATION_SHORT = {
    "白羊座": "白羊",
    "金牛座": "金牛",
    "双子座": "双子",
    "巨蟹座": "巨蟹",
    "狮子座": "狮子",
    "处女座": "处女",
    "天秤座": "天秤",
    "天蝎座": "天蝎",
    "射手座": "射手",
    "摩羯座": "摩羯",
    "水瓶座": "水瓶",
    "双鱼座": "双鱼",
}

# 图片配置
WIDTH = 1080
HEIGHT = 1400
MARGIN = 50

# Unicode 符号（替代 Emoji）
SYMBOLS = {
    "star": "★",
    "medal1": "①",
    "medal2": "②",
    "medal3": "③",
    "heart": "♥",
    "circle": "●",
    "number": "№",
    "couple": "★",  # P0 修复：♥ 仍显示方框，改用 ★（最通用）
}

# 配色模板
TEMPLATES = {
    1: {
        "name": "星空紫",
        "bg": "#1A0A2E",
        "primary": "#9D4EDD",
        "secondary": "#FFD700",
        "text": "#FFFFFF",
        "accent": "#FF6B9D",
    },
    2: {
        "name": "海洋蓝",
        "bg": "#0A1628",
        "primary": "#4CC9F0",
        "secondary": "#B8E6FF",
        "text": "#FFFFFF",
        "accent": "#FFB347",
    },
    3: {
        "name": "玫瑰金",
        "bg": "#F8F0E6",
        "primary": "#D4AF37",
        "secondary": "#B76E79",
        "text": "#1A1A1A",
        "accent": "#FF6B6B",
    },
    4: {
        "name": "极简黑",
        "bg": "#1C1C1C",
        "primary": "#FF6B6B",
        "secondary": "#4ECDC4",
        "text": "#FFFFFF",
        "accent": "#FFE66D",
    },
    5: {
        "name": "温暖橙",
        "bg": "#FFF5E6",
        "primary": "#FF8C42",
        "secondary": "#F4D35E",
        "text": "#1A1A1A",
        "accent": "#FF6B6B",
    },
}


# ==================== API 调用 ====================
def get_tianapi_fortune(constellation):
    """调用天行数据星座运势 API"""
    params = {
        "key": TIANAPI_KEY,
        "astro": constellation,
    }
    
    try:
        response = requests.get(TIANAPI_STAR_URL, params=params, timeout=10)
        data = response.json()
        
        if data.get("code") == 200:
            result = data.get("result", {})
            list_data = result.get("list", [])
            
            fortune_data = {
                "name": constellation,
                "all": "75",
                "love": "75",
                "work": "75",
                "money": "75",
                "health": "75",
                "color": "",
                "number": "",
                "QFriend": "",
                "summary": "",
            }
            
            for item in list_data:
                item_type = item.get("type", "")
                content = item.get("content", "")
                
                if "综合指数" in item_type:
                    fortune_data["all"] = content.replace("%", "")
                elif "爱情指数" in item_type:
                    fortune_data["love"] = content.replace("%", "")
                elif "工作指数" in item_type:
                    fortune_data["work"] = content.replace("%", "")
                elif "财运指数" in item_type:
                    fortune_data["money"] = content.replace("%", "")
                elif "健康指数" in item_type:
                    fortune_data["health"] = content.replace("%", "")
                elif "幸运颜色" in item_type:
                    fortune_data["color"] = content
                elif "幸运数字" in item_type:
                    fortune_data["number"] = content
                elif "贵人星座" in item_type:
                    fortune_data["QFriend"] = content
                elif "今日概述" in item_type:
                    fortune_data["summary"] = content
            
            return fortune_data
        else:
            print(f"API 错误：{data.get('msg')}")
            return None
            
    except Exception as e:
        print(f"请求失败：{e}")
        return None


def get_tianapi_pair(constellation1, constellation2, use_random=True):
    """调用天行数据星座配对 API（接口 ID:42）- P0 修复：强制使用本地算法确保分数差异化"""
    
    # P0 修复：强制使用本地算法（避免 API 返回的 star_count 导致全部高分）
    local_result = calculate_compatibility(constellation1, constellation2)
    
    # 获取基础分数范围
    score_range = local_result.get("score_range", (70, 85))
    score_min, score_max = score_range
    
    # 在范围内随机选择分数（确保差异化）
    if use_random:
        score = str(random.randint(score_min, score_max))
    else:
        # 使用固定分数（基于星座名称哈希，确保可复现）
        hash_val = sum(ord(c) for c in constellation1 + constellation2)
        score = str(score_min + (hash_val % (score_max - score_min + 1)))
    
    # 5 档评价标题
    score_int = int(score)
    if score_int >= 90:
        pair_title = "天生一对"
    elif score_int >= 80:
        pair_title = "非常匹配"
    elif score_int >= 70:
        pair_title = "和谐配对"
    elif score_int >= 60:
        pair_title = "需要磨合"
    else:
        pair_title = "挑战较大"
    
    return {
        "sign1": constellation1,
        "sign2": constellation2,
        "score": score,
        "title": pair_title,
        "desc": local_result["desc"],
        "tag": local_result.get("tag", ""),
    }


def get_all_constellations_fortune_tianapi():
    """获取 12 星座的运势数据"""
    constellations = get_all_constellations()
    results = []
    
    print(f"正在获取 12 个星座的运势数据...")
    
    for i, cons in enumerate(constellations, 1):
        print(f"  [{i}/12] {cons}", end="\r")
        data = get_tianapi_fortune(cons)
        
        if data:
            results.append(data)
    
    print(f"\n✅ 成功获取 {len(results)} 个星座数据")
    return results


def get_popular_pairs():
    """获取热门星座配对（P0 修复：use_random=False 确保分数一致）"""
    pairs_config = [
        ("白羊座", "狮子座"),
        ("金牛座", "处女座"),
        ("双子座", "天秤座"),
        ("巨蟹座", "天蝎座"),
        ("狮子座", "射手座"),
        ("处女座", "摩羯座"),
    ]
    
    print(f"正在获取星座配对数据...")
    results = []
    
    for i, (sign1, sign2) in enumerate(pairs_config, 1):
        print(f"  [{i}/{len(pairs_config)}] {sign1}+{sign2}", end="\r")
        # P0 修复：use_random=False 确保分数可复现
        data = get_tianapi_pair(sign1, sign2, use_random=False)
        if data:
            results.append(data)
    
    print(f"\n✅ 成功获取 {len(results)} 个配对数据")
    return results


# ==================== 分数优化 ====================
def normalize_scores(fortune_data):
    """优化分数分布"""
    if not fortune_data:
        return fortune_data
    
    scores = [int(item.get("all", 75)) for item in fortune_data]
    sorted_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    
    rank_scores = {
        0: random.randint(88, 92),
        1: random.randint(82, 86),
        2: random.randint(78, 81),
        3: random.randint(74, 77),
        4: random.randint(71, 73),
        5: random.randint(68, 70),
        6: random.randint(66, 68),
        7: random.randint(64, 66),
        8: random.randint(62, 64),
        9: random.randint(60, 62),
        10: random.randint(58, 60),
        11: random.randint(55, 58),
    }
    
    for rank, idx in enumerate(sorted_indices):
        fortune_data[idx]["all"] = str(rank_scores[rank])
        base = rank_scores[rank]
        fortune_data[idx]["love"] = str(min(100, base + random.randint(-5, 10)))
        fortune_data[idx]["work"] = str(min(100, base + random.randint(-5, 10)))
        fortune_data[idx]["money"] = str(min(100, base + random.randint(-10, 5)))
        fortune_data[idx]["health"] = str(min(100, base + random.randint(-10, 5)))
    
    return fortune_data


# ==================== 图片生成 ====================
def get_font(size):
    """获取字体"""
    font_paths = [
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    
    return ImageFont.load_default()


def draw_text_wrapped(draw, text, y, font, color, left_margin, right_margin, line_spacing=None):
    """左对齐绘制文字（自动换行，保证不截断）- 修复截断问题"""
    if line_spacing is None:
        line_spacing = font.size + 6
    
    max_width = WIDTH - left_margin - right_margin
    # 按字符数估算换行（中文约每个字符 font.size*0.8 宽度）
    chars_per_line = max(10, int(max_width / (font.size * 0.75)))
    
    # 中文按字符换行
    lines = []
    current_line = ""
    
    for char in text:
        test_line = current_line + char
        if len(test_line) <= chars_per_line:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = char
    
    if current_line:
        lines.append(current_line)
    
    # 绘制多行（左对齐）
    current_y = y
    for line in lines:
        draw.text((left_margin, current_y), line, fill=color, font=font)
        current_y += line_spacing
    
    return current_y


def draw_text_centered(draw, text, y, font, color, max_width=None):
    """居中绘制文字（自动换行，不超出宽度）"""
    if max_width is None:
        max_width = WIDTH - MARGIN * 2 - 60  # 左右各留 30px 安全边距
    
    # 测量文字宽度
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    
    # 如果超出宽度，自动换行
    if text_width > max_width:
        # 按字符数估算换行
        chars_per_line = max(10, int(max_width / (font.size * 0.75)))
        lines = []
        current_line = ""
        
        for char in text:
            test_line = current_line + char
            if len(test_line) <= chars_per_line:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        
        if current_line:
            lines.append(current_line)
        
        # 绘制多行（每行居中对齐）
        current_y = y
        for line in lines:
            line_bbox = draw.textbbox((0, 0), line, font=font)
            line_width = line_bbox[2] - line_bbox[0]
            x = (WIDTH - line_width) // 2
            draw.text((x, current_y), line, fill=color, font=font)
            current_y += (line_bbox[3] - line_bbox[1]) + 6
        
        return current_y
    else:
        x = (WIDTH - text_width) // 2
        draw.text((x, y), text, fill=color, font=font)
        return y + (bbox[3] - bbox[1]) + 8


def generate_page1_merged(fortune_data, pair_data, template_id=1):
    """第 1 页（合并版）：封面 + 红榜 + 排名 + 配对 (3 对) + 今日开运 - P0/P1/P2 全修复"""
    template = TEMPLATES.get(template_id, TEMPLATES[1])
    
    img = Image.new('RGB', (WIDTH, HEIGHT), color=template["bg"])
    draw = ImageDraw.Draw(img)
    
    # === P1 修复：视觉层级优化 ===
    title_font = get_font(64)      # 主标题
    date_font = get_font(40)       # 日期
    weekday_font = get_font(40)    # 星期
    section_font = get_font(38)    # 红榜/排名标题 40→38
    pair_section_font = get_font(32)  # 配对标题（弱化）
    lucky_section_font = get_font(32) # 开运标题（弱化）
    normal_font = get_font(32)     # 红榜内容
    rank_font = get_font(28)       # 排名内容 30→28
    pair_font = get_font(32)       # 配对名
    score_font = get_font(26)      # 配对分数
    lucky_font = get_font(28)      # 今日开运内容
    small_font = get_font(24)      # 底部
    
    y = MARGIN - 5  # 起始位置
    
    # === 封面区 ===
    y = draw_text_centered(draw, f"{SYMBOLS['star']} 星座运势 {SYMBOLS['star']}", y, title_font, template["primary"])
    y += 10
    
    # 日期
    date = datetime.now().strftime("%Y年%m月%d日")
    weekday = datetime.now().strftime("%A")
    y = draw_text_centered(draw, date, y, date_font, template["text"])
    y = draw_text_centered(draw, weekday, y, weekday_font, template["secondary"])
    y += 12
    
    # 分隔线
    draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=template["primary"], width=3)
    y += 15
    
    # === 红榜 TOP3 ===
    y = draw_text_centered(draw, f"{SYMBOLS['star']} 今日红榜 TOP3", y, section_font, template["primary"])
    y += 10
    
    # P0 修复：确保使用排序后的数据
    sorted_data = sorted(fortune_data, key=lambda x: int(x.get("all", 0)), reverse=True)
    top3 = sorted_data[:3]
    medals = [SYMBOLS['medal1'], SYMBOLS['medal2'], SYMBOLS['medal3']]
    
    for i, data in enumerate(top3):
        name = data.get("name", "")
        score = data.get("all", "0")
        row_text = f"{medals[i]} {name}  {score}%"
        y = draw_text_centered(draw, row_text, y, normal_font, template["accent"] if i == 0 else template["text"])
        y += 8
    
    y += 12
    
    # 分隔线
    draw.line([(MARGIN + 50, y), (WIDTH - MARGIN - 50, y)], fill=template["secondary"], width=2)
    y += 15
    
    # === 12 星座完整排名（双列） ===
    y = draw_text_centered(draw, f"{SYMBOLS['star']} 12 星座完整排名", y, section_font, template["primary"])
    y += 10
    
    # P1 修复：双列布局优化（固定宽度对齐）
    left_x = MARGIN + 30
    right_x = WIDTH // 2 + 15
    col_y = y
    
    # 左列 1-6 名
    for i, data in enumerate(sorted_data[:6], 1):
        name = data.get("name", "")
        score = data.get("all", "0")
        
        # 前 3 名用强调色
        if i <= 3:
            color = template["accent"]
        else:
            color = template["text"]
        
        # P1 修复：固定宽度格式确保对齐
        row_text = f"{i:2d}. {name:4s}: {score:2s}%"
        draw.text((left_x, col_y), row_text, fill=color, font=rank_font)
        col_y += 24
    
    # 右列 7-12 名
    col_y = y
    for i, data in enumerate(sorted_data[6:12], 7):
        name = data.get("name", "")
        score = data.get("all", "0")
        row_text = f"{i:2d}. {name:4s}: {score:2s}%"
        draw.text((right_x, col_y), row_text, fill=template["text"], font=rank_font)
        col_y += 24
    
    y = col_y + 10
    
    # 分隔线
    draw.line([(MARGIN + 60, y), (WIDTH - MARGIN - 60, y)], fill=template["secondary"], width=2)
    y += 15
    
    # === 星座配对（精简为 3 对） ===
    # P1 修复：配对标题弱化（橙色）
    y = draw_text_centered(draw, f"{SYMBOLS['heart']} 精选配对", y, pair_section_font, template["accent"])
    y += 10
    
    # P0 修复：随机选择 3 对（避免全是 95 分）
    import random
    selected_pairs = random.sample(pair_data, min(3, len(pair_data)))
    
    for i, pair in enumerate(selected_pairs):
        sign1 = pair.get("sign1", "")
        sign2 = pair.get("sign2", "")
        score = pair.get("score", "75")
        title = pair.get("title", "和谐配对")
        tag = pair.get("tag", "")
        
        # 配对名称 + 标签
        if tag:
            pair_text = f"{sign1} 与 {sign2}  ·  {tag}"
        else:
            pair_text = f"{sign1} 与 {sign2}"
        y = draw_text_centered(draw, pair_text, y, pair_font, template["text"])
        
        # 分数和标题
        score_text = f"{score}分  {title}"
        y = draw_text_centered(draw, score_text, y, score_font, template["accent"])
        
        y += 18  # P1 修复：统一间距 18px
    
    y += 5
    
    # 分隔线
    draw.line([(MARGIN + 80, y), (WIDTH - MARGIN - 80, y)], fill=template["secondary"], width=2)
    y += 15
    
    # === 今日开运 ===
    # P1 修复：开运标题弱化（橙色）
    y = draw_text_centered(draw, f"{SYMBOLS['star']} 今日开运", y, lucky_section_font, template["accent"])
    y += 10
    
    if fortune_data:
        first = fortune_data[0]
        lucky_color = first.get("color", "")
        lucky_num = first.get("number", "")
        qfriend = first.get("QFriend", "")
        
        # 一行展示所有开运信息
        lucky_text = f"幸运色：{lucky_color}   |   幸运数字：{lucky_num}   |   速配星座：{qfriend}"
        y = draw_text_centered(draw, lucky_text, y, lucky_font, template["text"], max_width=WIDTH - MARGIN * 2 - 40)
    
    y += 15
    
    # P2 修复：互动引导上移，减少底部留白
    y = draw_text_centered(draw, "你的星座今天排第几？评论区见！", y, normal_font, template["primary"])
    
    # 底部（固定位置）
    bottom_y = HEIGHT - MARGIN - 20
    draw_text_centered(draw, "娱乐参考 切勿迷信", bottom_y, small_font, template["secondary"])
    
    return img


def generate_page2_detail1(fortune_data, template_id=1):
    """第 2 页：详细运势 1-4 名"""
    template = TEMPLATES.get(template_id, TEMPLATES[1])
    
    img = Image.new('RGB', (WIDTH, HEIGHT), color=template["bg"])
    draw = ImageDraw.Draw(img)
    
    # 字体优化（加大提升可读性）
    title_font = get_font(56)      # 52→56
    sign_font = get_font(48)       # 44→48
    index_font = get_font(32)      # 34→32（次要信息）
    summary_font = get_font(36)    # 34→36（提升可读性）
    small_font = get_font(28)      # 26→28
    
    y = MARGIN
    
    # 标题
    y = draw_text_centered(draw, f"{SYMBOLS['star']} 12 星座详细运势 (1/3)", y, title_font, template["primary"])
    y += 20
    
    # 分隔线
    draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=template["primary"], width=3)
    y += 20
    
    # 显示前 4 个星座
    sorted_data = sorted(fortune_data, key=lambda x: int(x.get("all", 0)), reverse=True)
    
    for i, data in enumerate(sorted_data[:4]):
        if y > HEIGHT - 100:
            break
        
        name = data.get("name", "")
        all_score = data.get("all", "0")
        love = data.get("love", "0")
        work = data.get("work", "0")
        money = data.get("money", "0")
        health = data.get("health", "0")
        summary = data.get("summary", "")
        
        # 星座名 + 综合指数（居中）
        header = f"{name}  综合：{all_score}%"
        y = draw_text_centered(draw, header, y, sign_font, template["primary"])
        y += 8
        
        # 详细指数（居中）
        details = f"爱情:{love}%   工作:{work}%   财运:{money}%   健康:{health}%"
        y = draw_text_centered(draw, details, y, index_font, template["text"])
        y += 8
        
        # 概述（左对齐，保证不截断）- 修复截断问题
        if summary:
            y = draw_text_wrapped(draw, summary, y, summary_font, template["secondary"], 
                                  left_margin=MARGIN + 40, right_margin=MARGIN + 40, 
                                  line_spacing=42)
        
        y += 15
        
        # 分隔线
        if i < 3:
            draw.line([(MARGIN + 60, y), (WIDTH - MARGIN - 60, y)], fill=template["secondary"], width=2)
            y += 15
    
    # 底部
    bottom_y = HEIGHT - MARGIN - 30
    draw_text_centered(draw, "娱乐参考 切勿迷信", bottom_y, small_font, template["secondary"])
    
    return img


def generate_page3_detail2(fortune_data, template_id=1):
    """第 3 页：详细运势 5-8 名"""
    template = TEMPLATES.get(template_id, TEMPLATES[1])
    
    img = Image.new('RGB', (WIDTH, HEIGHT), color=template["bg"])
    draw = ImageDraw.Draw(img)
    
    # 字体优化（加大提升可读性）
    title_font = get_font(56)      # 52→56
    sign_font = get_font(48)       # 44→48
    index_font = get_font(32)      # 34→32
    summary_font = get_font(36)    # 34→36
    small_font = get_font(28)      # 26→28
    
    y = MARGIN
    
    y = draw_text_centered(draw, f"{SYMBOLS['star']} 12 星座详细运势 (2/3)", y, title_font, template["primary"])
    y += 20
    
    draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=template["primary"], width=3)
    y += 20
    
    sorted_data = sorted(fortune_data, key=lambda x: int(x.get("all", 0)), reverse=True)
    
    for i, data in enumerate(sorted_data[4:8], 5):
        if y > HEIGHT - 100:
            break
        
        name = data.get("name", "")
        all_score = data.get("all", "0")
        love = data.get("love", "0")
        work = data.get("work", "0")
        money = data.get("money", "0")
        health = data.get("health", "0")
        summary = data.get("summary", "")
        
        header = f"{name}  综合：{all_score}%"
        y = draw_text_centered(draw, header, y, sign_font, template["primary"])
        y += 8
        
        details = f"爱情:{love}%   工作:{work}%   财运:{money}%   健康:{health}%"
        y = draw_text_centered(draw, details, y, index_font, template["text"])
        y += 8
        
        # 概述（左对齐，保证不截断）- 修复截断问题
        if summary:
            y = draw_text_wrapped(draw, summary, y, summary_font, template["secondary"], 
                                  left_margin=MARGIN + 40, right_margin=MARGIN + 40, 
                                  line_spacing=42)
        
        y += 15
        
        if i < 8:
            draw.line([(MARGIN + 60, y), (WIDTH - MARGIN - 60, y)], fill=template["secondary"], width=2)
            y += 15
    
    bottom_y = HEIGHT - MARGIN - 30
    draw_text_centered(draw, "娱乐参考 切勿迷信", bottom_y, small_font, template["secondary"])
    
    return img


def generate_page4_detail3(fortune_data, template_id=1):
    """第 4 页：详细运势 9-12 名"""
    template = TEMPLATES.get(template_id, TEMPLATES[1])
    
    img = Image.new('RGB', (WIDTH, HEIGHT), color=template["bg"])
    draw = ImageDraw.Draw(img)
    
    # 字体优化（加大提升可读性）
    title_font = get_font(56)      # 52→56
    sign_font = get_font(48)       # 44→48
    index_font = get_font(32)      # 34→32
    summary_font = get_font(36)    # 34→36
    small_font = get_font(28)      # 26→28
    
    y = MARGIN
    
    y = draw_text_centered(draw, f"{SYMBOLS['star']} 12 星座详细运势 (3/3)", y, title_font, template["primary"])
    y += 20
    
    draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=template["primary"], width=3)
    y += 20
    
    sorted_data = sorted(fortune_data, key=lambda x: int(x.get("all", 0)), reverse=True)
    
    for i, data in enumerate(sorted_data[8:12], 9):
        if y > HEIGHT - 100:
            break
        
        name = data.get("name", "")
        all_score = data.get("all", "0")
        love = data.get("love", "0")
        work = data.get("work", "0")
        money = data.get("money", "0")
        health = data.get("health", "0")
        summary = data.get("summary", "")
        
        header = f"{name}  综合：{all_score}%"
        y = draw_text_centered(draw, header, y, sign_font, template["primary"])
        y += 8
        
        details = f"爱情:{love}%   工作:{work}%   财运:{money}%   健康:{health}%"
        y = draw_text_centered(draw, details, y, index_font, template["text"])
        y += 8
        
        # 概述（左对齐，保证不截断）- 修复截断问题
        if summary:
            y = draw_text_wrapped(draw, summary, y, summary_font, template["secondary"], 
                                  left_margin=MARGIN + 40, right_margin=MARGIN + 40, 
                                  line_spacing=42)
        
        y += 15
        
        if i < 12:
            draw.line([(MARGIN + 60, y), (WIDTH - MARGIN - 60, y)], fill=template["secondary"], width=2)
            y += 15
    
    bottom_y = HEIGHT - MARGIN - 30
    draw_text_centered(draw, "娱乐参考 切勿迷信", bottom_y, small_font, template["secondary"])
    
    return img


def generate_page5_pairs(pair_data, fortune_data, template_id=1):
    """第 5 页：星座配对（精简版）- 移除今日开运，内容居中"""
    template = TEMPLATES.get(template_id, TEMPLATES[1])
    
    img = Image.new('RGB', (WIDTH, HEIGHT), color=template["bg"])
    draw = ImageDraw.Draw(img)
    
    # 字体优化
    title_font = get_font(56)      # 恢复大标题
    pair_font = get_font(38)       # 配对名
    score_font = get_font(32)      # 分数
    normal_font = get_font(30)     # 互动引导
    small_font = get_font(26)      # 底部
    
    # 计算内容总高度，实现垂直居中
    # 标题 + 分隔线 + 6 对配对 + 2 条分隔线 + 互动 + 底部
    content_height = 70 + 3 + 6 * 55 + 2 * 2 + 40 + 35  # 约 420px
    
    # 从中间开始绘制
    y = (HEIGHT - content_height) // 2
    
    # 标题（居中）
    y = draw_text_centered(draw, "星座配对速查", y, title_font, template["primary"])
    y += 25
    
    # 分隔线
    draw.line([(MARGIN, y), (WIDTH - MARGIN, y)], fill=template["primary"], width=3)
    y += 25
    
    # 显示 6 对配对（精简布局：名称 + 标签 + 分数 + 标题）
    for i, pair in enumerate(pair_data):
        sign1 = pair.get("sign1", "")
        sign2 = pair.get("sign2", "")
        score = pair.get("score", "75")
        title = pair.get("title", "和谐配对")
        tag = pair.get("tag", "")
        
        # 配对名称 + 标签（居中）
        if tag:
            pair_text = f"{sign1} 与 {sign2}  ·  {tag}"
        else:
            pair_text = f"{sign1} 与 {sign2}"
        y = draw_text_centered(draw, pair_text, y, pair_font, template["primary"])
        
        # 分数和标题（居中）
        score_text = f"{score}分  {title}"
        y = draw_text_centered(draw, score_text, y, score_font, template["accent"])
        
        y += 22  # 间距
        
        # 每 3 对后加分隔线
        if i == 2:
            draw.line([(MARGIN + 100, y), (WIDTH - MARGIN - 100, y)], fill=template["secondary"], width=2)
            y += 20
    
    # 分隔线
    draw.line([(MARGIN + 80, y), (WIDTH - MARGIN - 80, y)], fill=template["secondary"], width=2)
    y += 25
    
    # 互动引导（居中）
    y = draw_text_centered(draw, "你的星座排第几？评论区见！", y, normal_font, template["primary"])
    
    # 底部（固定位置）
    bottom_y = HEIGHT - MARGIN - 25
    draw_text_centered(draw, "娱乐参考 切勿迷信", bottom_y, small_font, template["secondary"])
    
    return img


# ==================== 发布文案 ====================
def generate_publish_text(fortune_data):
    """生成今日头条发布文案"""
    
    sorted_data = sorted(fortune_data, key=lambda x: int(x.get("all", 0)), reverse=True)
    top3 = sorted_data[:3]
    bottom3 = sorted_data[-3:]
    
    date = datetime.now().strftime("%Y年%m月%d日")
    
    title = f"【{date}星座运势】{top3[0].get('name')}运势爆棚！这 3 个星座今天要走大运了"
    
    content = f"""大家好，今天是{date}。一起来看看十二星座今日的运势如何吧！

🏆 今日红榜 TOP3:
1️⃣ {top3[0].get('name')} {top3[0].get('all')}%
2️⃣ {top3[1].get('name')} {top3[1].get('all')}%
3️⃣ {top3[2].get('name')} {top3[2].get('all')}%

⚠️ 黑榜提醒:
{bottom3[0].get('name')} ({bottom3[0].get('all')}%)、{bottom3[1].get('name')} ({bottom3[1].get('all')}%)、{bottom3[2].get('name')} ({bottom3[2].get('all')}%)
今日需低调行事，避免重大决策。

💡 今日开运:
幸运色：{top3[0].get('color', '未知')}
幸运数字：{top3[0].get('number', '?')}
速配星座：{top3[0].get('QFriend', '未知')}

你的星座今天排第几？欢迎在评论区留言分享！

#星座 #星座运势 #十二星座 #今日运势"""

    return title, content


# ==================== 主函数 ====================
def main():
    parser = argparse.ArgumentParser(description="Daily Horoscope Generator V1.0 Fixed")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"),
                        help="Date (YYYY-MM-DD)")
    parser.add_argument("--template", type=int, default=0, choices=[0, 1, 2, 3, 4, 5],
                        help="Template (0=auto, 1-5=specific)")
    parser.add_argument("--output", type=str, default="output",
                        help="Output directory")
    
    args = parser.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    
    print(f"\n📅 Date: {args.date}")
    
    # 获取运势数据
    fortune_data = get_all_constellations_fortune_tianapi()
    
    if not fortune_data:
        print("❌ Failed to get fortune data.")
        return
    
    # 优化分数分布
    print("正在优化分数分布...")
    fortune_data = normalize_scores(fortune_data)
    
    # 获取配对数据
    pair_data = get_popular_pairs()
    
    # Template selection
    if args.template == 0:
        day = int(args.date.split("-")[2])
        template_id = (day % 5) + 1
    else:
        template_id = args.template
    
    template_name = TEMPLATES.get(template_id, {}).get("name", "Unknown")
    print(f"🎨 Template: {template_name}")
    
    date_str = args.date.replace("-", "")
    
    # 生成 4 页图片（P1 合并版）
    pages = [
        ("封面 + 红榜 + 排名 + 配对 + 开运", generate_page1_merged),
        ("详细运势 1-4", generate_page2_detail1),
        ("详细运势 5-8", generate_page3_detail2),
        ("详细运势 9-12", generate_page4_detail3),
    ]
    
    for i, (name, gen_func) in enumerate(pages, 1):
        print(f"\n📸 Generating Page {i}: {name}...")
        if i == 1:
            img = gen_func(fortune_data, pair_data, template_id)
        else:
            img = gen_func(fortune_data, template_id)
        path = os.path.join(args.output, f"{date_str}_星座运势_p{i}.png")
        img.save(path, "PNG", quality=95)
        print(f"✅ Saved: {path}")
    
    # 生成发布文案
    print("\n📝 Generating publish text...")
    title, content = generate_publish_text(fortune_data)
    
    content_path = os.path.join(args.output, f"{date_str}_发布文案.txt")
    with open(content_path, "w", encoding="utf-8") as f:
        f.write(f"标题：{title}\n\n")
        f.write(f"正文:\n{content}\n")
    print(f"✅ Saved: {content_path}")
    
    print("\n" + "="*60)
    print("发布文案预览:")
    print("="*60)
    print(f"标题：{title}")
    print(f"\n正文:\n{content}")
    print("="*60)
    
    print("\n✅ All tasks completed!")
    print(f"\n📊 共生成 5 页图片 + 1 个发布文案")


if __name__ == "__main__":
    main()
