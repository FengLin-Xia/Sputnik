# PR: 实现 Composition v0.1（通过 Ollama 生成合法广播乐谱）

## 目标
实现 Sputnik 后端中的 **Composition v0.1**，通过本地模型生成一份合法、可播、可视化兼容的 `score.json`。

本 PR 的目标不是提升音乐质量，也不是引入复杂污染机制，而是先让 Sputnik 的“生成端”真正接入本地模型，完成从：

**输入约束 / seed / 状态  
→ 本地模型  
→ 合法 `score.json`  
→ 现有 render + frontend 闭环**

的第一版通路。

---

## 背景
当前项目已经具备以下基础能力：

- 前端接收器界面已完成
- 平面像素星图已完成
- render 已可将 `score.json` 转为广播音频
- playback 已跑通
- `score spec v0.1` 已基本明确

因此目前的主要缺口不再是展示端或发声端，而是：

**谁来生成下一段广播乐谱。**

为降低工程复杂度，本 PR 采用 **Ollama** 作为本地模型 provider，将模型调用与项目主逻辑解耦。

---

## 本 PR 要解决的问题

### 1. 让本地模型第一次真正参与 Sputnik
给定一组最小输入，让本地模型输出一份符合 `score spec v0.1` 的广播乐谱。

### 2. 建立生成层的清晰边界
将 composition 明确拆分为：
- prompt 构建
- provider 调用
- 输出解析与校验

### 3. 为后续 drift / regression engine 留出接入口
v0.1 先不用复杂退行污染，但 composition 应预留未来接入：
- 前一天残留
- 文本碎片
- motif 漂移
- 外部污染

---

## 范围

### 本 PR 要做
- 使用 Ollama 作为本地模型调用方式
- 定义 composition 输入结构
- 实现 prompt builder
- 实现 Ollama provider
- 实现 composer（输出解析 + schema 校验）
- 输出合法 `score.json`
- 产出最小 demo 结果并接入现有 render / frontend

### 本 PR 不做
- 不做 drift / 自动化退行污染
- 不做用户污染输入
- 不做复杂 seed pack 抽样系统
- 不做高质量音乐优化
- 不做多模型切换 UI
- 不做在线 API 暴露

---

## Composition v0.1 的定位

Composition v0.1 的任务不是“创作一首好歌”，而是：

**生成一份能被 Sputnik 系统吃下去的广播乐谱。**

它首先要满足：
1. 合法
2. 可播
3. 可视化兼容
4. 不出戏

而不是首先满足：
- 音乐性强
- 情感丰富
- 旋律完整

---

## 输入来源（v0.1）

Composition v0.1 建议先使用以下最小输入：

### 1. 固定系统约束
包括：
- Sputnik 的基本身份设定
- 输出只能是 JSON
- 必须符合 `score spec v0.1`
- 只能使用 0–3 号轨道
- note 数量、pitch 范围、velocity 范围等边界

### 2. 最小 seed
先不接完整 seed pack，只接少量风格种子，例如：
- 冷电子广播
- 半导体
- 低功率
- 稀疏
- 失败的歌唱

### 3. 当前状态（可选）
例如：
- `mode = beacon`
- `mood = cold`
- `signal = stable`

v0.1 中状态字段可非常少，主要用于给模型一点广播情境感。

---

## 输出目标

Composition 模块最终输出：

- 一份合法的 `score.json`
- 能通过 schema 校验
- 能喂给 render
- 能喂给前端星图

### v0.1 输出要求
- 只输出 JSON
- 顶层字段至少包含：
  - `bpm`
  - `bars`
  - `notes`
- 每个 note 至少包含：
  - `t`
  - `d`
  - `p`
  - `v`
  - `track`

---

## 模块拆分建议

建议目录结构如下：

```text
pipeline/
  composition/
    __init__.py
    composer.py
    prompt_builder.py
    providers/
      __init__.py
      ollama_provider.py
      mock_provider.py
```

