#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from datetime import datetime
from request import Request
import config
import pytz

def verify_timezone_mapping(timezone_str):
    """验证并返回正确的时区映射"""
    if timezone_str == "UTC-07:00":
        # 优先尝试使用Vancouver时区，如果不可用则使用US/Mountain
        try:
            pytz.timezone("America/Vancouver")
            return "America/Vancouver"  # 温哥华时区
        except:
            return "US/Mountain"  # 山地时区(MDT)
    elif timezone_str == "UTC+08:00":
        return "Asia/Shanghai"  # 东八区
    else:
        print(f"未知的时区设置: {timezone_str}，将使用UTC")
        return "UTC"

def format_time_with_all_timezones(time_str, from_timezone):
    """格式化时间并显示在多个时区
    
    Args:
        time_str: 格式为 "HH:MM" 的时间字符串
        from_timezone: 输入时间的时区
        
    Returns:
        dict: 包含各时区时间的字典
    """
    try:
        # 解析时间字符串
        hour, minute = map(int, time_str.split(":"))
        
        # 构建今天的时间
        now = datetime.now()
        time_obj = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # 添加时区信息
        source_tz = pytz.timezone(from_timezone)
        time_with_tz = source_tz.localize(time_obj)
        
        # 转换到其他时区
        utc_time = time_with_tz.astimezone(pytz.UTC)
        shanghai_time = time_with_tz.astimezone(pytz.timezone("Asia/Shanghai"))
        
        return {
            "source": f"{hour:02d}:{minute:02d} ({from_timezone})",
            "utc": utc_time.strftime("%H:%M:%S"),
            "shanghai": shanghai_time.strftime("%H:%M:%S")
        }
    except Exception as e:
        print(f"时间格式化错误: {e}")
        return {
            "source": time_str,
            "utc": "格式错误",
            "shanghai": "格式错误"
        }

