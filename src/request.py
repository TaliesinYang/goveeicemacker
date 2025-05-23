#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import uuid
import time
import os
from datetime import datetime, timedelta, date
import pytz
import json
import logging

# 获取logger
logger = logging.getLogger(__name__)

class Request:
    def __init__(self, api_key, api_key_value):
        self.api_key = api_key
        self.api_key_value = api_key_value
        self.base_url = "https://openapi.api.govee.com"
        self.headers = {
            "Content-Type": "application/json",
            self.api_key: self.api_key_value
        }
        # 设备信息缓存
        self.devices = None
        # 定时任务列表 [(设备ID, 操作类型, 目标时间)]
        self.scheduled_tasks = []
        # 已加载的日期
        self.loaded_date = None
        # 上次使用的配置文件路径
        self.last_config_file = None
        # 标记每日任务是否已执行
        self._daily_tasks_executed = False
        # 最后一次检查的日期
        self.last_check_date = date.today()

    def get_devices(self):
        """获取所有设备信息"""
        url = f"{self.base_url}/router/api/v1/user/devices"
        try:
            response = requests.get(url, headers=self.headers)
            
            # 检查响应状态码
            if response.status_code != 200:
                print(f"API请求失败: 状态码 {response.status_code}")
                print(f"响应内容: {response.text}")
                return {"code": response.status_code, "message": "API请求失败", "data": []}
            
            # 尝试解析JSON响应
            try:
                result = response.json()
                
                if result.get("code") == 200:
                    self.devices = result.get("data", [])
                
                return result
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {e}")
                print(f"响应内容: {response.text}")
                return {"code": 500, "message": "JSON解析错误", "data": []}
            
        except requests.RequestException as e:
            print(f"请求异常: {e}")
            return {"code": 500, "message": f"请求异常: {str(e)}", "data": []}
    
    def control_device(self, sku, device_id, power_status):
        """控制设备开关
        
        Args:
            sku: 设备型号
            device_id: 设备ID
            power_status: 1表示开机，0表示关机
        """
        url = f"{self.base_url}/router/api/v1/device/control"
        
        payload = {
            "requestId": str(uuid.uuid4()),
            "payload": {
                "sku": sku,
                "device": device_id,
                "capability": {
                    "type": "devices.capabilities.on_off",
                    "instance": "powerSwitch",
                    "value": power_status
                }
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            
            # 检查响应状态码
            if response.status_code != 200:
                print(f"API请求失败: 状态码 {response.status_code}")
                print(f"响应内容: {response.text}")
                return {"code": response.status_code, "message": "API请求失败"}
            
            # 尝试解析JSON响应
            try:
                return response.json()
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {e}")
                print(f"响应内容: {response.text}")
                return {"code": 500, "message": "JSON解析错误"}
                
        except requests.RequestException as e:
            print(f"请求异常: {e}")
            return {"code": 500, "message": f"请求异常: {str(e)}"}
    
    def open_device(self, sku, device_id):
        """开启设备"""
        return self.control_device(sku, device_id, 1)
    
    def close_device(self, sku, device_id):
        """关闭设备"""
        return self.control_device(sku, device_id, 0)
    
    def set_work_mode(self, sku, device_id, mode):
        """设置工作模式
        
        Args:
            sku: 设备型号
            device_id: 设备ID
            mode: 工作模式 1-LargeIce, 2-MediumIce, 3-SmallIce
        """
        url = f"{self.base_url}/router/api/v1/device/control"
        
        payload = {
            "requestId": str(uuid.uuid4()),
            "payload": {
                "sku": sku,
                "device": device_id,
                "capability": {
                    "type": "devices.capabilities.work_mode",
                    "instance": "workMode",
                    "value": {
                        "workMode": mode,
                        "modeValue": 0
                    }
                }
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            
            # 检查响应状态码
            if response.status_code != 200:
                print(f"API请求失败: 状态码 {response.status_code}")
                print(f"响应内容: {response.text}")
                return {"code": response.status_code, "message": "API请求失败"}
            
            # 尝试解析JSON响应
            try:
                return response.json()
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {e}")
                print(f"响应内容: {response.text}")
                return {"code": 500, "message": "JSON解析错误"}
                
        except requests.RequestException as e:
            print(f"请求异常: {e}")
            return {"code": 500, "message": f"请求异常: {str(e)}"}
    
    def schedule_task(self, sku, device_id, action_type, target_time_utc):
        """设置定时任务
        
        Args:
            sku: 设备型号
            device_id: 设备ID
            action_type: "open" 或 "close"
            target_time_utc: UTC时间格式的目标时间
        """
        self.scheduled_tasks.append((sku, device_id, action_type, target_time_utc))
        print(f"已设置任务: 设备{device_id} 将在 {target_time_utc} (UTC时间) {action_type}")
    
    def schedule_with_timezone(self, sku, device_id, action_type, target_time, from_timezone="America/Vancouver", to_timezone="Asia/Shanghai"):
        """设置定时任务，处理时区转换
        
        Args:
            sku: 设备型号
            device_id: 设备ID
            action_type: "open" 或 "close"
            target_time: 格式为 "YYYY-MM-DD HH:MM:SS" 的目标时间字符串
            from_timezone: 输入时间的时区，默认为温哥华时区 (America/Vancouver)
            to_timezone: 设备所在时区，默认为东八区 (Asia/Shanghai)
        """
        # 将输入时间转换为 UTC 时间
        source_tz = pytz.timezone(from_timezone)
        target_tz = pytz.timezone(to_timezone)
        
        # 解析输入时间
        local_dt = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
        
        # 添加时区信息
        local_dt = source_tz.localize(local_dt)
        
        # 转换为UTC时间
        utc_dt = local_dt.astimezone(pytz.UTC)
        
        # 设置任务
        self.schedule_task(sku, device_id, action_type, utc_dt)
    
    def read_daily_controller_times(self, file_path="dailycontrollertime.txt"):
        """从配置文件读取每日定时任务
        
        Args:
            file_path: 配置文件路径
        
        Returns:
            dict: 包含open和close时间列表的字典
        """
        # 保存最后使用的配置文件路径
        self.last_config_file = file_path
        
        times = {"open": [], "close": []}
        
        try:
            if not os.path.exists(file_path):
                print(f"配置文件 {file_path} 不存在，将创建默认配置文件")
                # 创建默认配置文件
                with open(file_path, 'w') as f:
                    f.write("openlist:7:00,17:00\n")
                    f.write("closelist:12:00,23:59")
                return {"open": ["7:00", "17:00"], "close": ["12:00", "23:59"]}
            
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("openlist:"):
                        open_times = line.replace("openlist:", "").split(",")
                        times["open"] = [t.strip() for t in open_times]
                    elif line.startswith("closelist:"):
                        close_times = line.replace("closelist:", "").split(",")
                        times["close"] = [t.strip() for t in close_times]
            return times
        except Exception as e:
            print(f"读取配置文件失败: {e}")
            return times
    
    def setup_daily_tasks(self, sku, device_id, from_timezone="America/Vancouver", config_file=None):
        """Set up daily scheduled tasks
        
        Args:
            sku: Device model
            device_id: Device ID
            from_timezone: Input timezone, default is Vancouver timezone (America/Vancouver)
            config_file: Config file path, if None use last path or default
        """
        # Ensure timezone name is correct
        if from_timezone == "US/Mountain":
            # Prefer Vancouver timezone
            try:
                pytz.timezone("America/Vancouver")
                from_timezone = "America/Vancouver"
                logger.info("Timezone changed from US/Mountain to America/Vancouver")
            except:
                logger.info("Using US/Mountain timezone")
        
        # Get today's date
        today = date.today()
        
        # Check if it's a new day
        if self.last_check_date != today:
            logger.info(f"Date change detected: {self.last_check_date} -> {today}")
            # Reset daily task execution flag
            self._daily_tasks_executed = False
            self.last_check_date = today
        
        # If today's tasks already loaded and executed, skip
        if self.loaded_date == today and self._daily_tasks_executed:
            logger.info("Today's daily tasks already set and executed, skipping")
            return
        
        # Determine config file path
        if config_file is None:
            config_file = self.last_config_file or "dailycontrollertime.txt"
        
        # Read config file
        controller_times = self.read_daily_controller_times(config_file)
        
        # Get timezone object
        source_tz = pytz.timezone(from_timezone)
        
        # Clear previous tasks
        # Keep only non-daily tasks
        self.scheduled_tasks = [task for task in self.scheduled_tasks 
                                if not task[2].startswith("daily_")]
        
        logger.info(f"Setting up daily tasks using timezone: {from_timezone}")
        
        # Set up power on tasks
        for time_str in controller_times["open"]:
            try:
                # Parse time string (HH:MM)
                if ":" not in time_str:
                    logger.error(f"Invalid time format: {time_str}, should be HH:MM")
                    continue
                
                hour, minute = map(int, time_str.split(":"))
                
                # Build today's datetime
                now = datetime.now()
                task_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # Add timezone info - This is Vancouver time (UTC-7)
                local_dt = source_tz.localize(task_time)
                
                # Convert to UTC time
                utc_dt = local_dt.astimezone(pytz.UTC)
                
                # Convert to Shanghai time (for logging)
                china_dt = utc_dt.astimezone(pytz.timezone("Asia/Shanghai"))
                
                # Add task
                self.scheduled_tasks.append((sku, device_id, "daily_open", utc_dt))
                
                logger.info(f"Daily Power On Task Set:")
                logger.info(f" - Time: {hour:02d}:{minute:02d}")
                logger.info(f" - Vancouver Time: {local_dt.strftime('%H:%M:%S')} ({from_timezone})")
                logger.info(f" - UTC Time: {utc_dt.strftime('%H:%M:%S')}")
                logger.info(f" - Shanghai Time: {china_dt.strftime('%H:%M:%S')}")
                
            except ValueError as e:
                logger.error(f"Time format error: {time_str}, error: {e}")
        
        # Set up power off tasks
        for time_str in controller_times["close"]:
            try:
                # Parse time string (HH:MM)
                if ":" not in time_str:
                    logger.error(f"Invalid time format: {time_str}, should be HH:MM")
                    continue
                    
                hour, minute = map(int, time_str.split(":"))
                
                # Build today's datetime
                now = datetime.now()
                task_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # Add timezone info - This is Vancouver time (UTC-7)
                local_dt = source_tz.localize(task_time)
                
                # Convert to UTC time
                utc_dt = local_dt.astimezone(pytz.UTC)
                
                # Convert to Shanghai time (for logging)
                china_dt = utc_dt.astimezone(pytz.timezone("Asia/Shanghai"))
                
                # Add task
                self.scheduled_tasks.append((sku, device_id, "daily_close", utc_dt))
                
                logger.info(f"Daily Power Off Task Set:")
                logger.info(f" - Time: {hour:02d}:{minute:02d}")
                logger.info(f" - Vancouver Time: {local_dt.strftime('%H:%M:%S')} ({from_timezone})")
                logger.info(f" - UTC Time: {utc_dt.strftime('%H:%M:%S')}")
                logger.info(f" - Shanghai Time: {china_dt.strftime('%H:%M:%S')}")
                
            except ValueError as e:
                logger.error(f"Time format error: {time_str}, error: {e}")
        
        # Update loaded date
        self.loaded_date = today
    
    def check_scheduled_tasks(self):
        """Check and execute scheduled tasks, runs every 5 minutes"""
        # Get current UTC time
        current_time_utc = datetime.now(pytz.UTC)
        # Get current times in different timezones
        current_time_shanghai = current_time_utc.astimezone(pytz.timezone("Asia/Shanghai"))
        current_time_vancouver = current_time_utc.astimezone(pytz.timezone("America/Vancouver"))
        
        logger.info(f"Current Time Check:")
        logger.info(f" - UTC Time: {current_time_utc.strftime('%H:%M:%S')}")
        logger.info(f" - Shanghai Time (UTC+8): {current_time_shanghai.strftime('%H:%M:%S')}")
        logger.info(f" - Vancouver Time (UTC-7): {current_time_vancouver.strftime('%H:%M:%S')}")
        
        completed_tasks = []
        
        for index, (sku, device_id, action_type, target_time) in enumerate(self.scheduled_tasks):
            # Convert target time to different timezones (for logging)
            target_shanghai = target_time.astimezone(pytz.timezone("Asia/Shanghai"))
            target_vancouver = target_time.astimezone(pytz.timezone("America/Vancouver"))
            
            # Extract only hours and minutes for comparison
            current_hour, current_minute = current_time_shanghai.hour, current_time_shanghai.minute
            target_hour, target_minute = target_shanghai.hour, target_shanghai.minute
            
            # Convert to total minutes for easy comparison
            current_total_minutes = current_hour * 60 + current_minute
            target_total_minutes = target_hour * 60 + target_minute
            
            # Calculate time difference (minutes) - only consider time within 24 hours
            if target_total_minutes <= current_total_minutes:
                # Target time has already passed today
                time_diff_minutes = current_total_minutes - target_total_minutes
                time_status = "passed"
            else:
                # Target time hasn't arrived yet today
                time_diff_minutes = target_total_minutes - current_total_minutes
                time_status = "upcoming"
            
            # Log task details
            logger.info(f"Checking Task {index+1}: {action_type}")
            logger.info(f" - Target Time (UTC): {target_time.strftime('%H:%M:%S')}")
            logger.info(f" - Target Time (Shanghai): {target_shanghai.strftime('%H:%M:%S')}")
            logger.info(f" - Target Time (Vancouver): {target_vancouver.strftime('%H:%M:%S')}")
            logger.info(f" - Time Comparison: Target {target_hour:02d}:{target_minute:02d} vs Current {current_hour:02d}:{current_minute:02d}")
            logger.info(f" - Time Difference: {time_diff_minutes} minutes ({time_status})")
            
            # Determine if task should be executed
            should_execute = False
            
            # For daily tasks, execute if the time has just passed (within 5 minutes)
            if action_type.startswith("daily_") and time_status == "passed" and time_diff_minutes <= 5:
                should_execute = True
                logger.info(f" - Decision: Execute (daily task, passed {time_diff_minutes} minutes ago)")
            
            # For one-time tasks, use traditional UTC time comparison
            elif not action_type.startswith("daily_"):
                # Calculate UTC time difference (minutes)
                utc_time_diff = (current_time_utc - target_time).total_seconds() / 60
                if 0 <= utc_time_diff <= 10:
                    should_execute = True
                    logger.info(f" - Decision: Execute (one-time task, UTC diff: {utc_time_diff:.2f} minutes)")
                elif utc_time_diff > 10:
                    # One-time task expired too long ago
                    logger.warning(f" - Decision: One-time task expired {utc_time_diff:.2f} minutes ago, will be removed")
                    completed_tasks.append(index)
                    continue
                else:
                    logger.info(f" - Decision: Not yet time to execute, wait ~{-utc_time_diff:.2f} minutes")
                    continue
            
            # Execute task
            if should_execute:
                if action_type == "open" or action_type == "daily_open":
                    logger.info(f"Executing Power On: Device {device_id}")
                    result = self.open_device(sku, device_id)
                    logger.info(f"Power On Result: {result}")
                elif action_type == "close" or action_type == "daily_close":
                    logger.info(f"Executing Power Off: Device {device_id}")
                    result = self.close_device(sku, device_id)
                    logger.info(f"Power Off Result: {result}")
                
                # Mark task as completed
                completed_tasks.append(index)
        
        # Remove completed or expired tasks
        for index in sorted(completed_tasks, reverse=True):
            task_info = self.scheduled_tasks[index]
            if task_info[2].startswith("daily_"):
                logger.info(f"Completed Daily Task: {task_info[2]}, Scheduled Time: {task_info[3].strftime('%H:%M:%S')}")
            else:
                logger.info(f"Removing Task: {task_info[2]}, Scheduled Time: {task_info[3].strftime('%H:%M:%S')}")
            del self.scheduled_tasks[index]
            
        # If all daily tasks are completed for the day, set a flag to avoid repeating execution
        self._daily_tasks_executed = True
    
    def start_scheduler(self, interval=300):
        """启动定时任务调度器
        
        Args:
            interval: 检查间隔，默认300秒(5分钟)
        """
        try:
            while True:
                # If device list is empty, try to get devices
                if not self.devices:
                    self.get_devices()
                
                # If there are devices, set daily tasks
                if self.devices:
                    for device in self.devices:
                        self.setup_daily_tasks(device["sku"], device["device"])
                
                # Check tasks
                self.check_scheduled_tasks()
                
                # Wait for next check
                time.sleep(interval)
        except KeyboardInterrupt:
            print("调度器已停止")
    