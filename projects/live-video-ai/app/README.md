# 256×256 图像流基线

日期：2026-10-18。代码使用 SD-Turbo + Diffusers，先验证低分辨率单帧与顺序图像流，不声称复现Lucy或解决视频时序一致性。后续再对比StreamDiffusion加速与视频模型。

## 文件

- `verify_cuda.py`：GPU矩阵运算检查。
- `smoke_model.py`：合成图单帧测试，不读取摄像头或私人照片。
- `server.py`：仅监听localhost的FastAPI推理服务。
- `index.html`：摄像头、风格提示词、输出画面、延迟与有效FPS。
- `install-wsl.sh`、`requirements.in`：本项目隔离环境的安装配置。

## 本机运行（仅在3090主机的WSL中）

```bash
bash install-wsl.sh
.venv/bin/python verify_cuda.py
.venv/bin/python smoke_model.py
.venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8767 --ws-max-size 2100000
```

安装会下载多GB级依赖与模型文件，目录空间需求以实际下载为准。模型首次加载会联网，模型运行后不向第三方推理API发送摄像头画面。模型权重与缓存不提交到Git。

Windows浏览器使用 `http://localhost:8767`，是否由WSL转发成功须实际检查；Mac端通过SSH本地端口转发访问，不公开公网服务。

## 工作方式

客户端一次只发送一帧，收到结果后再捕获当前最新帧，避免输入队列无限积压。浏览器点击“开启摄像头”才请求权限，不自动开启；点击停止会停止轨道和连接。风格提示词点击应用后生效。

默认256×256推理，另提供512×512作为参考。SD-Turbo使用2个总步数、strength=0.5，按模型卡规则有效去噪步数为1；strength=1.0对应更强变换和2个有效步数。低步数下strength存在离散化，故没有放出多个看似可调但实际步数相同的档位。guidance_scale=0。

固定种子只减少随机扰动；本基线不是带时序建模的视频模型，仍可能闪烁、变形或改变身份。低分辨率下人物质量可能较差。服务器只缓存最近提示词的embedding，不保存摄像头帧。

模型耗时包含本次提示词embedding（若变化）与模型推理，另显示浏览器发送到收到结果的往返处理时间；后者不含完整相机硬件采集、解码显示与屏幕扫描延迟，不应叫完整glass-to-glass延迟。有效FPS按相邻结果解码完成的间隔测量，首帧显示预热中。

## 验证状态

代码已做Python/JavaScript语法检查。真实GPU验证、权重下载、256单帧、HTTP/WebSocket与摄像头联调的状态在[执行记录](../setup/README.md)逐项更新；不能仅凭页面完成就算模型已跑通。

## 模型版本

通过官方模型API核对并固定SD-Turbo修订 `b261bac6fd2cf515557d5d0707481eafa0485ec2`。下载使用safetensors；未将权重放进仓库。该版本已解析，模型运行与画质仍以执行记录为准。