def main():
    # 从配置文件读取API密钥和设备信息
    api_key = config.api_key
    api_key_value = config.api_key_value
    sku = config.sku
    device_id = config.device
    daily_control_time_file = config.daily_control_time_load
    timezone = config.timezone
    
    # 转换时区格式（从UTC-07:00转换为America/Vancouver）
    from_timezone = verify_timezone_mapping(timezone)
    
    print(f"当前使用的时区: {timezone} ({from_timezone})")
    print(f"设备: {sku} - {device_id}")
    print(f"API密钥: {api_key} = {api_key_value[:4]}{'*' * (len(api_key_value)-4) if len(api_key_value) > 4 else '****'}")
    
    # 显示当前各时区时间
    now_utc = datetime.now(pytz.UTC)
    now_local = now_utc.astimezone(pytz.timezone(from_timezone))
    now_china = now_utc.astimezone(pytz.timezone("Asia/Shanghai"))
    print(f"\n当前时间:")
    print(f"UTC时间: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{timezone}时间: {now_local.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"东八区时间: {now_china.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 初始化请求对象
    ice_maker = Request(api_key, api_key_value)
    
    # 获取设备列表
    devices_result = ice_maker.get_devices()
    
    if devices_result["code"] != 200:
        print(f"获取设备失败: {devices_result}")
        
        # 询问是否继续
        continue_choice = input("是否要跳过设备验证继续使用程序？(y/n): ")
        if continue_choice.lower() != 'y':
            return
        
        print("跳过设备验证，使用配置文件中的设备信息继续运行...")
    else:
        # 打印设备信息
        print("设备列表:")
        for device in devices_result.get("data", []):
            print(f"设备名称: {device.get('deviceName', 'Unknown')}")
            print(f"设备ID: {device.get('device', 'Unknown')}")
            print(f"设备型号: {device.get('sku', 'Unknown')}")
            print("----------")
    
    # 测试设备连接
    test_choice = input("是否要测试设备连接？(y/n): ")
    if test_choice.lower() == 'y':
        print("正在测试设备连接...")
        # 发送一个简单的状态查询请求
        result = ice_maker.get_devices()
        if result["code"] == 200:
            print("设备连接测试成功！")
        else:
            print(f"设备连接测试失败: {result}")
            print("请检查API密钥和设备信息是否正确。")
            print("API格式提示:")
            print("1. Govee官方API通常使用 'Govee-API-Key' 作为密钥名称")
            print("2. 某些设备可能使用 'x-api-key' 作为密钥名称")
            print(f"当前使用的API密钥名称: {api_key}")
            print("请确认您的配置文件中使用了正确的密钥名称和值。")
            
            # 询问是否继续
            continue_choice = input("是否要继续使用程序？(y/n): ")
            if continue_choice.lower() != 'y':
                return
    
    # 演示功能
    while True:
        print("\n冰块制造机控制系统")
        print("1. 开启设备")
        print("2. 关闭设备")
        print("3. 设置工作模式")
        print("4. 设置单次定时任务")
        print("5. 查看每日定时任务")
        print("6. 启动定时任务调度器(包含每日定时)")
        print("7. 查看当前配置信息")
        print("8. 修改API密钥")
        print("0. 退出")
        
        choice = input("请选择操作: ")
        
        if choice == "1":
            result = ice_maker.open_device(sku, device_id)
            print(f"开启设备结果: {result}")
            
        elif choice == "2":
            result = ice_maker.close_device(sku, device_id)
            print(f"关闭设备结果: {result}")
            
        elif choice == "3":
            print("工作模式: 1-大冰块, 2-中冰块, 3-小冰块")
            mode = int(input("请选择工作模式: "))
            if mode in [1, 2, 3]:
                result = ice_maker.set_work_mode(sku, device_id, mode)
                print(f"设置工作模式结果: {result}")
            else:
                print("无效的工作模式")
                
        elif choice == "4":
            print("操作类型: 1-开启, 2-关闭")
            action_type = input("请选择操作类型: ")
            if action_type == "1":
                action_type = "open"
            elif action_type == "2":
                action_type = "close"
            else:
                print("无效的操作类型")
                continue
                
            target_time = input(f"请输入目标时间({timezone})(格式: HH:MM 或 YYYY-MM-DD HH:MM:SS): ")
            try:
                # 尝试解析两种可能的时间格式
                if ":" in target_time and len(target_time.split(":")) == 2:
                    # 简单的HH:MM格式
                    hour, minute = map(int, target_time.split(":"))
                    # 构建今天的这个时间
                    now = datetime.now()
                    target_datetime = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    target_time = target_datetime.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    # 验证完整时间格式
                    datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                
                # 设置定时任务
                ice_maker.schedule_with_timezone(sku, device_id, action_type, target_time, from_timezone=from_timezone)
                print("定时任务已设置")
            except ValueError:
                print("无效的时间格式，请使用HH:MM或YYYY-MM-DD HH:MM:SS格式")
                
        elif choice == "5":
            # 显示配置文件中的定时任务
            daily_times = ice_maker.read_daily_controller_times(daily_control_time_file)
            print("\n每日定时任务:")
            
            # 格式化显示开机时间
            print("开机时间:")
            for time_str in daily_times['open']:
                time_info = format_time_with_all_timezones(time_str, from_timezone)
                print(f"  {time_info['source']} → UTC: {time_info['utc']} → 东八区: {time_info['shanghai']}")
            
            # 格式化显示关机时间
            print("关机时间:")
            for time_str in daily_times['close']:
                time_info = format_time_with_all_timezones(time_str, from_timezone)
                print(f"  {time_info['source']} → UTC: {time_info['utc']} → 东八区: {time_info['shanghai']}")
            
            print(f"\n注意: 这些时间配置为{timezone}({from_timezone})格式，程序会自动将其转换为各时区时间")
            
            # 询问是否修改配置文件
            edit_choice = input("\n是否需要修改定时任务配置? (y/n): ")
            if edit_choice.lower() == 'y':
                print("\n请输入新的定时任务时间，多个时间用逗号分隔，格式为HH:MM")
                new_open_times = input("新的开机时间列表: ")
                new_close_times = input("新的关机时间列表: ")
                
                try:
                    # 简单验证格式
                    for time_list in [new_open_times.split(','), new_close_times.split(',')]:
                        for t in time_list:
                            t = t.strip()
                            if t:  # 跳过空字符串
                                hours, minutes = t.split(':')
                                if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
                                    raise ValueError(f"无效的时间格式: {t}")
                    
                    # 写入配置文件
                    with open(daily_control_time_file, "w") as f:
                        f.write(f"openlist:{new_open_times}\n")
                        f.write(f"closelist:{new_close_times}")
                    
                    print("配置文件已更新")
                except Exception as e:
                    print(f"更新配置文件失败: {e}")
                
        elif choice == "6":
            print("启动定时任务调度器，包含每日定时任务，按Ctrl+C停止")
            # 先显示当前配置
            daily_times = ice_maker.read_daily_controller_times(daily_control_time_file)
            print("\n每日定时任务:")
            
            # 格式化显示开机时间
            print("开机时间:")
            for time_str in daily_times['open']:
                time_info = format_time_with_all_timezones(time_str, from_timezone)
                print(f"  {time_info['source']} → UTC: {time_info['utc']} → 东八区: {time_info['shanghai']}")
            
            # 格式化显示关机时间
            print("关机时间:")
            for time_str in daily_times['close']:
                time_info = format_time_with_all_timezones(time_str, from_timezone)
                print(f"  {time_info['source']} → UTC: {time_info['utc']} → 东八区: {time_info['shanghai']}")
            
            # 为当前设备设置每日任务
            ice_maker.setup_daily_tasks(sku, device_id, from_timezone=from_timezone)
            
            # 启动调度器
            ice_maker.start_scheduler()
            
        elif choice == "7":
            # 显示当前配置信息
            print("\n当前配置信息:")
            print(f"API密钥名称: {api_key}")
            # 隐藏部分API密钥值，只显示前4位
            masked_key = api_key_value[:4] + '*' * (len(api_key_value) - 4) if len(api_key_value) > 4 else '****'
            print(f"API密钥值: {masked_key}")
            print(f"设备型号: {sku}")
            print(f"设备ID: {device_id}")
            print(f"时区设置: {timezone} ({from_timezone})")
            print(f"定时任务配置文件: {daily_control_time_file}")
            
            # 显示各时区当前时间
            now_utc = datetime.now(pytz.UTC)
            now_local = now_utc.astimezone(pytz.timezone(from_timezone))
            now_china = now_utc.astimezone(pytz.timezone("Asia/Shanghai"))
            print(f"\n当前时间:")
            print(f"UTC时间: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{timezone}时间: {now_local.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"东八区时间: {now_china.strftime('%Y-%m-%d %H:%M:%S')}")
            
        elif choice == "8":
            # 修改API密钥
            print("\n当前API密钥:")
            print(f"名称: {api_key}")
            masked_key = api_key_value[:4] + '*' * (len(api_key_value) - 4) if len(api_key_value) > 4 else '****'
            print(f"值: {masked_key}")
            
            new_key_name = input("请输入新的API密钥名称(直接回车保持不变): ")
            new_key_value = input("请输入新的API密钥值(直接回车保持不变): ")
            
            if new_key_name or new_key_value:
                try:
                    # 读取当前配置文件内容
                    with open('config.py', 'r') as f:
                        lines = f.readlines()
                    
                    # 替换配置
                    with open('config.py', 'w') as f:
                        for line in lines:
                            if line.startswith('api_key =') and new_key_name:
                                f.write(f'api_key = "{new_key_name}"\n')
                            elif line.startswith('api_key_value =') and new_key_value:
                                f.write(f'api_key_value = "{new_key_value}"  # 请替换为你的实际API密钥\n')
                            else:
                                f.write(line)
                    
                    print("API密钥已更新，请重启程序以应用更改")
                    return
                except Exception as e:
                    print(f"更新API密钥失败: {e}")
            
        elif choice == "0":
            print("退出程序")
            break
            
        else:
            print("无效的选择")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已被用户中断")
    except Exception as e:
        print(f"\n程序发生错误: {e}")
        import traceback
        traceback.print_exc()
        input("按Enter键退出...") 