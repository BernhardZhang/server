"""
Merit Point Calculation Utilities
功分计算工具函数

基于协作贡献功分制度的数学公式实现
"""

import math
from typing import List, Dict, Tuple


def calculate_merit_points(contributions: List[float]) -> List[float]:
    """
    根据参与人数和贡献值计算功分
    
    Args:
        contributions: 参与者的贡献值列表 [S1, S2, ..., Sn]
        
    Returns:
        List[float]: 每个参与者的功分列表
    """
    n = len(contributions)
    
    if n == 0:
        return []
    elif n == 1:
        # 单人参与，功分为贡献值
        return contributions
    elif n == 2:
        return _calculate_two_participants(contributions)
    elif 3 <= n <= 10:
        return _calculate_small_group(contributions)
    else:  # n > 10
        return _calculate_large_group(contributions)


def _calculate_two_participants(contributions: List[float]) -> List[float]:
    """
    两人参与的功分计算 (n=2)
    公式: 功分i = Si * (1 + 0.1 * |S1-S2|/max(S1,S2))
    """
    s1, s2 = contributions[0], contributions[1]
    max_contribution = max(s1, s2)
    
    if max_contribution == 0:
        return [0.0, 0.0]
    
    adjustment_factor = 1 + 0.1 * abs(s1 - s2) / max_contribution
    
    return [s1 * adjustment_factor, s2 * adjustment_factor]


def _calculate_small_group(contributions: List[float]) -> List[float]:
    """
    小组参与的功分计算 (3≤n≤10)
    公式: 功分i = Si * Wi * Ai
    其中:
    - Wi = (Si/平均贡献值) * (1 + 0.05 * (n-3))
    - Ai = 1 + 0.1 * (Si - 最小贡献值)/(最大贡献值 - 最小贡献值)
    """
    n = len(contributions)
    total_contribution = sum(contributions)
    avg_contribution = total_contribution / n if n > 0 else 0
    min_contribution = min(contributions)
    max_contribution = max(contributions)
    
    if avg_contribution == 0 or max_contribution == min_contribution:
        return contributions
    
    merit_points = []
    
    for si in contributions:
        # 权重因子 Wi
        wi = (si / avg_contribution) * (1 + 0.05 * (n - 3))
        
        # 调整因子 Ai
        ai = 1 + 0.1 * (si - min_contribution) / (max_contribution - min_contribution)
        
        # 功分计算
        merit_point = si * wi * ai
        merit_points.append(merit_point)
    
    return merit_points


def _calculate_large_group(contributions: List[float]) -> List[float]:
    """
    大组参与的功分计算 (n>10)
    公式: 功分i = Si * Ti * Bi
    其中:
    - Ti = 0.8 + 0.4 * (Si/最大贡献值)
    - Bi = 1 + 0.05 * log(Si/平均贡献值 + 1)
    """
    n = len(contributions)
    total_contribution = sum(contributions)
    avg_contribution = total_contribution / n if n > 0 else 0
    max_contribution = max(contributions)
    
    if max_contribution == 0 or avg_contribution == 0:
        return contributions
    
    merit_points = []
    
    for si in contributions:
        # 分布因子 Ti
        ti = 0.8 + 0.4 * (si / max_contribution)
        
        # 对数调整因子 Bi
        bi = 1 + 0.05 * math.log(si / avg_contribution + 1)
        
        # 功分计算
        merit_point = si * ti * bi
        merit_points.append(merit_point)
    
    return merit_points


def calculate_team_merit_distribution(team_contributions: Dict[str, float]) -> Dict[str, float]:
    """
    计算团队成员的功分分配
    
    Args:
        team_contributions: {用户ID: 贡献值} 的字典
        
    Returns:
        Dict[str, float]: {用户ID: 功分} 的字典
    """
    if not team_contributions:
        return {}
    
    user_ids = list(team_contributions.keys())
    contributions = list(team_contributions.values())
    
    merit_points = calculate_merit_points(contributions)
    
    return dict(zip(user_ids, merit_points))


def normalize_merit_points(merit_points: List[float], target_total: float = 100.0) -> List[float]:
    """
    将功分标准化到指定总和
    
    Args:
        merit_points: 原始功分列表
        target_total: 目标总分
        
    Returns:
        List[float]: 标准化后的功分列表
    """
    current_total = sum(merit_points)
    
    if current_total == 0:
        return merit_points
    
    scale_factor = target_total / current_total
    return [point * scale_factor for point in merit_points]


def get_merit_calculation_info(n: int) -> Dict[str, str]:
    """
    获取功分计算方法信息
    
    Args:
        n: 参与人数
        
    Returns:
        Dict: 包含计算方法和公式描述的字典
    """
    if n == 1:
        return {
            "method": "单人参与",
            "formula": "功分 = 贡献值",
            "description": "单人参与时，功分等于其贡献值"
        }
    elif n == 2:
        return {
            "method": "双人协作",
            "formula": "功分i = Si × (1 + 0.1 × |S1-S2|/max(S1,S2))",
            "description": "双人协作时，根据贡献差异进行调整"
        }
    elif 3 <= n <= 10:
        return {
            "method": "小组协作",
            "formula": "功分i = Si × Wi × Ai",
            "description": "小组协作时，综合考虑权重因子和调整因子"
        }
    else:
        return {
            "method": "大组协作",
            "formula": "功分i = Si × Ti × Bi",
            "description": "大组协作时，使用分布因子和对数调整因子"
        }


# 示例使用和测试
if __name__ == "__main__":
    # 测试不同场景的功分计算
    
    # 双人协作示例
    print("=== 双人协作示例 ===")
    contributions_2 = [8.0, 6.0]
    merit_2 = calculate_merit_points(contributions_2)
    print(f"贡献值: {contributions_2}")
    print(f"功分: {merit_2}")
    print(f"计算方法: {get_merit_calculation_info(2)}")
    
    # 小组协作示例
    print("\n=== 小组协作示例 ===")
    contributions_5 = [9.0, 7.0, 8.0, 6.0, 5.0]
    merit_5 = calculate_merit_points(contributions_5)
    print(f"贡献值: {contributions_5}")
    print(f"功分: {[round(m, 2) for m in merit_5]}")
    print(f"计算方法: {get_merit_calculation_info(5)}")
    
    # 大组协作示例
    print("\n=== 大组协作示例 ===")
    contributions_12 = [9.0, 8.0, 7.0, 6.0, 8.0, 7.0, 5.0, 6.0, 7.0, 8.0, 6.0, 5.0]
    merit_12 = calculate_merit_points(contributions_12)
    print(f"贡献值: {contributions_12}")
    print(f"功分: {[round(m, 2) for m in merit_12]}")
    print(f"计算方法: {get_merit_calculation_info(12)}")
    
    # 团队功分分配示例
    print("\n=== 团队功分分配示例 ===")
    team_data = {
        "user_1": 9.0,
        "user_2": 7.0,
        "user_3": 8.0,
        "user_4": 6.0
    }
    team_merit = calculate_team_merit_distribution(team_data)
    print(f"团队贡献: {team_data}")
    print(f"团队功分: {{k: round(v, 2) for k, v in team_merit.items()}}")