PR: 前端接入 Broadcast Package v0.1（Receiver Integration）
目标

将 Sputnik 前端从 mock 数据驱动切换为 Broadcast Package v0.1 驱动。

本 PR 的核心目标不是新增视觉设计，而是验证完整接收链路：

前端读取真实广播包
自动播放真实音频
根据真实 score.json 点亮星图
根据 meta.json / state.json 展示运行信息

完成后，Sputnik 将第一次从“前端 mock”进入“真实接收器”状态。

背景

当前前端已经具备以下基础能力：

平面像素星空可视化
广播星点与项目恒星的分层结构
点亮动画基础逻辑
launch timer / orbit day 的展示方向
透明输入框 UI 基础

后端当前已进入：

render 输出音频
broadcast package 输出每日广播包

因此现在需要完成一次关键集成：

让前端不再依赖手写 mock，而是消费真实广播包。

本 PR 要解决的问题
1. 数据源切换

将前端的 mock 数据替换为真实 package 文件：

meta.json
state.json
playlist.json
score.json
audio/*.wav
2. 音频与星图同步

让星图点亮逻辑围绕真实 score.json 工作，并与真实播放时间对齐。

3. 页面状态真实化

让页面显示的：

since launch
orbit day
signal / mode

来自真实 package，而不是前端写死。

范围
本 PR 要做
读取 broadcast/latest/ 下的真实文件
前端建立 package loader
接入真实音频路径
接入真实 score 到星图
接入真实 meta / state 到页面状态行
跑通打开即播的最小闭环
本 PR 不做
不改前端视觉风格
不改星图设计方案
不做多段复杂 playlist 编排
不做输入框真实后端提交
不做污染机制接入
不做历史 archive 切换
接入目标文件
1. meta.json

前端使用：

launchAt
generatedAt
orbitDay
packageVersion

用途：

launch timer
orbit day 展示
页面状态信息
2. state.json

前端使用：

signal
mode
mood
transmission

用途：

状态行文案
弱状态展示
3. playlist.json

前端使用：

当前应播放哪个音频文件
当前 segment 对应哪个 score.json

用途：

音频入口统一化
后续支持多段扩展
4. score.json

前端使用：

bpm
bars
notes

用途：

广播星点生成
点亮时序推进
与播放时间同步
5. audio/segment_001.wav

前端使用：

页面自动播放
播放时间驱动星图同步
前端实现内容
A. Package Loader

新增一个广播包加载层，负责：

拉取 meta.json
拉取 state.json
拉取 playlist.json
拉取 score.json
建立统一前端状态对象

建议新增模块：

loadBroadcastPackage()
loadScore()
loadMetaState()
B. Audio Binding

让前端播放器不再读本地 mock 音频，而是读：

playlist.json 中声明的音频路径

要求：

音频路径通过 package 提供
不在前端硬编码文件名
允许后续扩展多段 segment
C. Score-driven Starfield

将星图真正切换到 score.json 驱动。

要求：

星点生成基于真实 notes
点亮节奏基于真实 note 时间
与音频播放时间关联
D. Meta/State-driven UI

将页面状态行切换为真实数据驱动。

例如：

transmitting since launch
orbit day
signal status
mode

要求：

不再依赖纯前端写死值
package 缺失字段时有兜底
技术任务拆分
Task 1：新增 package 读取模块
统一读取 broadcast/latest/
处理基础异常和缺文件兜底
Task 2：接入真实 meta.json
launch timer 改为从 meta 读取
orbit day 改为从 meta 读取
Task 3：接入真实 state.json
状态行改为真实广播状态
Task 4：接入真实 playlist.json
用 playlist 驱动音频路径
建立 segment 播放入口
Task 5：接入真实 score.json
星图节点从真实 notes 生成
替换 mock 数据
Task 6：打通播放时间与点亮逻辑
音频 currentTime 驱动星图激活
保证点亮不再是前端模拟时钟
验收标准
功能层
页面能读取完整 broadcast package
页面能自动播放真实音频
星图由真实 score.json 驱动
状态行由真实 meta/state 驱动
体验层
页面打开后不再只是视觉 mock
用户能明显感受到“接入了一次真实广播”
星图点亮与声音节奏基本对齐
工程层
mock 数据和真实 package 读取逻辑清楚分离
前端不再依赖手写假数据才能运行
未来多段 playlist 扩展有空间
风险与注意事项
1. 不要一次接太多

v0.1 只接单段 package，不要顺手引入复杂多段系统。

2. 时间对齐要优先保证

即使状态展示先粗一点，音频和星图同步也必须优先成立。

3. 保留 mock fallback

在真实 package 缺失时，前端最好还能退回 mock，方便开发。

完成后的价值

完成本 PR 后，Sputnik 将第一次形成真正闭环：

后端生成广播包
→ 前端读取广播包
→ 页面自动播放
→ 星图随真实乐谱点亮

这是项目从“前端 mock + 后端零件”进入“可运行装置”的关键一步。