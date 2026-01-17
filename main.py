"""
XXXGFPORN AstrBot Plugin
视频信息查询插件

Commands:
- /xxxgfporn <video_id> - 获取视频详细信息
- /xxxgfpornsearch <query> - 搜索视频
- /xxxgfpornlatest - 获取最新视频
- /xxxgfpornpopular - 获取热门视频
- /xxxgfporntop - 获取高评分视频
- /xxxgfpornrandom - 获取随机视频
- /xxxgfporncategory <category> - 获取分类视频
- /xxxgfporncategories - 获取所有分类列表
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp

from .modules import Client, Video, ImageProcessor, Category, SortOrder, TimeFilter


@register("astrbot_plugin_xxxgfporn", "vmoranv", "XXXGFPORN视频信息查询插件", "1.0.0")
class XXXGFPornPlugin(Star):
    """XXXGFPORN视频信息查询插件"""
    
    def __init__(self, context: Context):
        super().__init__(context)
        self._client: Optional[Client] = None
        self._image_processor: Optional[ImageProcessor] = None
        self._cache_dir: Optional[Path] = None
        self._last_cache_files: List[str] = []
    
    async def initialize(self):
        """初始化插件"""
        # 获取配置
        config = self.context.get_config()
        plugin_config = config.get("astrbot_plugin_xxxgfporn", {})
        
        # 代理配置
        proxy = plugin_config.get("proxy", "")
        
        # 打码程度 (0=不打码, 1=轻度, 2=中度, 3=重度)
        mosaic_level = plugin_config.get("mosaic_level", 2)
        
        # 初始化客户端
        self._client = Client(proxy=proxy if proxy else None)
        
        # 初始化缓存目录
        data_dir = Path(os.path.dirname(__file__)) / "data"
        self._cache_dir = data_dir / "cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化图片处理器
        self._image_processor = ImageProcessor(
            cache_dir=str(self._cache_dir),
            mosaic_level=mosaic_level,
            proxy=proxy if proxy else None
        )
        
        logger.info("XXXGFPORN插件初始化完成\u200B")
    
    async def terminate(self):
        """清理插件资源"""
        # 关闭客户端
        if self._client:
            await self._client.close()
        
        # 清理缓存
        self._cleanup_cache()
        
        logger.info("XXXGFPORN插件已停止\u200B")
    
    def _cleanup_cache(self) -> None:
        """清理上次发送的缓存文件"""
        for file_path in self._last_cache_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"清理缓存文件失败: {file_path}, 错误: {e}\u200B")
        self._last_cache_files.clear()
    
    def _format_video_info(self, video: Video) -> str:
        """格式化视频信息为文本"""
        lines = []
        lines.append(f"🎬 标题: {video.title or '未知'}\u200B")
        lines.append(f"🆔 ID: {video.video_id}\u200B")
        lines.append(f"🔗 链接: {video.url}\u200B")
        
        if video.duration:
            lines.append(f"⏱ 时长: {video.duration}\u200B")
        
        if video.views:
            lines.append(f"👀 观看: {video.views}\u200B")
        
        if video.rating:
            lines.append(f"⭐ 评分: {video.rating}\u200B")
        
        if video.uploader:
            lines.append(f"👤 上传者: {video.uploader}\u200B")
        
        if video.upload_date:
            lines.append(f"📅 上传日期: {video.upload_date}\u200B")
        
        if video.categories:
            lines.append(f"📁 分类: {', '.join(video.categories[:5])}\u200B")
        
        if video.tags:
            lines.append(f"🏷 标签: {', '.join(video.tags[:8])}\u200B")
        
        return "\n".join(lines)
    
    def _format_video_list_item(self, video_info: Dict[str, Any], index: int) -> str:
        """格式化视频列表项"""
        title = video_info.get("title", "未知标题")
        video_url = video_info.get("url", "")
        duration = video_info.get("duration", "")
        views = video_info.get("views", "")
        
        line = f"{index}. {title}\u200B"
        if duration:
            line += f" [{duration}]"
        if views:
            line += f" 👀{views}"
        
        # 显示完整URL而不是ID
        if video_url:
            line += f"\n   🔗 {video_url}\u200B"
        
        return line
    
    async def _get_and_send_thumbnail(
        self,
        event: AstrMessageEvent,
        thumbnail_url: Optional[str]
    ) -> None:
        """获取并发送缩略图"""
        if not thumbnail_url or not self._image_processor:
            return
        
        try:
            # 清理上次的缓存
            self._cleanup_cache()
            
            # 下载并处理图片
            image_path, from_cache = await self._image_processor.get_image(
                thumbnail_url,
                use_cache=True,
                apply_mosaic=True
            )
            
            if image_path:
                # 记录缓存文件
                if not from_cache:
                    self._last_cache_files.append(image_path)
                
                # 发送图片
                yield event.image_result(image_path)
        except Exception as e:
            logger.warning(f"获取缩略图失败: {e}\u200B")
    
    @filter.command("xxxgfporn")
    async def cmd_get_video(self, event: AstrMessageEvent):
        """获取视频详情 - 用法: /xxxgfporn <video_id>"""
        # 清理上次缓存
        self._cleanup_cache()
        
        # 解析参数
        message_str = event.message_str.strip()
        parts = message_str.split(maxsplit=1)
        
        if len(parts) < 2:
            yield event.plain_result("❌ 请提供视频ID\n用法: /xxxgfporn <video_id>\u200B")
            return
        
        video_id = parts[1].strip()
        
        try:
            # 获取视频信息
            video = await self._client.get_video(video_id)
            
            # 准备消息链 - 图片在前，文字在后
            chain = []
            
            # 先获取缩略图
            if video.thumbnail:
                try:
                    image_path, from_cache = await self._image_processor.get_image(
                        video.thumbnail,
                        use_cache=True,
                        apply_mosaic=True
                    )
                    if image_path:
                        if not from_cache:
                            self._last_cache_files.append(image_path)
                        # 图片放在最前面
                        chain.append(Comp.Image.fromFileSystem(image_path))
                except Exception as img_err:
                    logger.warning(f"缩略图处理失败: {img_err}\u200B")
            
            # 文字放在图片后面
            chain.append(Comp.Plain(self._format_video_info(video)))
            
            # 发送合并的消息
            yield event.chain_result(chain)
        
        except Exception as e:
            logger.error(f"获取视频失败: {e}\u200B")
            yield event.plain_result(f"❌ 获取视频失败: {str(e)}\u200B")
    
    @filter.command("xxxgfpornsearch")
    async def cmd_search(self, event: AstrMessageEvent):
        """搜索视频 - 用法: /xxxgfpornsearch <关键词>"""
        self._cleanup_cache()
        
        message_str = event.message_str.strip()
        parts = message_str.split(maxsplit=1)
        
        if len(parts) < 2:
            yield event.plain_result("❌ 请提供搜索关键词\n用法: /xxxgfpornsearch <关键词>\u200B")
            return
        
        query = parts[1].strip()
        
        try:
            videos = []
            async for video_info in self._client.search(query, page=1):
                videos.append(video_info)
                if len(videos) >= 10:
                    break
            
            if not videos:
                yield event.plain_result(f"🔍 未找到相关视频: {query}\u200B")
                return
            
            lines = [f"🔍 搜索结果: {query}\u200B\n"]
            for i, video_info in enumerate(videos, 1):
                lines.append(self._format_video_list_item(video_info, i))
            
            lines.append("\n💡 点击链接访问视频\u200B")
            yield event.plain_result("\n".join(lines))
        
        except Exception as e:
            logger.error(f"搜索失败: {e}\u200B")
            yield event.plain_result(f"❌ 搜索失败: {str(e)}\u200B")
    
    @filter.command("xxxgfpornlatest")
    async def cmd_latest(self, event: AstrMessageEvent):
        """获取最新视频"""
        self._cleanup_cache()
        
        try:
            videos = []
            async for video_info in self._client.get_latest_videos(page=1):
                videos.append(video_info)
                if len(videos) >= 10:
                    break
            
            if not videos:
                yield event.plain_result("📭 暂无最新视频\u200B")
                return
            
            lines = ["🆕 最新视频\u200B\n"]
            for i, video_info in enumerate(videos, 1):
                lines.append(self._format_video_list_item(video_info, i))
            
            lines.append("\n💡 点击链接访问视频\u200B")
            yield event.plain_result("\n".join(lines))
        
        except Exception as e:
            logger.error(f"获取最新视频失败: {e}\u200B")
            yield event.plain_result(f"❌ 获取最新视频失败: {str(e)}\u200B")
    
    @filter.command("xxxgfpornpopular")
    async def cmd_popular(self, event: AstrMessageEvent):
        """获取热门视频"""
        self._cleanup_cache()
        
        try:
            videos = []
            async for video_info in self._client.get_popular_videos(page=1):
                videos.append(video_info)
                if len(videos) >= 10:
                    break
            
            if not videos:
                yield event.plain_result("📭 暂无热门视频\u200B")
                return
            
            lines = ["🔥 热门视频\u200B\n"]
            for i, video_info in enumerate(videos, 1):
                lines.append(self._format_video_list_item(video_info, i))
            
            lines.append("\n💡 点击链接访问视频\u200B")
            yield event.plain_result("\n".join(lines))
        
        except Exception as e:
            logger.error(f"获取热门视频失败: {e}\u200B")
            yield event.plain_result(f"❌ 获取热门视频失败: {str(e)}\u200B")
    
    @filter.command("xxxgfporntop")
    async def cmd_top_rated(self, event: AstrMessageEvent):
        """获取高评分视频"""
        self._cleanup_cache()
        
        try:
            videos = []
            async for video_info in self._client.get_top_rated_videos(page=1):
                videos.append(video_info)
                if len(videos) >= 10:
                    break
            
            if not videos:
                yield event.plain_result("📭 暂无高评分视频\u200B")
                return
            
            lines = ["⭐ 高评分视频\u200B\n"]
            for i, video_info in enumerate(videos, 1):
                lines.append(self._format_video_list_item(video_info, i))
            
            lines.append("\n💡 点击链接访问视频\u200B")
            yield event.plain_result("\n".join(lines))
        
        except Exception as e:
            logger.error(f"获取高评分视频失败: {e}\u200B")
            yield event.plain_result(f"❌ 获取高评分视频失败: {str(e)}\u200B")
    
    @filter.command("xxxgfpornrandom")
    async def cmd_random(self, event: AstrMessageEvent):
        """获取随机视频"""
        self._cleanup_cache()
        
        try:
            video = await self._client.get_random_video()
            
            if not video:
                yield event.plain_result("🎲 获取随机视频失败\u200B")
                return
            
            # 准备消息链 - 图片在前，文字在后
            chain = []
            
            # 先获取缩略图
            thumbnail_url = video.thumbnail
            logger.debug(f"视频缩略图URL: {thumbnail_url}\u200B")
            
            if thumbnail_url:
                try:
                    image_path, from_cache = await self._image_processor.get_image(
                        thumbnail_url,
                        use_cache=True,
                        apply_mosaic=True
                    )
                    logger.debug(f"图片处理结果: path={image_path}, from_cache={from_cache}\u200B")
                    
                    if image_path:
                        if not from_cache:
                            self._last_cache_files.append(image_path)
                        # 图片放在消息链最前面
                        chain.append(Comp.Image.fromFileSystem(image_path))
                    else:
                        logger.warning(f"缩略图下载失败: {thumbnail_url}\u200B")
                except Exception as img_err:
                    logger.warning(f"缩略图处理失败: {img_err}\u200B")
            else:
                logger.debug("视频没有缩略图URL\u200B")
            
            # 文字放在图片后面
            chain.append(Comp.Plain("🎲 随机视频\u200B\n" + self._format_video_info(video)))
            
            # 发送合并的消息
            yield event.chain_result(chain)
        
        except Exception as e:
            logger.error(f"获取随机视频失败: {e}\u200B")
            yield event.plain_result(f"❌ 获取随机视频失败: {str(e)}\u200B")
    
    @filter.command("xxxgfporncategory")
    async def cmd_category(self, event: AstrMessageEvent):
        """获取分类视频 - 用法: /xxxgfporncategory <category>"""
        self._cleanup_cache()
        
        message_str = event.message_str.strip()
        parts = message_str.split(maxsplit=1)
        
        if len(parts) < 2:
            # 显示可用分类
            categories = Category.all()
            yield event.plain_result(
                "❌ 请提供分类名称\n"
                f"可用分类: {', '.join(categories)}\n"
                "用法: /xxxgfporncategory <category>\u200B"
            )
            return
        
        category = parts[1].strip().lower()
        
        try:
            videos = []
            async for video_info in self._client.get_category_videos(category, page=1):
                videos.append(video_info)
                if len(videos) >= 10:
                    break
            
            if not videos:
                yield event.plain_result(f"📭 分类 [{category}] 暂无视频\u200B")
                return
            
            lines = [f"📁 分类: {category}\u200B\n"]
            for i, video_info in enumerate(videos, 1):
                lines.append(self._format_video_list_item(video_info, i))
            
            lines.append("\n💡 点击链接访问视频\u200B")
            yield event.plain_result("\n".join(lines))
        
        except Exception as e:
            logger.error(f"获取分类视频失败: {e}\u200B")
            yield event.plain_result(f"❌ 获取分类视频失败: {str(e)}\u200B")
    
    @filter.command("xxxgfporncategories")
    async def cmd_categories(self, event: AstrMessageEvent):
        """获取所有分类列表"""
        self._cleanup_cache()
        
        try:
            categories = await self._client.get_categories()
            
            if not categories:
                # 返回预定义分类
                predefined = Category.all()
                yield event.plain_result(
                    "📁 可用分类:\u200B\n" +
                    ", ".join(predefined) +
                    "\n\n💡 使用 /xxxgfporncategory <category> 查看分类视频\u200B"
                )
                return
            
            lines = ["📁 所有分类:\u200B\n"]
            for cat in categories[:30]:
                lines.append(f"• {cat['name']} ({cat['slug']})\u200B")
            
            if len(categories) > 30:
                lines.append(f"\n... 还有 {len(categories) - 30} 个分类\u200B")
            
            lines.append("\n💡 使用 /xxxgfporncategory <slug> 查看分类视频\u200B")
            yield event.plain_result("\n".join(lines))
        
        except Exception as e:
            logger.error(f"获取分类列表失败: {e}\u200B")
            # 返回预定义分类
            predefined = Category.all()
            yield event.plain_result(
                "📁 预定义分类:\u200B\n" +
                ", ".join(predefined) +
                "\n\n💡 使用 /xxxgfporncategory <category> 查看分类视频\u200B"
            )
