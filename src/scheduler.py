#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冰块制造机定时任务调度器
该程序设计为在服务器上长期运行，自动执行每日定时任务
"""

import os
import sys
import time
import logging
from datetime import datetime
from request import Request
import config
import pytz
import threading

# 获取当前文件所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 日志文件路径
log_file = os.path.join(current_dir, "ice_maker_scheduler.log")
# PID文件路径
pid_file = os.path.join(current_dir, "ice_maker_scheduler.pid")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_current_time_in_multiple_timezones():
    """获取多个时区的当前时间"""
    now_utc = datetime.now(pytz.UTC)
    now_shanghai = now_utc.astimezone(pytz.timezone("Asia/Shanghai"))  # 东八区
    now_vancouver = now_utc.astimezone(pytz.timezone("America/Vancouver"))  # 温哥华时间(太平洋时间)
    now_mountain = now_utc.astimezone(pytz.timezone("US/Mountain"))  # 山地时间(MDT)
    
    return {
        "UTC": now_utc,
        "UTC+08:00 (东八区/上海)": now_shanghai,
        "UTC-07:00 (温哥华/山地时间)": now_mountain
    }

def verify_timezone_mapping(timezone_str):
    """Verify and return the correct timezone mapping"""
    if timezone_str == "UTC-07:00":
        # Prefer Vancouver timezone, fallback to US/Mountain
        try:
            pytz.timezone("America/Vancouver")
            logger.info("Using America/Vancouver timezone")
            return "America/Vancouver"  # Vancouver timezone
        except:
            logger.info("Using US/Mountain timezone")
            return "US/Mountain"  # Mountain time (MDT)
    elif timezone_str == "UTC+08:00":
        return "Asia/Shanghai"  # Shanghai timezone
    else:
        logger.warning(f"Unknown timezone setting: {timezone_str}, using UTC")
        return "UTC"

def display_current_times():
    """Display current time in different timezones for debugging"""
    now_utc = datetime.now(pytz.UTC)
    now_vancouver = now_utc.astimezone(pytz.timezone("America/Vancouver"))
    now_shanghai = now_utc.astimezone(pytz.timezone("Asia/Shanghai"))
    
    logger.info("Current Time Check (Time Only):")
    logger.info(f"UTC Time: {now_utc.strftime('%H:%M:%S')}")
    logger.info(f"Vancouver Time: {now_vancouver.strftime('%H:%M:%S')}")
    logger.info(f"Shanghai Time: {now_shanghai.strftime('%H:%M:%S')}")

def run_scheduler():
    """Run the scheduler to manage ice maker"""
    # Load config
    api_key = config.api_key
    api_key_value = config.api_key_value
    sku = config.sku
    device_id = config.device
    daily_control_time_file = config.daily_control_time_load
    timezone = config.timezone
    
    # Convert timezone format
    from_timezone = verify_timezone_mapping(timezone)
    
    logger.info(f"Starting Ice Maker Scheduler")
    logger.info(f"Timezone setting: {timezone} ({from_timezone})")
    logger.info(f"Device: {sku} - {device_id}")
    
    # Display current time in different timezones
    display_current_times()
    
    # Initialize request object
    ice_maker = Request(api_key, api_key_value)
    
    # Check if we can connect to the device
    devices_result = ice_maker.get_devices()
    if devices_result["code"] != 200:
        logger.error(f"Failed to get devices: {devices_result}")
        logger.error("Check API key and network connection")
        return
    
    logger.info("Device connection successful")
    
    # Set up initial daily tasks
    ice_maker.setup_daily_tasks(sku, device_id, from_timezone=from_timezone, 
                              config_file=daily_control_time_file)
    
    # Run first check immediately
    logger.info("Running initial task check")
    ice_maker.check_scheduled_tasks()
    
    # Set up periodic task checking
    interval = 300  # 5 minutes in seconds
    logger.info(f"Starting scheduler loop with {interval} seconds interval")
    
    try:
        while True:
            # Wait for the next interval
            time.sleep(interval)
            
            # Set up daily tasks again in case of changes
            ice_maker.setup_daily_tasks(sku, device_id, from_timezone=from_timezone,
                                       config_file=daily_control_time_file)
            
            # Display current time for debugging
            display_current_times()
            
            # Check scheduled tasks
            ice_maker.check_scheduled_tasks()
            
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}", exc_info=True)

def run_as_daemon():
    """以守护进程方式运行（仅支持Linux/Unix系统）"""
    try:
        # 检查操作系统
        if os.name != 'posix':
            logger.warning("守护进程模式仅支持Linux/Unix系统，将以普通模式运行")
            run_scheduler()
            return
            
        # 第一次fork
        pid = os.fork()
        if pid > 0:
            # 父进程退出
            logger.info(f"守护进程第一次fork, 子进程PID: {pid}")
            sys.exit(0)
            
        # 脱离控制终端
        os.setsid()
        os.umask(0)
        
        # 第二次fork
        pid = os.fork()
        if pid > 0:
            # 第二个父进程退出
            logger.info(f"守护进程第二次fork, 子进程PID: {pid}")
            sys.exit(0)
            
        # 重定向标准输入输出
        sys.stdout.flush()
        sys.stderr.flush()
        
        with open('/dev/null', 'r') as f:
            os.dup2(f.fileno(), sys.stdin.fileno())
        with open(log_file, 'a+') as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
            os.dup2(f.fileno(), sys.stderr.fileno())
            
        # 切换到当前目录
        os.chdir(current_dir)
        
        logger.info(f"调度器已以守护进程模式启动，PID: {os.getpid()}")
        
        # 运行调度器
        run_scheduler()
        
    except Exception as e:
        logger.error(f"启动守护进程失败: {e}", exc_info=True)
        run_scheduler()  # 尝试以普通模式运行

def create_systemd_service():
    """创建systemd服务文件"""
    try:
        # 检查是否是Linux系统
        if os.name != 'posix':
            logger.warning("创建systemd服务仅支持Linux系统")
            return False
            
        # 获取当前用户
        import getpass
        current_user = getpass.getuser()
        
        # 获取当前脚本的绝对路径
        script_path = os.path.abspath(__file__)
        work_dir = os.path.dirname(script_path)
        
        # 创建服务文件内容
        service_content = f"""[Unit]
Description=Ice Maker Scheduler Service
After=network.target

[Service]
Type=simple
User={current_user}
WorkingDirectory={work_dir}
ExecStart=/usr/bin/python3 {script_path}
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
"""
        
        # 保存服务文件到当前目录
        service_file_path = os.path.join(current_dir, "ice-maker.service")
        with open(service_file_path, 'w') as f:
            f.write(service_content)
            
        logger.info(f"systemd服务文件已创建: {service_file_path}")
        logger.info("要安装此服务，请执行以下命令:")
        logger.info(f"sudo cp {service_file_path} /etc/systemd/system/")
        logger.info(f"sudo systemctl daemon-reload")
        logger.info(f"sudo systemctl start ice-maker")
        logger.info(f"sudo systemctl enable ice-maker")
        
        return True
    except Exception as e:
        logger.error(f"创建systemd服务文件失败: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='冰块制造机定时任务调度器')
    parser.add_argument('-d', '--daemon', action='store_true', help='以守护进程模式运行（仅Linux/Unix）')
    parser.add_argument('-s', '--systemd', action='store_true', help='创建systemd服务文件（仅Linux）')
    args = parser.parse_args()
    
    if args.systemd:
        create_systemd_service()
    elif args.daemon:
        run_as_daemon()
    else:
        run_scheduler() 