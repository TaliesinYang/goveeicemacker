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
        """设置每日定时任务
        
        Args:
            sku: 设备型号
            device_id: 设备ID
            from_timezone: 输入时间的时区，默认为温哥华时区 (America/Vancouver)
            config_file: 配置文件路径，如果为None则使用上次路径或默认路径
        """
        # 确保时区名称正确
        if from_timezone == "US/Mountain":
            # 优先使用温哥华时区
            try:
                pytz.timezone("America/Vancouver")
                from_timezone = "America/Vancouver"
                logger.info("时区已从US/Mountain转换为America/Vancouver")
            except:
                logger.info("使用US/Mountain时区")
        
        # 获取今天的日期
        today = date.today()
        
        # 如果今天已经加载过任务，则跳过
        if self.loaded_date == today:
            return
        
        # 确定配置文件路径
        if config_file is None:
            config_file = self.last_config_file or "dailycontrollertime.txt"
        
        # 读取配置文件
        controller_times = self.read_daily_controller_times(config_file)
        
        # 获取时区对象
        source_tz = pytz.timezone(from_timezone)
        
        # 清除之前的任务
        self.scheduled_tasks = [task for task in self.scheduled_tasks 
                               if task[2] not in ["daily_open", "daily_close"]]
        
        logger.info(f"设置每日任务，使用时区: {from_timezone}")
        
        # 设置开机任务
        for time_str in controller_times["open"]:
            # 构建完整的日期时间字符串
            full_time = f"{today.year}-{today.month:02d}-{today.day:02d} {time_str}:00"
            
            try:
                # 转换为datetime对象
                local_dt = datetime.strptime(full_time, "%Y-%m-%d %H:%M:%S")
                # 添加时区信息 - 这是温哥华时间(西七区)
                local_dt = source_tz.localize(local_dt)
                
                # 转换为UTC时间
                utc_dt = local_dt.astimezone(pytz.UTC)
                
                # 转换为东八区时间(便于记录)
                china_dt = utc_dt.astimezone(pytz.timezone("Asia/Shanghai"))
                
                # 添加任务
                self.scheduled_tasks.append((sku, device_id, "daily_open", utc_dt))
                
                logger.info(f"已设置每日开机任务:")
                logger.info(f" - 温哥华时间: {local_dt.strftime('%Y-%m-%d %H:%M:%S')} ({from_timezone})")
                logger.info(f" - UTC时间: {utc_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f" - 东八区时间: {china_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                
            except ValueError as e:
                logger.error(f"时间格式错误: {full_time}, 错误: {e}")
        
        # 设置关机任务
        for time_str in controller_times["close"]:
            # 构建完整的日期时间字符串
            full_time = f"{today.year}-{today.month:02d}-{today.day:02d} {time_str}:00"
            
            try:
                # 转换为datetime对象
                local_dt = datetime.strptime(full_time, "%Y-%m-%d %H:%M:%S")
                # 添加时区信息 - 这是温哥华时间(西七区)
                local_dt = source_tz.localize(local_dt)
                
                # 转换为UTC时间
                utc_dt = local_dt.astimezone(pytz.UTC)
                
                # 转换为东八区时间(便于记录)
                china_dt = utc_dt.astimezone(pytz.timezone("Asia/Shanghai"))
                
                # 添加任务
                self.scheduled_tasks.append((sku, device_id, "daily_close", utc_dt))
                
                logger.info(f"已设置每日关机任务:")
                logger.info(f" - 温哥华时间: {local_dt.strftime('%Y-%m-%d %H:%M:%S')} ({from_timezone})")
                logger.info(f" - UTC时间: {utc_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f" - 东八区时间: {china_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                
            except ValueError as e:
                logger.error(f"时间格式错误: {full_time}, 错误: {e}")
        
        # 更新已加载日期
        self.loaded_date = today
    
    def check_scheduled_tasks(self):
        """检查并执行定时任务，每5分钟执行一次"""
        current_time = datetime.now(pytz.UTC)
        logger.info(f"当前UTC时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        completed_tasks = []
        
        for index, (sku, device_id, action_type, target_time) in enumerate(self.scheduled_tasks):
            # 计算时间差(分钟)
            time_diff_minutes = (current_time - target_time).total_seconds() / 60
            
            # 记录详细的时间对比信息
            logger.info(f"检查任务 {index+1}: {action_type}")
            logger.info(f"  - 目标UTC时间: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"  - 当前UTC时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"  - 时间差(分钟): {time_diff_minutes:.2f}")
            
            # 如果当前时间已经超过目标时间且时差不超过10分钟
            if time_diff_minutes >= 0 and time_diff_minutes <= 10:
                # 记录要执行的操作
                if action_type == "open" or action_type == "daily_open":
                    logger.info(f"时间条件满足，执行开机操作: 设备{device_id}")
                    result = self.open_device(sku, device_id)
                    logger.info(f"开机操作结果: {result}")
                elif action_type == "close" or action_type == "daily_close":
                    logger.info(f"时间条件满足，执行关机操作: 设备{device_id}")
                    result = self.close_device(sku, device_id)
                    logger.info(f"关机操作结果: {result}")
                
                # 标记任务为已完成
                completed_tasks.append(index)
            elif time_diff_minutes > 10:
                # 如果时差超过10分钟，说明这个任务已经过期太久
                logger.warning(f"任务 {index+1} 已过期 {time_diff_minutes:.2f} 分钟，将被移除")
                completed_tasks.append(index)
            else:
                # 时间未到
                logger.info(f"任务 {index+1} 未到执行时间，还需等待约 {-time_diff_minutes:.2f} 分钟")
        
        # 移除已完成或过期的任务
        for index in sorted(completed_tasks, reverse=True):
            task_info = self.scheduled_tasks[index]
            logger.info(f"移除任务: {task_info[2]}, 原定执行时间: {task_info[3].strftime('%Y-%m-%d %H:%M:%S')}")
            del self.scheduled_tasks[index]
    
    def start_scheduler(self, interval=300):
        """启动定时任务调度器
        
        Args:
            interval: 检查间隔，默认300秒(5分钟)
        """
        try:
            while True:
                # 如果设备列表为空，尝试获取设备
                if not self.devices:
                    self.get_devices()
                
                # 如果有设备，设置每日任务
                if self.devices:
                    for device in self.devices:
                        self.setup_daily_tasks(device["sku"], device["device"])
                
                # 检查任务
                self.check_scheduled_tasks()
                
                # 等待下一次检查
                time.sleep(interval)
        except KeyboardInterrupt:
            print("调度器已停止")
    