PR: 实现 Broadcast Package v0.1（每日广播包协议与产物输出）
目标

实现 Sputnik 后端中的 Broadcast Package v0.1，将当天生成结果整理为一组前端可直接消费的静态文件。

本 PR 的目标不是做实时服务，而是建立一套每日广播包协议，作为后端生产线与前端接收器之间的稳定交界面。

完成本 PR 后，系统应能将一段广播的：

乐谱结构
音频产物
状态信息
元信息
播放编排

统一输出到一个可发布、可归档、可被前端直接读取的目录中。

背景

当前项目已经明确采用以下总体策略：

非实时生成
离线批量产出每日广播内容
前端作为静态接收器，打开即播
前端视觉和音频共享同一份乐谱结构
后端最终产物应以“广播包”的形式存在，而不是散落在各模块中的中间文件

因此，需要定义一个最小但稳定的 Broadcast Package 作为 v0.1 的正式协议层。

本 PR 要解决的问题
1. 定义后端最终交付物

明确后端产出哪些文件、这些文件的语义是什么、放在哪里。

2. 建立前后端共享协议

前端后续将直接读取该广播包进行：

自动播放
星图点亮
状态展示
since launch / orbit day 展示
3. 为后续归档与每日演化留口子

v0.1 先支持单日包 / latest 包，但结构上应允许未来按日期归档。

范围
本 PR 要做
定义 Broadcast Package v0.1 的目录结构
定义各 json 文件最小字段
实现 package 构建逻辑
将 render 产物和元信息整理到 package 中
输出到固定目录（如 broadcast/latest/）
本 PR 不做
不实现真实云端发布
不实现每日自动 push
不实现复杂多段 playlist 编排
不实现归档历史浏览 UI
不实现用户污染输入写入
不实现完整 drift pipeline 接入（可先接受占位数据）
Broadcast Package v0.1 的定位

Broadcast Package = 某一天 Sputnik 广播状态的完整静态快照。

它是：

前端可直接读取的资源包
后端每日生成的最终产物
之后归档、退行污染、重新发布的基础单元

它不是：

运行时数据库
中间调试文件堆
只给后端看的内部缓存
目录结构（v0.1 建议）
broadcast/
  latest/
    score.json
    state.json
    meta.json
    playlist.json
    fragments.json
    audio/
      segment_001.wav

后续预留结构：

broadcast/
  latest/
  archive/
    2026-04-18/
    2026-04-19/

但本 PR 只要求先完成 latest/。

文件说明
1. score.json

作用：记录当前广播的乐谱结构，是音频和前端星图的共同底稿。

最小建议结构：

{
  "bpm": 72,
  "bars": 4,
  "notes": [
    { "t": 0, "d": 1, "p": 60, "v": 0.8, "track": 0 },
    { "t": 2, "d": 1, "p": 64, "v": 0.6, "track": 1 }
  ]
}

说明：

本文件来自 composition（或当前阶段的 demo score）
render 必须严格基于此文件产出音频
前端星图点亮逻辑也将读取此文件
2. state.json

作用：记录当前广播的状态信息，用于前端弱状态文案展示。

建议最小结构：

{
  "signal": "stable",
  "mode": "beacon",
  "mood": "cold",
  "transmission": "active"
}

字段解释：

signal：信号状态，如 stable / degraded / unstable
mode：广播模式，如 beacon / drift / memory_leak
mood：当日气质，可选
transmission：当前是否在持续广播

说明：

v0.1 可手写或程序默认生成
不要求复杂动态状态机
3. meta.json

作用：记录广播的时间与版本元信息。

建议最小结构：

{
  "launchAt": "2026-04-18T00:00:00Z",
  "generatedAt": "2026-04-18T12:30:00Z",
  "orbitDay": 1,
  "packageVersion": "0.1.0",
  "audioFormat": "wav"
}

字段解释：

launchAt：卫星发射时间
generatedAt：当前广播包生成时间
orbitDay：当前为第几日广播
packageVersion：广播包协议版本
audioFormat：音频格式

说明：

前端 since launch / orbit day 展示依赖本文件
该文件是广播包的时间锚点
4. playlist.json

作用：定义当前广播包中应播放哪些音频资源，以及与哪些 score/segment 对应。

v0.1 因为先只做单段广播，可极简：

{
  "segments": [
    {
      "id": "segment_001",
      "audio": "audio/segment_001.wav",
      "score": "score.json",
      "startOffset": 0
    }
  ]
}

说明：

v0.1 可以只有一个 segment
后续可扩展为多个片段广播编排
前端统一从此文件读取播放入口，不直接写死音频路径
5. fragments.json

作用：记录当前广播包保留的碎片残留，用于之后 drift/退行污染读取。

建议最小结构：

{
  "fragments": [
    "still transmitting",
    "cold signal",
    "no confirmed return"
  ]
}

说明：

v0.1 可先由默认文本或手写数据填充
后续 drift engine 将从这里读取并再加工
这是“系统记忆残片”的最小接口
6. audio/segment_001.wav

作用：当前广播段的实际音频文件。

说明：

来自 render 输出
playlist 将引用它
前端播放的是真音频，不是实时渲染
Package 构建逻辑
输入

本 PR 的 package builder 接收：

一份 score.json
一份 render 输出音频
一份最小状态数据
一份最小 fragments 数据
基础 meta 参数
输出

在固定目录中生成一整包：

broadcast/latest/
  score.json
  state.json
  meta.json
  playlist.json
  fragments.json
  audio/
    segment_001.wav
模块建议位置

建议新增：

pipeline/
  broadcast_package/
    __init__.py
    builder.py
    schema.py
文件职责
builder.py

负责：

创建目标目录
拷贝或写入 score/state/meta/playlist/fragments
拷贝音频产物到 audio/
保证 package 结构完整
schema.py

负责：

定义 package 内各 json 文件的最小结构
做基础字段校验
开发任务拆分
Task 1：定义 package 目录结构
固定 broadcast/latest/
固定 audio/ 子目录
明确文件命名规则
Task 2：定义各 json 最小字段
score.json
state.json
meta.json
playlist.json
fragments.json
Task 3：实现 builder
写目录
拷文件
生成 json
统一输出到 broadcast/latest/
Task 4：接入 render 产物
接收 rendered.wav
重命名或复制为 audio/segment_001.wav
Task 5：生成最小可读 package
前端可直接读取
手动验证各文件关系正确
验收标准
协议层
广播包目录结构固定且清晰
各 json 字段语义明确
前端后续可稳定依赖这些文件
功能层
给定一份 score 和音频，能成功生成完整广播包
playlist.json 能指向正确音频
meta.json 能支撑 launch timer / orbit day 展示
工程层
package 构建与 render 解耦
package builder 不关心音频怎么生成
package builder 不直接依赖前端代码
风险与注意事项
1. 不要把 package 当中间缓存

它是正式产物，不是临时目录。

2. 不要把前端配置和每日广播包混在一起

例如长期固定的 projects.json 不建议放入 broadcast/，除非未来它也会随每日广播变化。

3. v0.1 不要过度设计多段播放

先让单段广播包成立，再扩成多段 playlist。

4. 字段越少越好

先服务当前前端与 render 闭环，不要预埋过多未来字段。

完成后的价值

完成本 PR 后，系统将第一次具备：

明确的后端最终产物形态
前后端共享的每日广播协议
render -> package -> frontend 的可闭环基础
后续 composition / drift 接入的稳定目标格式