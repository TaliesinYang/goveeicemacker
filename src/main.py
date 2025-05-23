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
    """Format time and display in multiple timezones
    
    Args:
        time_str: Time string in "HH:MM" format
        from_timezone: Input timezone
        
    Returns:
        dict: Dictionary containing times in different timezones
    """
    try:
        # Parse time string
        hour, minute = map(int, time_str.split(":"))
        
        # Build today's time
        now = datetime.now()
        time_obj = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Add timezone info
        source_tz = pytz.timezone(from_timezone)
        time_with_tz = source_tz.localize(time_obj)
        
        # Convert to other timezones
        utc_time = time_with_tz.astimezone(pytz.UTC)
        shanghai_time = time_with_tz.astimezone(pytz.timezone("Asia/Shanghai"))
        
        return {
            "source": f"{hour:02d}:{minute:02d} ({from_timezone})",
            "utc": utc_time.strftime("%H:%M:%S"),
            "shanghai": shanghai_time.strftime("%H:%M:%S")
        }
    except Exception as e:
        print(f"Time formatting error: {e}")
        return {
            "source": time_str,
            "utc": "Format error",
            "shanghai": "Format error"
        }

def main():
    # Read API key and device info from config file
    api_key = config.api_key
    api_key_value = config.api_key_value
    sku = config.sku
    device_id = config.device
    daily_control_time_file = config.daily_control_time_load
    timezone = config.timezone
    
    # Convert timezone format (from UTC-07:00 to America/Vancouver)
    from_timezone = verify_timezone_mapping(timezone)
    
    print(f"Current timezone: {timezone} ({from_timezone})")
    print(f"Device: {sku} - {device_id}")
    print(f"API Key: {api_key} = {api_key_value[:4]}{'*' * (len(api_key_value)-4) if len(api_key_value) > 4 else '****'}")
    
    # Display current time in different timezones
    now_utc = datetime.now(pytz.UTC)
    now_local = now_utc.astimezone(pytz.timezone(from_timezone))
    now_china = now_utc.astimezone(pytz.timezone("Asia/Shanghai"))
    print(f"\nCurrent Time:")
    print(f"UTC Time: {now_utc.strftime('%H:%M:%S')}")
    print(f"{timezone} Time: {now_local.strftime('%H:%M:%S')}")
    print(f"Shanghai Time (UTC+8): {now_china.strftime('%H:%M:%S')}")
    
    # Initialize request object
    ice_maker = Request(api_key, api_key_value)
    
    # Get device list
    devices_result = ice_maker.get_devices()
    
    if devices_result["code"] != 200:
        print(f"Failed to get devices: {devices_result}")
        
        # Ask whether to continue
        continue_choice = input("Skip device verification and continue? (y/n): ")
        if continue_choice.lower() != 'y':
            return
        
        print("Skipping device verification, continuing with device info from config...")
    else:
        # Print device information
        print("Device List:")
        for device in devices_result.get("data", []):
            print(f"Device Name: {device.get('deviceName', 'Unknown')}")
            print(f"Device ID: {device.get('device', 'Unknown')}")
            print(f"Device Model: {device.get('sku', 'Unknown')}")
            print("----------")
    
    # Test device connection
    test_choice = input("Test device connection? (y/n): ")
    if test_choice.lower() == 'y':
        print("Testing device connection...")
        # Send a simple status query request
        result = ice_maker.get_devices()
        if result["code"] == 200:
            print("Device connection test successful!")
        else:
            print(f"Device connection test failed: {result}")
            print("Please check if the API key and device information are correct.")
            print("API Format Tips:")
            print("1. Official Govee API typically uses 'Govee-API-Key' as the key name")
            print("2. Some devices may use 'x-api-key' as the key name")
            print(f"Current API key name: {api_key}")
            print("Please ensure your config file uses the correct key name and value.")
            
            # Ask whether to continue
            continue_choice = input("Continue with the program? (y/n): ")
            if continue_choice.lower() != 'y':
                return
    
    # Demo features
    while True:
        print("\nIce Maker Control System")
        print("1. Power On Device")
        print("2. Power Off Device")
        print("3. Set Work Mode")
        print("4. Set One-time Scheduled Task")
        print("5. View Daily Scheduled Tasks")
        print("6. Start Task Scheduler (includes daily scheduling)")
        print("7. View Current Configuration")
        print("8. Modify API Key")
        print("0. Exit")
        
        choice = input("Select operation: ")
        
        if choice == "1":
            result = ice_maker.open_device(sku, device_id)
            print(f"Power On result: {result}")
            
        elif choice == "2":
            result = ice_maker.close_device(sku, device_id)
            print(f"Power Off result: {result}")
            
        elif choice == "3":
            print("Work modes: 1-Large Ice, 2-Medium Ice, 3-Small Ice")
            mode = int(input("Select work mode: "))
            if mode in [1, 2, 3]:
                result = ice_maker.set_work_mode(sku, device_id, mode)
                print(f"Set work mode result: {result}")
            else:
                print("Invalid work mode")
                
        elif choice == "4":
            print("Action type: 1-Power On, 2-Power Off")
            action_type = input("Select action type: ")
            if action_type == "1":
                action_type = "open"
            elif action_type == "2":
                action_type = "close"
            else:
                print("Invalid action type")
                continue
                
            target_time = input(f"Enter target time ({timezone})(format: HH:MM or YYYY-MM-DD HH:MM:SS): ")
            try:
                # Try to parse two possible time formats
                if ":" in target_time and len(target_time.split(":")) == 2:
                    # Simple HH:MM format
                    hour, minute = map(int, target_time.split(":"))
                    # Build today's time
                    now = datetime.now()
                    target_datetime = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    target_time = target_datetime.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    # Validate full time format
                    datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
                
                # Set scheduled task
                ice_maker.schedule_with_timezone(sku, device_id, action_type, target_time, from_timezone=from_timezone)
                print("Scheduled task set")
            except ValueError:
                print("Invalid time format, please use HH:MM or YYYY-MM-DD HH:MM:SS format")
                
        elif choice == "5":
            # Display scheduled tasks from config file
            daily_times = ice_maker.read_daily_controller_times(daily_control_time_file)
            print("\nDaily Scheduled Tasks:")
            
            # Format and display power on times
            print("Power On Times:")
            for time_str in daily_times['open']:
                time_info = format_time_with_all_timezones(time_str, from_timezone)
                print(f"  {time_info['source']} → UTC: {time_info['utc']} → Shanghai: {time_info['shanghai']}")
            
            # Format and display power off times
            print("Power Off Times:")
            for time_str in daily_times['close']:
                time_info = format_time_with_all_timezones(time_str, from_timezone)
                print(f"  {time_info['source']} → UTC: {time_info['utc']} → Shanghai: {time_info['shanghai']}")
            
            print(f"\nNote: These times are configured in {timezone} ({from_timezone}) format, the program will automatically convert them to various timezone times")
            
            # Ask whether to modify the config file
            edit_choice = input("\nModify scheduled task configuration? (y/n): ")
            if edit_choice.lower() == 'y':
                print("\nEnter new scheduled task times, separate multiple times with commas, format is HH:MM")
                new_open_times = input("New power on time list: ")
                new_close_times = input("New power off time list: ")
                
                try:
                    # Simple format validation
                    for time_list in [new_open_times.split(','), new_close_times.split(',')]:
                        for t in time_list:
                            t = t.strip()
                            if t:  # Skip empty strings
                                hours, minutes = t.split(':')
                                if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
                                    raise ValueError(f"Invalid time format: {t}")
                    
                    # Write to config file
                    with open(daily_control_time_file, "w") as f:
                        f.write(f"openlist:{new_open_times}\n")
                        f.write(f"closelist:{new_close_times}")
                    
                    print("Configuration file updated")
                except Exception as e:
                    print(f"Failed to update configuration file: {e}")
                
        elif choice == "6":
            print("Starting task scheduler, including daily scheduled tasks, press Ctrl+C to stop")
            # First display current configuration
            daily_times = ice_maker.read_daily_controller_times(daily_control_time_file)
            print("\nDaily Scheduled Tasks:")
            
            # Format and display power on times
            print("Power On Times:")
            for time_str in daily_times['open']:
                time_info = format_time_with_all_timezones(time_str, from_timezone)
                print(f"  {time_info['source']} → UTC: {time_info['utc']} → Shanghai: {time_info['shanghai']}")
            
            # Format and display power off times
            print("Power Off Times:")
            for time_str in daily_times['close']:
                time_info = format_time_with_all_timezones(time_str, from_timezone)
                print(f"  {time_info['source']} → UTC: {time_info['utc']} → Shanghai: {time_info['shanghai']}")
            
            # Set up daily tasks for current device
            ice_maker.setup_daily_tasks(sku, device_id, from_timezone=from_timezone)
            
            # Start scheduler
            ice_maker.start_scheduler()
            
        elif choice == "7":
            # Display current configuration
            print("\nCurrent Configuration:")
            print(f"API Key Name: {api_key}")
            # Mask part of the API key value, only show the first 4 digits
            masked_key = api_key_value[:4] + '*' * (len(api_key_value) - 4) if len(api_key_value) > 4 else '****'
            print(f"API Key Value: {masked_key}")
            print(f"Device Model: {sku}")
            print(f"Device ID: {device_id}")
            print(f"Timezone Setting: {timezone} ({from_timezone})")
            print(f"Scheduled Task Config File: {daily_control_time_file}")
            
            # Display current time in different timezones
            now_utc = datetime.now(pytz.UTC)
            now_local = now_utc.astimezone(pytz.timezone(from_timezone))
            now_china = now_utc.astimezone(pytz.timezone("Asia/Shanghai"))
            print(f"\nCurrent Time:")
            print(f"UTC Time: {now_utc.strftime('%H:%M:%S')}")
            print(f"{timezone} Time: {now_local.strftime('%H:%M:%S')}")
            print(f"Shanghai Time (UTC+8): {now_china.strftime('%H:%M:%S')}")
            
        elif choice == "8":
            # Modify API key
            print("\nCurrent API Key:")
            print(f"Name: {api_key}")
            masked_key = api_key_value[:4] + '*' * (len(api_key_value) - 4) if len(api_key_value) > 4 else '****'
            print(f"Value: {masked_key}")
            
            new_key_name = input("Enter new API key name (press Enter to keep unchanged): ")
            new_key_value = input("Enter new API key value (press Enter to keep unchanged): ")
            
            if new_key_name or new_key_value:
                try:
                    # Read current config file content
                    with open('config.py', 'r') as f:
                        lines = f.readlines()
                    
                    # Replace configuration
                    with open('config.py', 'w') as f:
                        for line in lines:
                            if line.startswith('api_key =') and new_key_name:
                                f.write(f'api_key = "{new_key_name}"\n')
                            elif line.startswith('api_key_value =') and new_key_value:
                                f.write(f'api_key_value = "{new_key_value}"  # Replace with your actual API key\n')
                            else:
                                f.write(line)
                    
                    print("API key updated, please restart the program to apply changes")
                    return
                except Exception as e:
                    print(f"Failed to update API key: {e}")
            
        elif choice == "0":
            print("Exiting program")
            break
            
        else:
            print("Invalid selection")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"\nProgram error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...") 