# 256×256 图像流基线

日期：2026-10-18。代码使用 SD-Turbo + Diffusers，先验证低分辨率单帧与顺序图像流，不声称复现Lucy或解决视频时序一致性。后续再对比StreamDiffusion加速与视频模型。

## 文件

- `verify_cuda.py`：GPU矩阵运算检查。
- `benchmark.py`：预热后分别连续测试256与512，记录吞吐量、延迟、显存和GPU板卡功耗。
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

## 连续测试与成本口径

运行 `.venv/bin/python benchmark.py`：每种尺寸先预热3帧，再连续处理至少30秒且至少60帧；输入是移动的合成图形，结果在忽略的 `artifacts/benchmark.json`。每0.5秒尝试读取一次nvidia-smi板卡功耗。测试吞吐包含合成图、JPEG/base64与服务器推理，不包含浏览器、网络和摄像头。

页面另提供“合成画面测试（60秒）”，经过真实WebSocket与GPU模型，明确标注为合成输入，不冒充摄像头帧率。测试会自动停止。

成本分别记录：GPU板卡用电量（实测功率折算）、整机电费（需要插座功耗与实际电价）、设备折旧（购置/残值与使用时数假设）、云租赁参考；已有设备不产生新的GPU租金，但不等于整机运行免费。

## 已验证结果与服务管理

[2026-10-18实测报告](../benchmarks/2026-10-18/README.md)：256服务端7.06 FPS，Mac经SSH客户端5.54 FPS，浏览器60秒合成图显示平均5.0 FPS。显存、功耗、冷启动与边界见报告；真人摄像头尚待权限与画面验收。

当前主机启用了WSL systemd，可在项目目录运行：

```bash
bash start-service.sh
systemctl status liveai-style-v1.service
journalctl -u liveai-style-v1.service -n 40 --no-pager
systemctl stop liveai-style-v1.service
```

脚本启动临时systemd服务，使用已经下载的本地模型缓存；首次安装需先完成权重下载。服务不依赖SSH安装会话，WSL关闭后停止，不会开机自启。Mac端的SSH转发仍需保持连接。浏览器打开 `http://127.0.0.1:8767`；摄像头权限需要在实际使用的浏览器中允许。

摄像头等待期间可点击停止；健康状态轮询不会反复启用启动按钮，迟到的摄像头请求会关闭已取得的轨道。合成测试只用于验证真实模型和显示链路，60秒自动停止。
