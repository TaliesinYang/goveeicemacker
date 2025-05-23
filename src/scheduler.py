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

def run_scheduler():
    """运行调度器主函数"""
    try:
        # 记录进程ID
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"进程ID: {os.getpid()}, PID文件保存在: {pid_file}")
            
        # 读取配置
        api_key = config.api_key
        api_key_value = config.api_key_value
        sku = config.sku
        device_id = config.device
        daily_control_time_file = os.path.join(current_dir, config.daily_control_time_load)
        timezone = config.timezone
        
        # 转换时区格式
        from_timezone = "US/Mountain"  # 默认西七区
        if timezone == "UTC-07:00":
            from_timezone = "US/Mountain"
        elif timezone == "UTC+08:00":
            from_timezone = "Asia/Shanghai"
        
        logger.info(f"启动冰块制造机调度器")
        logger.info(f"时区: {timezone} ({from_timezone})")
        logger.info(f"设备: {sku} - {device_id}")
        logger.info(f"API密钥: {api_key}")
        logger.info(f"定时任务配置文件: {daily_control_time_file}")
        logger.info(f"日志文件保存在: {log_file}")
        
        # 初始化请求对象
        ice_maker = Request(api_key, api_key_value)
        
        # 获取设备信息
        devices_result = ice_maker.get_devices()
        if devices_result["code"] != 200:
            logger.warning(f"获取设备信息失败: {devices_result}")
            logger.warning("将使用配置文件中的设备信息继续运行")
        else:
            logger.info("成功获取设备信息")
            for device in devices_result.get("data", []):
                logger.info(f"设备: {device.get('deviceName', 'Unknown')} ({device.get('device', 'Unknown')})")
        
        # 读取定时任务配置
        times = ice_maker.read_daily_controller_times(daily_control_time_file)
        logger.info(f"每日开机时间: {', '.join(times['open'])}")
        logger.info(f"每日关机时间: {', '.join(times['close'])}")
        
        # 设置设备每日任务
        ice_maker.setup_daily_tasks(sku, device_id, from_timezone=from_timezone, config_file=daily_control_time_file)
        
        # 启动无限循环的调度器
        logger.info("调度器已启动，每5分钟检查一次定时任务")
        
        # 保存启动时间
        start_time = datetime.now()
        
        # 开始调度循环
        while True:
            try:
                # 立即检查一次任务（不等待第一次5分钟）
                logger.info("执行定时任务检查...")
                
                # 检查定时任务
                ice_maker.check_scheduled_tasks()
                
                # 每天重新加载一次任务
                current_time = datetime.now()
                if current_time.day != start_time.day:
                    logger.info("日期变更，重新加载定时任务")
                    ice_maker.setup_daily_tasks(sku, device_id, from_timezone=from_timezone, config_file=daily_control_time_file)
                    start_time = current_time
                
                # 等待5分钟
                logger.info(f"下一次检查将在5分钟后进行")
                time.sleep(300)
            except Exception as e:
                logger.error(f"调度循环中发生错误: {e}", exc_info=True)
                # 出错后等待30秒再继续
                time.sleep(30)
                
    except KeyboardInterrupt:
        logger.info("调度器被用户中断")
    except Exception as e:
        logger.error(f"调度器启动失败: {e}", exc_info=True)
    finally:
        # 清理PID文件
        if os.path.exists(pid_file):
            try:
                os.remove(pid_file)
                logger.info(f"已删除PID文件: {pid_file}")
            except:
                pass

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