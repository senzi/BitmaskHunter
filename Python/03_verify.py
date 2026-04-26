# filename: Python/verify.py
"""
掩码规则验证脚本。

该脚本用于加载训练阶段生成的 rules.mask 文件，
并对集合 A（负样本）和集合 B（正样本）进行验证，
检查规则是否满足以下要求:
    - 集合 A 中的任何样本都不应被规则命中（零误报）。
    - 集合 B 中的所有样本都应被规则命中（全覆盖）。
"""


def load_rules(path):
    """
    从文件加载位掩码规则。

    文件格式:
        每行一条规则，格式为 "bit1,bit2,...,bitN:value"
        例如: "0,5,10:3" 表示选取第 0、5、10 位，期望模式值为 3。

    Args:
        path (str): 规则文件路径。

    Returns:
        list: 规则列表，每个元素为 (bits, val) 元组。
    """
    rules = []
    with open(path) as f:
        for line in f:
            if ':' not in line:
                continue
            bits_str, val_str = line.strip().split(':')
            bits = [int(b) for b in bits_str.split(',')]
            rules.append((bits, int(val_str)))
    return rules


def check_match(h_int, rules):
    """
    判断给定的哈希整数是否匹配任意一条规则。

    匹配逻辑:
        对每条规则，提取指定的比特位并计算模式值，
        如果模式值与规则中的期望值一致，则视为命中。

    Args:
        h_int (int): 待检测的 128 位哈希整数。
        rules (list): 规则列表。

    Returns:
        bool: 如果命中任意规则返回 True，否则返回 False。
    """
    for bits, target_val in rules:
        val = 0
        for i, bit in enumerate(bits):
            if (h_int >> bit) & 1:
                val |= (1 << i)
        if val == target_val:
            return True
    return False


def main():
    """
    主函数：加载规则并对集合 A、B 进行验证，输出验证报告。
    """
    rules = load_rules("rules.mask")
    hashes_a = [int(line.strip(), 16) for line in open("A.txt") if line.strip()]
    hashes_b = [int(line.strip(), 16) for line in open("B.txt") if line.strip()]

    # 统计集合 A 中的误报数量（不应被命中的却被命中了）
    a_wrong = sum(1 for h in hashes_a if check_match(h, rules))
    # 统计集合 B 中的正确检出数量
    b_correct = sum(1 for h in hashes_b if check_match(h, rules))

    print("--- 验证报告 ---")
    print(f"规则数量: {len(rules)}")
    print(f"集合 A (应为负): 总数 {len(hashes_a)}, 误报 {a_wrong} ({(a_wrong / len(hashes_a)) * 100:.2f}%)")
    print(f"集合 B (应为正): 总数 {len(hashes_b)}, 检出 {b_correct} ({(b_correct / len(hashes_b)) * 100:.2f}%)")

    if a_wrong == 0 and b_correct == len(hashes_b):
        print("[SUCCESS] 完美区分！算法逻辑通过。")
    else:
        print("[INFO] 部分区分，请检查位宽或样本差异。")


if __name__ == "__main__":
    main()
