import subprocess
import json
import csv
import sys
import argparse

def run_amap_command(args):
    """运行 amap-gui 命令并返回 JSON 结果"""
    cmd = ["amap-gui"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        if "start" in args: return None
        print(f"执行命令失败: {' '.join(cmd)}, 错误: {e}")
        return None

def get_coordinates(target_name):
    """获取目标地点的坐标"""
    print(f"正在定位目标地点: {target_name}...")
    res = run_amap_command(["searchPOI", "--keyword", target_name, "--pageSize", "1"])
    if res and res.get("success") and res["data"]["pois"]:
        poi = res["data"]["pois"][0]
        return poi["location"], poi["name"]
    return None, None

def search_nearby_housing(center_coords, radius=5000, page_size=50):
    """搜索周边的小区"""
    print(f"正在搜索周边 {radius}m 内的住宅小区...")
    res = run_amap_command([
        "searchPOI", "--keyword", "住宅区", 
        "--center", f"{center_coords[0]},{center_coords[1]}", 
        "--radius", str(radius), "--pageSize", str(page_size)
    ])
    if res and res.get("success"):
        return res["data"]["pois"]
    return []

def get_route_time(from_coords, to_coords, route_type):
    """获取路径规划时间（单位：分钟）"""
    res = run_amap_command([
        "route", 
        "--from", f"{from_coords[0]},{from_coords[1]}", 
        "--to", f"{to_coords[0]},{to_coords[1]}", 
        "--type", route_type
    ])
    if res and res.get("success"):
        seconds = res["data"]["summary"]["time"]
        return int((seconds + 59) / 60) # 向上取整
    return 9999

def main():
    parser = argparse.ArgumentParser(description="查找符合通勤要求的小区")
    parser.add_argument("--target", required=True, help="目标地点名称")
    parser.add_argument("--walk-limit", type=int, default=30, help="步行限制时间（分钟）")
    parser.add_argument("--ride-limit", type=int, default=15, help="骑行限制时间（分钟）")
    parser.add_argument("--output", default="nearby_housing.csv", help="输出文件名")
    parser.add_argument("--limit", type=int, default=50, help="处理的小区数量限制")
    args = parser.parse_args()

    run_amap_command(["start"])
    
    center_loc, formal_name = get_coordinates(args.target)
    if not center_loc:
        print("无法定位目标地点。")
        return

    pois = search_nearby_housing(center_loc, page_size=args.limit)
    if not pois:
        print("未找到周边小区。")
        return

    results = []
    print(f"开始分析前 {len(pois)} 个地点...")
    
    for poi in pois:
        poi_type = poi.get("type", "")
        # 筛选逻辑：必须包含“商务住宅”或“住宅区”
        if "商务住宅" not in poi_type and "住宅区" not in poi_type:
            continue
            
        poi_loc = poi["location"]
        poi_name = poi["name"]
        
        walk_time = get_route_time(poi_loc, center_loc, "walking")
        ride_time = get_route_time(poi_loc, center_loc, "riding")
        
        is_match = walk_time <= args.walk_limit or ride_time <= args.ride_limit
        status = "符合" if is_match else "不符合"
        
        results.append({
            "小区名称": poi_name,
            "是否符合": status,
            "步行分钟": walk_time,
            "骑行分钟": ride_time,
            "地点类型": poi_type,
            "地址": poi["address"]
        })
        print(f"- {poi_name} ({status})")

    if results:
        with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print(f"\n查询结束！结果已保存至: {args.output}")

if __name__ == "__main__":
    main()
