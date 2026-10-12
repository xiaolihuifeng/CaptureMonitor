# CaptureMonitor 屏幕自动采图工具

## 简介

CaptureMonitor 是一个 Windows 托盘应用程序：它周期性截取屏幕画面，与参考图（`reference_image`）做模板匹配；当匹配相似度连续多帧达到阈值时，自动保存当前画面截图。连续重复的画面通过感知哈希（dHash）去重，避免大量冗余文件。

程序入口为 `run.py`，调用 `capture_monitor.app.main()` 启动。

## 功能特性

- 驻留系统托盘运行，不占用任务栏，界面轻量。
- 按固定间隔（`capture_interval_ms`）抓屏并与参考图做模板匹配。
- 相似度 >= `match_threshold` 且连续 `min_confirm_frames` 帧满足时，自动触发采图。
- dHash 感知哈希去重：仅当感知哈希相近且帧间灰度差 <= `dedup_max_diff` 时判为重复（避免漏采局部变化的新图像），相邻帧判定为重复时跳过保存。
- 支持限定匹配区域（`match_region`）与多显示器（`monitor_index`）。
- 采图保存为 `cap_<YYYYmmdd_HHMMSS_mmm>.<png|jpg>`（时间戳精确到毫秒）。
- 全局快捷键采图（默认 `F9`，可在「采图列表」→「设置」修改；按下立即把当前屏幕存入 `Image/`）。
- 托盘菜单提供「采图列表」与「退出」；参数设置（保存目录 / 阈值 / 间隔等）可在「采图列表」窗口中修改。

## 目录结构

```
CaptureMonitor/
├── run.py                 # 程序入口（调用 capture_monitor.app.main()）
├── capture_monitor/       # 应用源码（tray、采图、配置等模块）
├── tests/                 # 测试
├── DEMO.png               # 演示用参考图（1920x1080）
├── assets/
│   ├── icon.png           # 256x256 应用图标
│   └── icon.ico           # 多尺寸 Windows 图标（16~256）
├── tools/
│   └── make_icon.py       # 图标生成脚本（Pillow）
├── requirements.txt       # 运行时依赖
├── requirements-build.txt # 打包依赖（含 PyInstaller）
├── CaptureMonitor.spec    # PyInstaller 打包配置
├── build.bat              # Windows 一键打包脚本
├── pyproject.toml         # 项目元数据与 pytest 配置
└── README.md
```

## 运行（开发）

