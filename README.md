# Ice Maker Controller

这是一个用于控制 Govee 智能制冰机的 Python 应用程序。通过 Govee API，可以实现对制冰机的远程控制，包括开关机、设置工作模式以及定时启动功能。

## 功能特点

- 获取设备信息
- 远程开关机
- 设置工作模式（大/中/小冰块）
- 定时任务功能
  - 支持单次定时任务
  - 支持每日定时任务（通过配置文件设置）
- 跨时区支持（用户在西七区，设备在东八区）
- 支持服务器长期运行模式

## 安装依赖

```bash
pip install -r src/requirements.txt
```

## 使用方法

### 交互式界面

```bash
cd src
python main.py
```

### 后台调度器（服务器模式）

我们提供了一个专门的调度器程序，可以在服务器上长期运行，不需要用户交互：

```bash
cd src
# 普通模式运行
python scheduler.py

# 守护进程模式运行（仅Linux/Unix）
python scheduler.py -d

# 创建systemd服务文件（仅Linux）
python scheduler.py -s
```

#### Linux 服务器安装步骤

1. **普通运行**

   ```bash
   cd src
   python3 scheduler.py
   ```

2. **守护进程模式**

   ```bash
   cd src
   python3 scheduler.py -d
   ```

3. **作为 systemd 服务运行（推荐）**

   ```bash
   # 创建服务文件
   cd src
   python3 scheduler.py -s

   # 安装服务（按照提示的命令执行）
   sudo cp ice-maker.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl start ice-maker
   sudo systemctl enable ice-maker

   # 查看服务状态
   sudo systemctl status ice-maker

   # 查看日志
   tail -f ice_maker_scheduler.log
   ```

4. **使用 screen 或 tmux**

   ```bash
   screen -S ice-maker
   cd src
   python3 scheduler.py
   # 按 Ctrl+A 然后按 D 分离会话
   ```

5. **使用 nohup**
   ```bash
   cd src
   nohup python3 scheduler.py > /dev/null 2>&1 &
   ```

所有日志都会保存在当前目录下的`ice_maker_scheduler.log`文件中。

## 定时任务

该应用支持两种定时任务方式：

### 1. 单次定时任务

通过程序界面手动设置特定时间的单次任务。

### 2. 每日定时任务

通过配置文件`dailycontrollertime.txt`设置每日固定时间的任务。配置文件格式如下：

```
openlist:7:00,17:00
closelist:12:00,23:59
```

说明：

- `openlist`: 每日开机时间列表，多个时间用逗号分隔
- `closelist`: 每日关机时间列表，多个时间用逗号分隔

这些时间基于西七区（美国山地时间），程序会自动将其转换为设备所在的东八区（中国时间）。

您可以通过程序界面中的"查看每日定时任务"选项查看并修改这些定时任务。

## 配置文件

系统使用`config.py`文件存储所有配置项：

```python
api_key = "Govee-API-Key"  # API密钥名称
api_key_value = "your_api_key_here"  # API密钥值
daily_control_time_load = "dailycontrollertime.txt"  # 定时任务配置文件
sku = "H7172"  # 设备型号
device = "2E:78:D0:C9:07:8D:78:A0"  # 设备ID
timezone = "UTC-07:00"  # 时区设置
```

## API 说明

### Request 类

主要类，提供以下方法：

- `get_devices()`: 获取设备列表
- `open_device(sku, device_id)`: 开启设备
- `close_device(sku, device_id)`: 关闭设备
- `set_work_mode(sku, device_id, mode)`: 设置工作模式
- `schedule_with_timezone(sku, device_id, action_type, target_time)`: 设置单次定时任务
- `read_daily_controller_times(file_path)`: 从配置文件读取每日定时任务
- `setup_daily_tasks(sku, device_id)`: 设置每日定时任务
- `start_scheduler()`: 启动定时任务调度器

## 示例

```python
# 初始化
api_key = "Govee-API-Key"
api_key_value = "your_api_key_here"
controller = Request(api_key, api_key_value)

# 获取设备列表
devices = controller.get_devices()

# 开启设备
controller.open_device("H7172", "2E:78:D0:C9:07:8D:78:A0")

# 设置单次定时任务（西七区时间）
controller.schedule_with_timezone(
    "H7172", "2E:78:D0:C9:07:8D:78:A0",
    "open", "2023-08-10 08:00:00"
)

# 设置每日定时任务
controller.setup_daily_tasks("H7172", "2E:78:D0:C9:07:8D:78:A0")

# 启动定时任务调度器
controller.start_scheduler()
```

## 注意事项

- 请确保网络连接稳定
- API 密钥需要保密
- 定时任务每 5 分钟检查一次
- 系统会自动处理时区转换
- 配置文件`dailycontrollertime.txt`需要放在程序运行目录下
