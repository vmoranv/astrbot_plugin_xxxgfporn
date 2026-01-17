# XXXGFPORN AstrBot Plugin

## 功能特性

- 🔍 **视频搜索** - 根据关键词搜索视频
- 📋 **视频详情** - 获取视频标题、时长、观看数、评分等信息
- 🆕 **最新视频** - 浏览最新上传的视频
- 🔥 **热门视频** - 查看最受欢迎的视频
- ⭐ **高评分视频** - 获取评分最高的视频
- 🎲 **随机视频** - 随机获取一个视频
- 📁 **分类浏览** - 按分类浏览视频
- 🖼️ **缩略图展示** - 可配置的图片打码功能

## 安装

### 方法一：通过 AstrBot 插件管理器安装

1. 打开 AstrBot 管理面板
2. 进入「插件管理」
3. 点击「安装插件」
4. 输入仓库地址：`https://github.com/vmoranv/astrbot_plugin_xxxgfporn`

### 方法二：手动安装

1. 克隆仓库到 AstrBot 的 `addons/plugins/` 目录：
```bash
cd addons/plugins/
git clone https://github.com/vmoranv/astrbot_plugin_xxxgfporn
```

2. 安装依赖：
```bash
pip install -r astrbot_plugin_xxxgfporn/requirements.txt
```

3. 重启 AstrBot

## 命令列表

| 命令 | 说明 | 示例 |
|------|------|------|
| `/xxxgfpornsearch <关键词>` | 搜索视频 | `/xxxgfpornsearch asian` |
| `/xxxgfpornlatest` | 获取最新视频列表 | `/xxxgfpornlatest` |
| `/xxxgfpornpopular` | 获取热门视频列表 | `/xxxgfpornpopular` |
| `/xxxgfporntop` | 获取高评分视频列表 | `/xxxgfporntop` |
| `/xxxgfpornrandom` | 获取一个随机视频 | `/xxxgfpornrandom` |
| `/xxxgfporncategory <分类>` | 获取指定分类的视频 | `/xxxgfporncategory milf` |
| `/xxxgfporncategories` | 获取所有分类列表 | `/xxxgfporncategories` |

### 真实使用示例

以下是实际运行时的日志输出：

**搜索视频:**
```
[15:44:29] [Core] [INFO]: /xxxgfpornsearch asian
[15:44:29] [Core] [INFO]: 🔍 搜索结果: asian

1. Two asian Ladyboys and one masked faggot... [17:32] 👀233
   🔗 https://www.xxxgfporn.com/video/two-asian-ladyboys-...-151605.html
   🖼️ https://media.xxxgfporn.com/thumbs/embedded/151605.jpg
2. Hot asian teenager +18 want a rough... [25:38] 👀43
   🔗 https://www.xxxgfporn.com/video/hot-asian-teenager-...-190469.html
   ...
```

**随机视频（含打码缩略图）:**
```
用户: /xxxgfpornrandom
机器人: 🎲 随机视频
🎬 标题: TINY4K Petite Blonde Gets Facialed
🆔 ID: tiny4k-petite-blonde-gets-facialed-93944.html
🔗 链接: https://www.xxxgfporn.com/video/tiny4k-petite-blonde-gets-facialed-93944.html
🖼️ 缩略图: https://media.xxxgfporn.com/thumbs/embedded/93944.jpg
[打码缩略图图片]
```

**分类浏览:**
```
用户: /xxxgfporncategory milf
机器人: 📁 分类: milf

1. Sexy Nerdy Milf Abbey James First Fuck... [02:16] 👀1117
   🔗 https://www.xxxgfporn.com/video/sexy-nerdy-milf-...-112283.html
2. Sexy Milf Ainsley Adams Promo... [02:15] 👀110
   ...
```

## 配置说明

在 AstrBot 管理面板中配置插件：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `proxy` | 代理服务器地址 | 空（不使用代理） |
| `mosaic_level` | 图片打码程度 (0-3) | 2 |
| `max_cache_files` | 最大缓存文件数量 | 100 |
| `request_timeout` | 请求超时时间(秒) | 30 |

### 打码级别说明

- **0** - 不打码（原图）
- **1** - 轻度模糊
- **2** - 中度模糊（推荐）
- **3** - 重度模糊 + 马赛克

## 可用分类

```
amateur, anal, asian, bbw, big-tits, blonde, blowjob, 
brunette, creampie, cumshot, hardcore, lesbian, 
mature, milf, teen, threesome
```

## 开发

### 运行测试

```bash
# 安装测试依赖
pip install pyyaml

# 运行测试
python test_plugin.py
```

### 项目结构

```
astrbot_plugin_xxxgfporn/
├── main.py              # 插件主文件
├── metadata.yaml        # 插件元数据
├── _conf_schema.json    # 配置schema
├── requirements.txt     # 依赖声明
├── test_plugin.py       # 测试脚本
├── README.md            # 说明文档
├── LICENSE              # 许可证
└── modules/             # 核心模块
    ├── __init__.py      # 模块入口
    ├── client.py        # HTTP客户端
    ├── video.py         # 视频类
    ├── consts.py        # 常量定义
    ├── errors.py        # 错误定义
    └── image_utils.py   # 图片处理
```

## 注意事项

⚠️ **重要提醒**：

1. 本插件仅供学习和技术研究使用
2. 请遵守当地法律法规
3. 请勿在公共场合使用
4. 使用代理可能有助于访问稳定性

## 许可证

MIT License

## 作者

[vmoranv](https://github.com/vmoranv)

## 致谢

- [AstrBot](https://github.com/Soulter/AstrBot) - 强大的机器人框架
- [Eporner-API](https://github.com/EchterAlpha/Eporner-API) - 参考实现
