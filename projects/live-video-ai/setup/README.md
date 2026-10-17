# 第一版搭建记录：3090 + Windows / WSL2

日期：2026-10-18。[返回目标路线](../README.md)

## 已确认的第一版范围

- 使用现有3090，Windows主机、WSL2推理环境。
- 摄像头实时输入，按提示词做风格转换；先不训练基础模型。
- 用户接受200×200像素画面。展示尺寸先定200×200；实际推理尺寸与展示尺寸分别记录。
- 建议比较256×256推理（低分辨率实验）与512×512推理（SD-Turbo模型卡推荐参考），最后缩放为200×200显示。256是否可用、画质与速度仍需在实际机器测试，不能只把512输出缩小就宣称推理更快。
- 不强行把内部推理尺寸设成200×200；尺寸需要适合选定模型与加速后端。不能仅凭200可被8整除就断言整条网络和加速引擎兼容。
- 第一轮优先同一台Windows机器的浏览器localhost与摄像头跑通，减少跨机器网络与摄像头访问变量；之后再接Mac摄像头。摄像头接在哪台机器尚待执行阶段确认，不能当作已有事实。

SD-Turbo支持少步推理，其官方模型卡偏好512×512。较低分辨率可能牺牲语义与人物质量，需实际对比。[官方模型卡](https://huggingface.co/stabilityai/sd-turbo)

![第一步与画面尺寸](step-01.svg)

## 当前进度

| 步骤 | 内容 | 状态 |
| --- | --- | --- |
| 0 | 确认目标与现有设备 | 已确认 |
| 1 | 检查Windows、驱动、WSL2、RAM与磁盘 | 已提供命令，等待用户在3090主机执行 |
| 2 | 验证WSL2中的GPU访问 | 待步骤1结果 |
| 3 | 建立隔离Python环境并固定依赖版本 | 待GPU验证 |
| 4 | 下载预训练模型，验证单帧转换 | 未执行 |
| 5 | 浏览器摄像头连续输入与200×200展示 | 未执行 |
| 6 | 提示词切换、延迟/FPS与画面连续性检查 | 未执行 |
| 7 | 根据结果优化，再考虑微调 | 未执行 |

## 第1步：只检查，不安装

当前聊天可操作的本地工作区在Mac上，尚未获得3090主机的连接信息，因此不能声称已在Windows或WSL中执行检查。

在3090那台电脑打开普通PowerShell，依次执行下面四条命令，复制输出回聊天。诊断失败或提示某命令不存在，也请保留原样；先不按网上教程混装CUDA或驱动。

```powershell
Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber
nvidia-smi --query-gpu=name,driver_version,memory.total,memory.free --format=csv
wsl --version
wsl --list --verbose
```

若WSL提示需要安装或更新，本步只记录提示，关闭提示即可，不把它记作已安装。正常检查不需要管理员PowerShell。

可选：下载并查看[完整只读诊断脚本](01-check-windows.ps1)，额外输出RAM与各磁盘空闲空间。若系统阻止运行.ps1，不修改执行策略；先复制上面四条命令即可。该脚本没有在真实Windows上运行验证。

## 判断依据

- GPU应识别为RTX3090；标准规格24GB，空闲显存以实际输出为准。
- `wsl --list --verbose`中目标发行版应为VERSION 2；本步不要求所有人已安装Ubuntu。
- `wsl --version`用于了解组件版本，老版WSL可能不支持该参数，不能仅凭这一项就判定GPU不可用。
- `nvidia-smi`表头中的CUDA兼容版本不是“已安装的CUDA Toolkit版本”；后续单独验证PyTorch能否使用CUDA。
- 接下来需要RAM与磁盘空间时再补充检查；不要求现在批量安装Python、Docker、CUDA、TensorRT。

NVIDIA官方明确支持WSL2中的CUDA，并说明WSL内不应另装Linux显示驱动。[CUDA on WSL文档](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)

## 为什么先不固定整套安装命令

上游摄像头示例与加速依赖有特定版本要求。先取得主机状态，再冻结本项目的Python/PyTorch/Diffusers等版本与模型修订。第一阶段可先用PyTorch路径验证，再加入TensorRT，避免把加速编译失败误认为模型不能运行。

[StreamDiffusion摄像头示例](https://github.com/cumulo-autumn/StreamDiffusion/tree/main/demo/realtime-img2img)

## 执行日志

### 2026-10-18：开始步骤1

- 用户选定3090 + Windows/WSL2，接受先200×200画面。
- 已准备本操作指南与只读PowerShell脚本。
- Windows版本、驱动版本、WSL发行版和GPU访问结果：待返回。
- 未安装环境、未下载权重、未启动摄像头、无FPS或延迟实测。