---

## 文件职责

### `prompt_builder.py`
负责：
- 组织系统提示
- 组织 seed / 状态输入
- 注入 score 规范要求
- 输出给 provider 的 prompt / messages

### `providers/ollama_provider.py`
负责：
- 调用本地 Ollama
- 向指定模型发送请求
- 返回模型原始文本输出
- 提供基础错误处理与超时处理

### `providers/mock_provider.py`
负责：
- 在无模型或调试阶段返回假输出
- 方便开发 package / render / frontend 联调

### `composer.py`
负责：
- 调用 `prompt_builder`
- 调用 provider
- 解析模型输出
- 做 JSON 提取与 schema 校验
- 输出最终合法 `score.json`
- 必要时执行重试

---

## 生成流程（v0.1）

### Step 1：构建 prompt
输入：
- 固定风格约束
- 最小 seed
- 当前状态（可选）
- score spec 摘要

输出：
- 一段面向本地模型的结构化 prompt

---

### Step 2：调用 Ollama
通过本地 Ollama provider 调模型，例如：
- `qwen2.5:7b`（具体 tag 以本地实际为准）

输出：
- 模型返回文本

---

### Step 3：解析 JSON
从模型返回中提取 JSON。

目标：
- 去掉自然语言解释
- 去掉多余前后缀
- 提取合法结构

---

### Step 4：校验 score
根据 `score spec v0.1` 检查：
- 顶层字段
- note 必需字段
- 数值范围
- track 合法性
- note 数量边界

---

### Step 5：输出最终 score
输出路径例如：
- `composition_output/score.json`
或后续直接交给 package builder

---

## Prompt 设计原则

### 1. 壳要薄
prompt 的目标不是替模型写审美，而是：
- 不要出戏
- 不要输出自然语言解释
- 不要跑出 schema 外

### 2. 明确输出格式
必须明确要求：
- 只输出 JSON
- 不加说明
- 不加 markdown
- 不加注释

### 3. 明确 Sputnik 气质边界
允许写很少，但要明确：
- 稀疏
- 冷
- 机械
- 带广播感
- 不要完整流行旋律
- 更像失败的歌唱

---

## Ollama Provider 要求

### 功能要求
- 支持调用本地模型
- 支持模型名称配置
- 支持超时
- 支持返回原始文本

### 工程要求
- 不将 Ollama 细节泄漏到 `composer.py`
- provider 层单独处理请求参数
- 便于未来替换为其他本地 provider

---

## 验收标准

### 功能层
- 能成功通过 Ollama 获取模型输出
- 能解析出一份合法 `score.json`
- `score.json` 可被 render 正常使用
- 前端星图可基于该 score 正常显示/点亮

### 工程层
- prompt 构建、provider 调用、输出解析职责清楚
- composition 与 render 解耦
- composition 与 frontend 解耦
- provider 可替换

### 体验层
- 生成结果不要求“好听”
- 但必须：
  - 不出戏
  - 不完全坍塌
  - 仍像 Sputnik 的广播乐谱

---

## 风险与注意事项

### 1. 不要在 v0.1 追求高质量音乐
先追求合法和可系统消费。

### 2. 不要让 prompt 过厚
避免把审美和结构都写死，导致模型只是复读 prompt。

### 3. 不要让 provider 侵入整个项目
模型调用应只存在于 composition 层。

### 4. 要接受第一次输出可能很笨
这是正常的。  
v0.1 的目标是“先让它会写谱”，不是“先让它写得惊艳”。

---

## 完成后的价值

完成本 PR 后，Sputnik 将第一次具备：

- 本地模型驱动的乐谱生成能力
- 从生成到发声再到可视化的完整闭环
- 后续接入 drift / regression 的真实落点
- 一个清晰、可替换的本地模型调用层

---

## 一句话总结

本 PR 的目标不是让 Sputnik 学会作曲，而是：

**先让它学会写出一份自己能唱出来的广播乐谱。**
