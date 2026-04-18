PR: 实现 Sputnik Render v0.1（冷电子广播发声器）
目标

实现 Sputnik 后端中的第一版发声模块：
将一份最小 score.json 渲染为一段可播放的冷电子广播音频。

本 PR 的目标不是做通用音乐引擎，也不是做完整作曲系统，而是先实现一个Sputnik 专用发声器，让这台机器第一次真正“发出声音”。

背景

当前前端接收器界面已经基本成型，下一步需要一个可稳定输出音频的后端模块，作为整个广播链路的第一块可运行基础设施。

在当前阶段：

composition（模型生成乐谱）还未最终接入
drift（退行污染）还未正式启用
score 协议尚在收紧

因此，最合理的切入点是优先实现 render 模块，先验证：

最小乐谱结构是否足够驱动声音
声音是否符合 Sputnik 的气质
前端星图和后端乐谱是否能围绕同一份结构协作
本 PR 要解决的问题
1. 让系统第一次“出声”

给一份手写的最小 score.json，能够输出一段 wav 音频。

2. 确定 Sputnik 的基础音色方向

第一版声音不追求完整音乐性，而追求：

冷
稀疏
机械
带广播/半导体设备感
带轻微噪声和信号不稳定感
3. 倒逼 score 协议收敛

通过 render 反推：

一个 note 需要哪些字段
时间/时值如何定义
track 是否必要
音高和密度的合理边界
范围
本 PR 要做
定义 render 所需的最小 score.json 输入格式
解析 note 数据并建立时间轴
实现四条基础轨道的简单发声（track 0–3）
实现最小包络（ADSR 或简化包络）
实现基础冷电子广播效果
输出 wav 音频
提供一份可直接测试的 demo score
本 PR 不做
不接真实 Qwen 输出
不做复杂乐理规则
不做高保真乐器
不做完整混音系统
不做外部污染输入
不做实时 API
不做 mp3 压缩优化（可后续补）
声音目标
一句话目标

像一台旧半导体收音机在宇宙里用低功率发射一首自己没学会的人类歌。

第一版声音气质关键词
冷电子
广播感
半导体
短波/低功率
轻微噪声
稀疏
远
机械
失败的歌唱
不希望出现的感觉
温暖 pad 氛围乐
完整旋律编曲
lofi 学习电台
synthwave
游戏菜单 BGM
电影感大混响宇宙音乐
输入协议（最小 render score）

本 PR 依赖的最小输入结构如下：

{
  "bpm": 72,
  "bars": 4,
  "notes": [
    { "t": 0, "d": 1, "p": 60, "v": 0.8, "track": 0 },
    { "t": 2, "d": 1, "p": 64, "v": 0.6, "track": 1 },
    { "t": 4, "d": 2, "p": 67, "v": 0.5, "track": 0 },
    { "t": 6, "d": 0.35, "p": 79, "v": 0.4, "track": 3 }
  ]
}
字段说明
bpm：速度
bars：总小节数
notes：音符列表
t：起始位置（基于离散格）
d：持续时长（基于离散格）
p：音高（先按 MIDI 风格整数处理）
v：力度/音量
track：轨道编号（0–3，见下「声音结构」）
当前假设
时间单位先统一为固定网格
每段长度固定
不支持复杂节拍变化
不支持复杂自动化参数
Render v0.1 声音结构

第一版发声器采用四层思路（四条基础轨道）：

Track 0：Beacon / Lead

主信号轨，承担“机器在唱”的部分。

目标感觉：

薄
冷
有信号感
不圆润

建议实现：

triangle 或 sine 为主
短 attack
中短 release
音量较克制
可带极轻微 pitch 漂移
Track 1：Cold Drone

底层持续轨，提供设备仍在工作的低存在感。

目标感觉：

低功率供电感
长音
空
冷

建议实现：

sine / filtered triangle
更长 sustain
更低音量
不抢主信号
Track 2：Static / Ghost（可选）

故障和边缘信号层。

目标感觉：

电路噪声
信号边缘掉渣
短暂闪现
不稳定

建议实现：

短 burst noise
高频 hiss
少量重复/回声
低概率触发或按 track 输出
Track 3：Relay / Ping（遥测脉冲）

短促、偏金属/玻璃的应答感，像远端遥测或呼号边缘，不抢主信号。

目标感觉：

冷
短
有「信号被收到又弹回」的脉冲感
存在感低于 Beacon

建议实现：

轻度 FM 或短 decay 的正弦簇
短 attack、较快 decay、较低 sustain
音量明显低于 track 0
效果链
必做效果
1. 最小包络

每个 note 需要简单包络，避免纯硬开硬关。

第一版允许：

attack
decay
sustain
release

要求：

参数简单
可按 track 区分
2. 轻微 delay

用于制造“广播回声”感，而不是房间空间感。

要求：

很轻
不能拖成氛围乐
主要服务于远距离感和残响感
3. 控制性噪声

需要一层广播设备底噪。

要求：

不是全程盖住主信号
更像弱 hiss / carrier / 电路底噪
可全局存在，也可按轨混入
可选效果（本 PR 可不做完）
极轻微 wow/flutter
偶发 signal drop
轻度 bit roughness
轻微带通/高通滤波
输出
主输出
rendered.wav
可选输出
调试用中间结果
单轨 wav
note 事件日志
时长信息
建议目录结构
pipeline/
  render/
    __init__.py
    schema.py
    synth.py
    effects.py
    exporter.py
    demo_score.json
文件职责
schema.py

定义 render 使用的最小 score 结构，负责基础校验。

synth.py

核心合成逻辑：

note -> waveform
时间轴放置
多轨混合
effects.py

处理：

delay
hiss/noise
简单滤波
可选信号衰减
exporter.py

输出 wav 文件。

demo_score.json

手写测试谱，用于 render 联调。

开发任务拆分
Task 1：定义 render 最小 score 结构
定义 note 数据结构
定义 bpm / bars / notes 最小规则
提供 demo score
Task 2：实现单 note 基础发声
通过 p 生成频率
支持基础波形
支持基础包络
Task 3：实现 note 时间轴拼接
支持根据 t 和 d 放置音符
支持总时长计算
支持简单混合
Task 4：实现按 track 区分音色
track 0 / 1 / 2 / 3 不同基础声音
参数先写死也可以
Task 5：实现广播感效果
加轻微 delay
加底噪
调整整体输出质感
Task 6：导出 wav
输出最终文件
可本地试听
验收标准
功能层
给定 demo_score.json，能稳定输出 wav
note 时间位置正确
多轨可同时发声
声音层
听起来不是纯蜂鸣器测试音
听起来不是普通 BGM
有明显冷电子广播装置感
能感受到“机器试图歌唱”
工程层
render 与 composition 解耦
render 不依赖真实模型
输入输出边界清楚
未来可直接替换为真实 score.json
风险与注意事项
1. 不要做成通用音乐引擎

本模块服务于 Sputnik，不追求通用。

2. 不要过早追求音色复杂度

第一版先求气质成立，再求细节丰富。

3. 不要让噪声盖住结构

噪声应服务于广播感，而不是毁掉 note 节奏。

4. 不要让声音太暖

当前方向明确偏冷、偏薄、偏远。

完成后的价值

完成本 PR 后，可以立刻验证：

Sputnik 是否已经具备“发声能力”
当前 score 结构是否足够合理
前端星图是否能围绕同一份数据继续推进
后续 composition 模块应该向什么声音方向收敛
一句话总结

本 PR 的目标不是做“音乐生成”，而是：

先造出一台会发出冷电子广播歌声的 Sputnik。