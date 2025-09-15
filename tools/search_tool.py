import asyncio
import pandas as pd
from bilibili_api import search, video, Credential
from bilibili_api.search import SearchObjectType
from datetime import datetime
import time
import re
import html
import aiohttp
import json
import xml.etree.ElementTree as ET
from crewai.tools import BaseTool
from typing import Optional,ClassVar


class BilibiliSearchTool(BaseTool):
    name: str = "B站视频数据抓取工具"
    description: str = "抓取B站搜索结果的视频数据，包括列表信息、详情和弹幕内容"

    # 1. 声明为类变量（Pydantic 不会拦截）
    HEADERS: ClassVar[dict] = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.bilibili.com/'
    }

    def __init__(self):
        super().__init__()
        # self.HEADERS = {
        #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        #     'Referer': 'https://www.bilibili.com/'
        # }

    def _run(self, keyword: str, max_videos: Optional[int] = 10,
             comment_pages: Optional[int] = 2, max_danmaku: Optional[int] = 50) -> str:
        """
        抓取B站搜索结果的视频数据

        Args:
            keyword: 搜索关键词
            max_videos: 最大视频数量 (默认10)
            comment_pages: 评论页数 (默认2)
            max_danmaku: 最大弹幕数 (默认50)

        Returns:
            str: 执行结果信息
        """
        # 运行异步主函数
        result = asyncio.run(self.main_async(keyword, max_videos, comment_pages, max_danmaku))
        return result

    async def main_async(self, keyword: str, max_videos: int,
                         comment_pages: int, max_danmaku: int) -> str:
        """异步主函数"""
        all_video_list_data = []
        all_video_detail_data = []
        all_danmaku_data = []

        # 获取多页结果以确保有足够的数据
        page = 1
        total_videos = 0

        while total_videos < max_videos:
            print(f"正在获取第 {page} 页搜索结果...")
            search_result = await self.fetch_search_results(keyword, page=page, page_size=20)

            if not search_result or 'result' not in search_result:
                print(f"第 {page} 页未获取到搜索结果")
                break

            video_list = search_result['result']
            if not video_list:
                print("没有更多视频了")
                break

            print(f"第 {page} 页获取到 {len(video_list)} 个视频")

            # 遍历每个视频，获取列表数据和详情数据
            for v in video_list:
                if total_videos >= max_videos:
                    break

                # 提取视频列表数据
                bvid = v.get('bvid')
                if not bvid:
                    continue

                video_url = f"https://www.bilibili.com/video/{bvid}"
                duration = v.get('duration')
                duration_formatted = self.format_duration(duration)

                # 转换发布时间戳
                pubdate = v.get('pubdate')
                if pubdate:
                    try:
                        publish_date = datetime.fromtimestamp(pubdate).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        publish_date = "未知"
                else:
                    publish_date = "未知"

                # 清理标题
                raw_title = v.get('title', '无标题')
                clean_title_text = self.clean_title(raw_title)

                video_list_data = {
                    "视频地址": video_url,
                    "播放量": v.get('play', 0),
                    "评论数": v.get('review', 0),
                    "视频时长": duration_formatted,
                    "视频标题": clean_title_text,
                    "UP主昵称": v.get('author', '未知'),
                    "UP主主页链接": f"https://space.bilibili.com/{v.get('mid', '')}",
                    "视频发布日期": publish_date,
                    "BV号": bvid
                }
                all_video_list_data.append(video_list_data)

                # 获取视频详情数据
                print(f"正在获取视频详情: {clean_title_text}")
                detail_data = await self.fetch_video_detail_direct(bvid, comment_pages, max_danmaku)

                if detail_data:
                    # 为每条评论创建单独的记录
                    comments = detail_data.pop('comments', [])
                    if comments:
                        for comment in comments:
                            comment_record = detail_data.copy()
                            comment_record.update(comment)
                            all_video_detail_data.append(comment_record)
                        print(f"视频 '{clean_title_text}' 获取了 {len(comments)} 条评论")
                    else:
                        # 如果没有评论，也添加一条记录
                        detail_data['comment_content'] = "暂无评论"
                        detail_data['comment_like'] = 0
                        detail_data['comment_time'] = "未知"
                        all_video_detail_data.append(detail_data)
                        print(f"视频 '{clean_title_text}' 没有评论")

                    # 为每条弹幕创建单独的记录
                    danmaku = detail_data.pop('danmaku', [])
                    if danmaku:
                        for dm in danmaku:
                            dm_record = {
                                "bvid": detail_data['bvid'],
                                "video_title": clean_title_text,
                                "danmaku_content": dm['content'],
                                "danmaku_time": dm['time'],
                                # "danmaku_type": dm['type'],
                                # "danmaku_size": dm['size'],
                                # "danmaku_color": dm['color'],
                                "danmaku_send_time": dm['send_time']
                            }
                            all_danmaku_data.append(dm_record)
                        print(f"视频 '{clean_title_text}' 获取了 {len(danmaku)} 条弹幕")
                    else:
                        print(f"视频 '{clean_title_text}' 没有弹幕")
                else:
                    # 如果获取详情失败，添加空数据
                    empty_detail = {
                        "bvid": bvid,
                        "summary": "获取失败",
                        "like": 0,
                        "coin": 0,
                        "favorite": 0,
                        "share": 0,
                        "danmaku_count": 0,
                        "comment_content": "获取失败",
                        "comment_like": 0,
                        "comment_time": "未知"
                    }
                    all_video_detail_data.append(empty_detail)
                    print(f"视频 '{clean_title_text}' 详情获取失败")

                total_videos += 1
                # 添加延迟，避免请求过于频繁
                await asyncio.sleep(1)

            page += 1
            # 页间延迟
            await asyncio.sleep(2)

        print(f"总共获取了 {total_videos} 个视频")

        # 保存数据到固定文件名
        self.save_data_to_fixed_files(all_video_list_data, all_video_detail_data, all_danmaku_data, keyword)

        return f"成功抓取 {total_videos} 个视频数据。列表数据保存到 'b站列表数据.csv'，详情数据保存到 'b站详情数据.csv'，弹幕数据保存到 'b站弹幕数据.csv'"

    def save_data_to_fixed_files(self, list_data, detail_data, danmaku_data, keyword):
        """保存数据到固定文件名"""
        # 将数据转换为DataFrame
        df_list = pd.DataFrame(list_data)
        df_detail = pd.DataFrame(detail_data) if detail_data else pd.DataFrame()
        df_danmaku = pd.DataFrame(danmaku_data) if danmaku_data else pd.DataFrame()

        # 使用固定文件名保存数据
        df_list.to_csv("b站列表数据.csv", index=False, encoding='utf-8-sig')
        print("列表数据已保存到 'b站列表数据.csv'")

        if not df_detail.empty:
            df_detail.to_csv("b站详情数据.csv", index=False, encoding='utf-8-sig')
            print("详情数据已保存到 'b站详情数据.csv'")

        if not df_danmaku.empty:
            df_danmaku.to_csv("b站弹幕数据.csv", index=False, encoding='utf-8-sig')
            print("弹幕数据已保存到 'b站弹幕数据.csv'")

        # 打印统计信息
        if not df_detail.empty:
            print(f"\n总共获取了 {len(df_detail)} 条评论")

        if not df_danmaku.empty:
            print(f"总共获取了 {len(df_danmaku)} 条弹幕")

    # 以下是原有的工具函数，保持不变
    def clean_title(self, title):
        """清理标题中的HTML标签和特殊字符"""
        if not title:
            return "无标题"
        clean = re.sub(r'<[^>]+>', '', title)
        clean = html.unescape(clean)
        return clean

    def format_duration(self, duration):
        """格式化视频时长"""
        # 保持原有实现
        if isinstance(duration, int):
            minutes, seconds = divmod(duration, 60)
            hours, minutes = divmod(minutes, 60)
            if hours > 0:
                return f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                return f"{minutes}:{seconds:02d}"
        elif isinstance(duration, str):
            if re.match(r'^\d+:\d+', duration):
                return duration
            else:
                try:
                    seconds = int(duration)
                    minutes, seconds = divmod(seconds, 60)
                    hours, minutes = divmod(minutes, 60)
                    if hours > 0:
                        return f"{hours}:{minutes:02d}:{seconds:02d}"
                    else:
                        return f"{minutes}:{seconds:02d}"
                except:
                    return "未知"
        else:
            return "未知"

    async def fetch_search_results(self, keyword: str, page: int = 1, page_size: int = 50):
        """获取B站搜索结果的异步函数"""
        try:
            result = await search.search_by_type(
                keyword=keyword,
                search_type=SearchObjectType.VIDEO,
                page=page,
                page_size=page_size
            )
            return result
        except Exception as e:
            print(f"获取搜索结果时出错: {e}")
            return None

    async def fetch_comments(self, aid: int, max_pages: int = 2):
        """获取视频评论的异步函数"""
        comments = []
        page = 1

        async with aiohttp.ClientSession() as session:
            while page <= max_pages:
                try:
                    comment_url = f"https://api.bilibili.com/x/v2/reply?type=1&oid={aid}&sort=2&pn={page}&ps=20"
                    async with session.get(comment_url, headers=self.HEADERS) as response:
                        if response.status == 200:
                            comment_data = await response.json()
                            if comment_data['code'] == 0 and 'replies' in comment_data['data']:
                                replies = comment_data['data']['replies']
                                if not replies:
                                    break

                                for reply in replies:
                                    comments.append({
                                        "comment_content": reply['content']['message'],
                                        "comment_like": reply.get('like', 0),
                                        "comment_time": datetime.fromtimestamp(reply['ctime']).strftime(
                                            '%Y-%m-%d %H:%M:%S')
                                    })

                                print(f"已获取第 {page} 页评论，共 {len(replies)} 条")
                                page += 1
                                await asyncio.sleep(0.5)
                            else:
                                print(f"获取评论失败: {comment_data.get('message', '未知错误')}")
                                break
                        else:
                            print(f"获取评论失败: HTTP {response.status}")
                            break
                except Exception as e:
                    print(f"获取评论时出错: {e}")
                    break

        return comments

    async def fetch_danmaku(self, cid: int, max_danmaku: int = 50):
        """获取视频弹幕的异步函数"""
        danmaku_list = []

        try:
            async with aiohttp.ClientSession() as session:
                danmaku_url = f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}"
                async with session.get(danmaku_url, headers=self.HEADERS) as response:
                    if response.status == 200:
                        xml_content = await response.text()
                        root = ET.fromstring(xml_content)

                        for i, d in enumerate(root.findall('.//d')):
                            if i >= max_danmaku:
                                break

                            attrs = d.get('p').split(',')
                            danmaku_time = float(attrs[0])
                            danmaku_type = int(attrs[1])
                            danmaku_size = int(attrs[2])
                            danmaku_color = int(attrs[3])
                            danmaku_timestamp = int(attrs[4])

                            danmaku_formatted_time = f"{int(danmaku_time // 60)}:{int(danmaku_time % 60):02d}"
                            danmaku_send_time = datetime.fromtimestamp(danmaku_timestamp).strftime('%Y-%m-%d %H:%M:%S')

                            danmaku_list.append({
                                "content": d.text,
                                "time": danmaku_formatted_time,
                                "type": danmaku_type,
                                "size": danmaku_size,
                                "color": f"#{danmaku_color:06x}",
                                "send_time": danmaku_send_time
                            })

                        print(f"获取了 {len(danmaku_list)} 条弹幕")
                    else:
                        print(f"获取弹幕失败: HTTP {response.status}")
        except Exception as e:
            print(f"获取弹幕时出错: {e}")

        return danmaku_list

    async def fetch_video_detail_direct(self, bvid: str, comment_pages: int, max_danmaku: int):
        """直接通过API获取视频详细信息的异步函数"""
        try:
            async with aiohttp.ClientSession() as session:
                info_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
                async with session.get(info_url, headers=self.HEADERS) as response:
                    if response.status == 200:
                        info_data = await response.json()
                        if info_data['code'] == 0:
                            info = info_data['data']
                            stat = info.get('stat', {})
                        else:
                            print(f"获取视频 {bvid} 信息失败: {info_data['message']}")
                            return None
                    else:
                        print(f"获取视频 {bvid} 信息失败: HTTP {response.status}")
                        return None

                comments = await self.fetch_comments(info['aid'], max_pages=comment_pages)

                danmaku = []
                if 'cid' in info:
                    danmaku = await self.fetch_danmaku(info['cid'], max_danmaku=max_danmaku)
                elif 'pages' in info and len(info['pages']) > 0 and 'cid' in info['pages'][0]:
                    danmaku = await self.fetch_danmaku(info['pages'][0]['cid'], max_danmaku=max_danmaku)

                detail_data = {
                    "bvid": bvid,
                    "summary": info.get('desc', '暂无摘要'),
                    "like": stat.get('like', 0),
                    "coin": stat.get('coin', 0),
                    "favorite": stat.get('favorite', 0),
                    "share": stat.get('share', 0),
                    "danmaku_count": stat.get('danmaku', 0),
                    "comments": comments,
                    "danmaku": danmaku
                }
                return detail_data
        except Exception as e:
            print(f"获取视频 {bvid} 详情时出错: {e}")
            return None


# 使用示例
# 改动点 1：去掉 __main__ 里写死的 "AI工作流"
if __name__ == '__main__':
    import sys
    # 如果命令行给了关键词就用，否则给出一个提示
    if len(sys.argv) < 2:
        print("用法: python search_tool.py <关键词> [max_videos] [comment_pages] [max_danmaku]")
        sys.exit(1)

    keyword = sys.argv[1]
    max_videos      = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    comment_pages   = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    max_danmaku     = int(sys.argv[4]) if len(sys.argv) > 4 else 30

    tool = BilibiliSearchTool()
    print(tool._run(keyword, max_videos, comment_pages, max_danmaku))