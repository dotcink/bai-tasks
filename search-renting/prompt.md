# 上海周浦租房信息抓取指令

## 核心任务
使用 `opencli` 抓取小红书（Rednote）上海周浦地区的二居室和三居室租房信息，提取详细字段，并自动同步到飞书电子表格。

## 执行步骤
1. **搜索抓取**：
   使用 `opencli xiaohongshu search` 搜索“上海周浦房东直租”、“周浦二居房东直租”等关键词，获取最近 2 个月内的笔记列表。
2. **深度解析**：
   针对候选笔记，使用 `opencli xiaohongshu note <url>` 获取正文内容。
3. **字段提取**：
   从标题和正文中解析出以下信息：
   - 租金 (Price)
   - 小区名称 (Compound)
   - 具体户型 (Layout)
   - 宠物政策 (Pet Friendly)
   - 租赁方式 (Rental Type: 直租/中介)
4. **过滤与评估**：
   - 仅保留周浦地区、2-3居室的信息。
   - 排除“求租”信息。
   - 排除明确标注“不可养宠”的房源。
5. **数据同步**：
   - 自动追加（Append）到飞书表格：`https://ycnuavhumwlq.feishu.cn/sheets/L4xPswHvXhQYAAtOzNYc5D4ynmg`。

## 运行命令
```bash
python3 process_renting.py
```
