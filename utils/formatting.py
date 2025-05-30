from datetime import datetime, timezone

def format_traffic(traffic_bytes: int) -> str:

    if traffic_bytes == 0:
        return "نامحدود"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(traffic_bytes)
    unit_index = 0
    
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
    
    return f"{value:.2f} {units[unit_index]}"

def format_expire_time(expire_timestamp: int) -> str:
    if not expire_timestamp:
        return "نامحدود"
    expire_date = datetime.fromtimestamp(expire_timestamp, tz=timezone.utc)
    return expire_date.strftime("%Y-%m-%d")
