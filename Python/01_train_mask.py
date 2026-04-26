# filename: Python/train_mask.py
"""
掩码规则训练脚本。

该脚本实现了 BitmaskHunter 核心算法：通过贪心策略和随机搜索，
从 MD5 哈希的 128 个比特位中筛选出一组位掩码规则，
使得这些规则能够覆盖集合 B（正样本）中的所有哈希，同时不覆盖集合 A（负样本）中的任何哈希。

核心思想:
    - MD5 是 128 位整数，每一位都可以作为特征。
    - 从 128 位中随机选取少量比特位（位宽），计算这些位组成的模式值。
    - 如果某个模式值在集合 B 中出现，但在集合 A 中从未出现，则该模式可作为区分规则。
    - 通过贪心策略不断寻找新规则，直到覆盖集合 B 中的所有样本。
    - 采用蒙特卡洛随机搜索，在可接受的位宽范围内快速寻找有效规则。
"""

import random
import pathlib
import time


class BitmaskHunter:
    """
    BitmaskHunter 核心类。

    属性:
        hashes_a (list): 集合 A 的哈希整数列表（负样本）。
        hashes_b (list): 集合 B 的哈希整数列表（正样本）。
        rules (list):  训练得到的规则列表，每条规则为 (bits, val) 元组。
                       bits: 选取的比特位索引列表。
                       val:  这些比特位对应的期望模式值。
    """

    def __init__(self, file_a, file_b):
        """
        初始化 BitmaskHunter，从文件中加载两个哈希集合。

        Args:
            file_a (str): 集合 A 的文件路径（负样本）。
            file_b (str): 集合 B 的文件路径（正样本）。
        """
        self.hashes_a = [int(line.strip(), 16) for line in open(file_a) if line.strip()]
        self.hashes_b = [int(line.strip(), 16) for line in open(file_b) if line.strip()]
        self.rules = []

    def get_val(self, h_int, bits):
        """
        从给定的 128 位哈希整数中提取指定比特位，组成一个新的模式值。

        例如：bits = [0, 5, 10]，则提取第 0、5、10 位，
              组成一个 3 位整数（第 0 位对应结果的第 0 位，以此类推）。

        Args:
            h_int (int): 128 位哈希整数。
            bits (list): 比特位索引列表。

        Returns:
            int: 提取出的模式值。
        """
        val = 0
        for i, bit in enumerate(bits):
            if (h_int >> bit) & 1:
                val |= (1 << i)
        return val

    def solve(self, max_width=12):
        """
        执行贪心搜索，寻找能够区分集合 A 和集合 B 的位掩码规则。

        算法流程:
            1. 从集合 B 中尚未被覆盖的样本开始。
            2. 对于每个位宽（1 到 max_width），随机选取多组比特位。
            3. 计算这些比特位在集合 A 中形成的"黑名单"模式值。
            4. 如果在集合 B 中存在某个样本的模式值不在黑名单中，
               则该 (bits, val) 构成一条有效规则。
            5. 移除被该规则覆盖的所有 B 样本，继续搜索，直到全部覆盖或无法继续。

        Args:
            max_width (int): 单条规则最多使用的比特位数，默认 12。

        Returns:
            dict: 训练统计信息，包含 elapsed, rule_count, unique_bits,
                  width_distribution, covered_all, uncovered_count 等字段。
        """
        start_time = time.perf_counter()
        uncovered = list(self.hashes_b)
        print(f"[INFO] 开始训练：A={len(self.hashes_a)}, B={len(self.hashes_b)}, 目标覆盖 {len(uncovered)} 个样本...")

        while uncovered:
            found_rule = False
            # 从小到大尝试不同的位宽
            for width in range(1, max_width + 1):
                # 对当前位宽进行多轮随机搜索
                for _ in range(500):  # 随机搜索尝试次数
                    bits = random.sample(range(128), width)
                    # 计算集合 A 中该组比特位的所有模式值（黑名单）
                    black_list = {self.get_val(h, bits) for h in self.hashes_a}

                    # 尝试寻找一个能覆盖部分 uncovered B 且不在黑名单的 val
                    for target_h in uncovered:
                        val = self.get_val(target_h, bits)
                        if val not in black_list:
                            # 优化：一次性过滤掉所有被命中的样本
                            new_uncovered = [h for h in uncovered if self.get_val(h, bits) != val]
                            hits_count = len(uncovered) - len(new_uncovered)
                            self.rules.append((bits, val))
                            uncovered = new_uncovered
                            print(f"[INFO] 找到规则: 位宽 {width}, 覆盖 {hits_count} 个, 剩余 {len(uncovered)}")
                            found_rule = True
                            break
                    if found_rule:
                        break
                if found_rule:
                    break

            # 如果所有位宽都尝试过仍无法找到新规则，则结束搜索
            if not found_rule:
                print("[WARNING] 无法完全覆盖所有样本。")
                break

        # 将规则持久化到文件
        with open("rules.mask", "w") as f:
            for bits, val in self.rules:
                f.write(f"{','.join(map(str, bits))}:{val}\n")
        print("[INFO] 规则已保存至 rules.mask")

        # 收集统计数据
        all_bits = set()
        width_counts = {}
        for bits, val in self.rules:
            all_bits.update(bits)
            w = len(bits)
            width_counts[w] = width_counts.get(w, 0) + 1

        elapsed = time.perf_counter() - start_time

        # 生成训练结果报表
        self._print_report(elapsed, len(all_bits), width_counts)

        return {
            "elapsed": elapsed,
            "rule_count": len(self.rules),
            "unique_bits": len(all_bits),
            "width_distribution": width_counts,
            "covered_all": len(uncovered) == 0,
            "uncovered_count": len(uncovered),
        }

    def _print_report(self, elapsed, unique_bits_count, width_counts):
        """
        打印掩码规则的统计报表。

        Args:
            elapsed (float): 训练总耗时（秒）。
            unique_bits_count (int): 涉及的不重复比特位数量。
            width_counts (dict): 位宽分布字典 {位宽: 规则数}。
        """
        if not self.rules:
            print("[INFO] 未生成任何规则。")
            return

        print("\n========== Mask 生成报表 ==========")
        print(f"训练总耗时: {elapsed:.2f} 秒")
        print(f"规则总数量: {len(self.rules)}")
        print(f"涉及比特位: {unique_bits_count} / 128 个")
        print("位宽分布:")
        for w in sorted(width_counts):
            print(f"  - 位宽 {w:2d}: {width_counts[w]} 条规则")
        print("===================================\n")


if __name__ == "__main__":
    hunter = BitmaskHunter("A.txt", "B.txt")
    hunter.solve()