```bat
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## 配置文件 config.json

配置文件位于程序目录（打包后即 EXE 所在目录）下的 `config.json`，首次运行自动生成默认值。

| 字段 | 说明 | 默认值 |
| --- | --- | --- |
| `reference_image` | 参考图路径（用于模板匹配） | `DEMO.png` |
| `save_dir` | 采图保存目录 | 程序所在目录下的 `Image` |
| `match_threshold` | 匹配相似度阈值（0~1） | `0.8` |
| `match_region` | 匹配区域（x, y, w, h），空表示整屏 | 空 |
| `capture_interval_ms` | 抓屏间隔（毫秒） | `1000` |
| `min_confirm_frames` | 连续确认帧数，达到后才触发采图 | `2` |
| `dedup_hamming_threshold` | dHash 去重汉明距离阈值，<= 视为重复 | `4` |
| `dedup_max_diff` | 帧间灰度平均绝对差阈值(0~1)，与哈希共同判定重复 | `0.008` |
| `monitor_index` | 显示器索引（多显示器） | `0` |
| `image_format` | 保存格式：`png` 或 `jpg` | `png` |
| `auto_start_monitor` | 启动后是否自动开始监控 | `true` |
| `hotkey` | 全局采图快捷键(如 F9 / Ctrl+Alt+S) | `F9` |
| `hotkey_enabled` | 是否启用全局快捷键采图 | `true` |

## 托盘菜单

托盘图标右键菜单包含两项：

- **采图列表**：打开采图列表窗口，可查看已保存的图片，并在该窗口中修改参数设置（保存目录、阈值、间隔等）。
- **退出**：退出程序。

## 采图保存位置

采图默认保存在程序所在目录下的 `Image` 文件夹，文件名格式为 `cap_<YYYYmmdd_HHMMSS_mmm>.<png|jpg>`。可通过 `config.json` 的 `save_dir` 字段（或「采图列表」窗口中的设置）自定义保存目录。

## 打包 EXE 步骤（Windows）

1. 在 Windows 上安装 Python 3.9+（勾选 Add to PATH）。
2. 将本项目完整拷贝到 Windows 机器。
3. 双击运行 `build.bat`，脚本会自动完成：
   - 创建虚拟环境 `.venv`（若不存在）；
   - 升级 pip；
   - 安装 `requirements-build.txt`（运行时依赖 + PyInstaller + Pillow）；
   - 执行 `pyinstaller --clean --noconfirm CaptureMonitor.spec`。
4. 打包完成后，在 `dist\CaptureMonitor.exe` 得到单文件、无控制台窗口的可执行程序。
5. 把 `DEMO.png` 与 `config.json`（可选，首次运行自动生成）放在 EXE 同目录即可使用。

说明：EXE 以窗口模式（`console=False`）打包，运行时不弹黑色控制台窗口；图标使用 `assets/icon.ico`，`DEMO.png` 与 `assets/icon.png` 已作为数据文件打进 EXE 内部。

## 云端构建 EXE（GitHub Actions，无需本地 Windows 环境）

若本地 Windows 打包受阻（例如杀软锁定 `d3dcompiler_47.dll`），可用 GitHub Actions 在云端 Windows 机器上自动打包：

1. 在 GitHub 新建仓库，把本项目推上去：
   ```bash
   cd CaptureMonitor
   git init
   git add .
   git commit -m "CaptureMonitor: screen capture tray tool"
   git branch -M main
   git remote add origin https://github.com/<你的用户名>/CaptureMonitor.git
   git push -u origin main
   ```
2. 推送后进入仓库 **Actions** 标签 → 运行 `Build Windows EXE`（push 或手动触发都会跑）。
3. 构建完成后，在该次运行页面底部 **Artifacts** 下载 `CaptureMonitor-windows`（含 `CaptureMonitor.exe` 与 `DEMO.png`）。
4. 打 tag 推送时（如 `v1.0.0`），会自动把 EXE 附加到 GitHub Release：
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

工作流文件：`.github/workflows/build-windows.yml`（Python 3.12 + PyInstaller，**先跑测试再打包**）。

## 使用 DEMO.png 测试

1. 运行程序（开发模式或打包后的 EXE）。
2. 确保 `config.json` 中 `reference_image` 指向 `DEMO.png`（默认即可）。
3. 在屏幕上显示 DEMO.png（例如用图片查看器打开它）。
4. 程序抓屏与参考图匹配成功后（达到阈值并连续确认），会自动把屏幕画面保存到 `Image` 目录。
5. 打开托盘菜单「采图列表」查看结果，或在 `Image` 目录检查 `cap_*.png` 文件。

## 技术栈

- PyQt5（托盘与界面）
- OpenCV（抓屏、模板匹配、感知哈希）
- numpy（图像数值计算）
- PyInstaller（打包 EXE）

## 打包常见问题

**`ERROR: Could not install packages due to an OSError: [Errno 13] Permission denied: ...PyQt5\Qt5\bin\d3dcompiler_47.dll`**

这是 Windows 环境问题（不是代码问题），按顺序尝试：

1. **关闭占用该目录的程序**：编辑器（VS Code）、资源管理器预览、云同步（OneDrive/坚果云等）。
2. **杀毒软件拦截**：Windows Defender / 360 / 火绒 在解压 DLL 时会短暂锁文件，导致拒绝访问。
   把 `D:\AI_View\CaptureMonitor` 加入杀软**排除/信任目录**，或临时关闭实时防护后重试。
3. **删除残留的 `.venv` 重建**（最常见有效）：
   ```bat
   rmdir /s /q .venv
   build.bat
   ```
4. **以管理员身份运行** `build.bat`（右键 → 以管理员身份运行）。
5. 网络代理/镜像异常时，可显式指定镜像：
   ```bat
   pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements-build.txt
   ```

新版 `build.bat` 已内置 **3 次自动重试**（并加 `--no-cache-dir`）以规避杀软瞬时锁文件；失败时会打印上面的排查提示。

**手动打包等价命令**：

```bat
cd /d D:\AI_View\CaptureMonitor
rmdir /s /q .venv
python -m venv .venv
call .venv\Scripts\activate
pip install --no-cache-dir -r requirements-build.txt
pyinstaller --clean --noconfirm CaptureMonitor.spec
```

成功后产物在 `dist\CaptureMonitor.exe`；把 `DEMO.png` 放到 EXE 同目录即可运行。
