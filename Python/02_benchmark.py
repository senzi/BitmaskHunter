# filename: Python/benchmark.py
"""
压测脚本：逐步增大样本规模，评估 BitmaskHunter 算法的性能与效果。

运行方式:
    python benchmark.py

逻辑说明:
    - 从 200 条样本起步，根据上一轮训练耗时动态决定下一轮规模。
    - 记录每一轮的样本规模、训练耗时、规则数量、涉及比特位、位宽分布、检出率、误报率。
    - 最终结果输出为 benchmark_report.md。
"""

import os
import sys
import time

# 将脚本所在目录加入模块搜索路径，确保能 import 同级模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 使用 __import__ 导入以数字开头的模块名
_gen_samples = __import__("00_gen_samples")
generate_and_save = _gen_samples.generate_and_save

_train_mask = __import__("01_train_mask")
BitmaskHunter = _train_mask.BitmaskHunter

_verify = __import__("03_verify")
load_rules = _verify.load_rules
check_match = _verify.check_match


def run_benchmark():
    """
    执行多轮压测，动态调整样本规模，最终生成 Markdown 报表。
    """
    results = []
    current_size = 200  # 初始样本规模
    max_size = 500000   # 规模上限
    max_elapsed = 120   # 单轮训练耗时上限（秒），超过则停止

    while True:
        print(f"\n{'=' * 70}")
        print(f"[BENCHMARK] 当前总样本规模: {current_size}")
        print(f"{'=' * 70}")

        # 1. 生成样本
        t0 = time.perf_counter()
        generate_and_save(current_size)
        t_gen = time.perf_counter() - t0

        # 2. 训练掩码规则
        hunter = BitmaskHunter("A.txt", "B.txt")
        stats = hunter.solve(max_width=12)

        # 3. 验证规则效果
        rules = load_rules("rules.mask")
        hashes_a = [int(line.strip(), 16) for line in open("A.txt") if line.strip()]
        hashes_b = [int(line.strip(), 16) for line in open("B.txt") if line.strip()]

        a_wrong = sum(1 for h in hashes_a if check_match(h, rules))
        b_correct = sum(1 for h in hashes_b if check_match(h, rules))

        result = {
            "total_size": current_size,
            "a_size": len(hashes_a),
            "b_size": len(hashes_b),
            "gen_time": t_gen,
            "train_time": stats["elapsed"],
            "rule_count": stats["rule_count"],
            "unique_bits": stats["unique_bits"],
            "width_distribution": stats["width_distribution"],
            "covered_all": stats["covered_all"],
            "uncovered_count": stats["uncovered_count"],
            "a_wrong": a_wrong,
            "b_correct": b_correct,
        }
        results.append(result)

        print(f"[BENCHMARK] 本轮训练耗时: {stats['elapsed']:.2f} 秒")

        # 4. 动态决定下一轮规模
        elapsed = stats["elapsed"]
        if elapsed < 5:
            multiplier = 5
        elif elapsed < 30:
            multiplier = 2
        elif elapsed < max_elapsed:
            multiplier = 1.5
        else:
            print(f"[BENCHMARK] 训练耗时超过 {max_elapsed} 秒，停止压测。")
            break

        next_size = int(current_size * multiplier)
        if next_size > max_size:
            print(f"[BENCHMARK] 达到规模上限 {max_size}，停止压测。")
            break

        # 若完全无法生成规则，后续规模无意义，直接停止
        if stats["rule_count"] == 0:
            print("[BENCHMARK] 未生成任何规则，停止压测。")
            break

        current_size = next_size

    generate_md_report(results)
    print("[BENCHMARK] 全部压测完成。")


def generate_md_report(results):
    """
    根据多轮压测结果生成 Markdown 报表。

    Args:
        results (list): 每轮压测结果字典的列表。
    """
    lines = []
    lines.append("# BitmaskHunter 压测报告\n")

    # 测试参数说明
    lines.append("## 测试参数")
    lines.append("- **算法**: 贪心位掩码搜索 + 蒙特卡洛随机采样")
    lines.append("- **单条规则最大位宽**: 12")
    lines.append("- **每轮位宽随机尝试次数**: 500")
    lines.append("- **样本生成方式**: 随机 MD5（os.urandom + hashlib.md5）")
    lines.append("- **正负样本比例**: 1:1（总样本平分为 A、B 两份）")
    lines.append("- **规模上限**: 500,000 总样本")
    lines.append("- **单轮耗时上限**: 120 秒\n")

    # 汇总表格
    lines.append("## 汇总数据\n")
    lines.append("| 总样本规模 | A规模 | B规模 | 生成耗时(s) | 训练耗时(s) | 规则数量 | 涉及比特位 | 位宽分布 | B检出率 | A误报率 | 是否全覆盖 |")
    lines.append("|-----------|-------|-------|------------|------------|---------|-----------|---------|--------|--------|-----------|")

    for r in results:
        width_dist = ", ".join([f"{k}位:{v}" for k, v in sorted(r["width_distribution"].items())])
        b_rate = f"{(r['b_correct'] / r['b_size']) * 100:.1f}%" if r["b_size"] else "N/A"
        a_rate = f"{(r['a_wrong'] / r['a_size']) * 100:.2f}%" if r["a_size"] else "N/A"
        covered = "是" if r["covered_all"] else f"否(余{r['uncovered_count']})"
        lines.append(
            f"| {r['total_size']} | {r['a_size']} | {r['b_size']} | {r['gen_time']:.3f} | "
            f"{r['train_time']:.2f} | {r['rule_count']} | {r['unique_bits']} / 128 | {width_dist} | "
            f"{b_rate} | {a_rate} | {covered} |"
        )

    lines.append("")

    # 趋势分析（文本柱状图）
    if len(results) >= 2:
        lines.append("## 趋势分析\n")

        # 训练耗时趋势
        lines.append("### 训练耗时随规模变化")
        lines.append("```")
        max_time = max(r["train_time"] for r in results)
        for r in results:
            bar_len = int((r["train_time"] / max_time) * 40) if max_time > 0 else 0
            bar = "█" * bar_len
            lines.append(f"{r['total_size']:>9} | {bar} {r['train_time']:.2f}s")
        lines.append("```\n")

        # 规则数量趋势
        lines.append("### 规则数量随规模变化")
        lines.append("```")
        max_rules = max(r["rule_count"] for r in results)
        for r in results:
            bar_len = int((r["rule_count"] / max_rules) * 40) if max_rules > 0 else 0
            bar = "█" * bar_len
            lines.append(f"{r['total_size']:>9} | {bar} {r['rule_count']}")
        lines.append("```\n")

        # 涉及比特位趋势
        lines.append("### 涉及比特位随规模变化")
        lines.append("```")
        max_bits = max(r["unique_bits"] for r in results)
        for r in results:
            bar_len = int((r["unique_bits"] / max_bits) * 40) if max_bits > 0 else 0
            bar = "█" * bar_len
            lines.append(f"{r['total_size']:>9} | {bar} {r['unique_bits']} / 128")
        lines.append("```\n")

    # 结论与观察
    lines.append("## 结论与观察\n")
    lines.append("1. **训练耗时**: 随着样本规模增大，训练耗时通常呈非线性增长。当正负样本均为随机 MD5 时，由于分布均匀，早期规模增长耗时增长较缓；但当规模达到数万级别后，黑名单计算量和搜索空间急剧膨胀，耗时可能快速上升。")
    lines.append("2. **规则数量**: 规则数量通常随样本规模增加而上升，但增长斜率取决于数据本身的可分性。若正负样本差异显著，规则增长较缓慢；若边界模糊，则可能需要大量细粒度规则。")
    lines.append("3. **涉及比特位**: 随着规则数量增加，涉及的比特位会逐步分散到 128 个位的不同位置，最终趋近于 128（饱和）。")
    lines.append("4. **覆盖能力**: 在随机 MD5 数据上，只要搜索空间（max_width 和尝试次数）足够，算法通常仍能实现 100% 的 B 集合检出和 0% 的 A 集合误报。但若规模过大导致训练超时，可能出现未完全覆盖的情况。")
    lines.append("5. **优化建议**: 若训练耗时成为瓶颈，可考虑降低 max_width、减少每轮尝试次数，或采用更高效的位运算批量计算策略。\n")

    with open("benchmark_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("[BENCHMARK] Markdown 报表已保存至 benchmark_report.md")


if __name__ == "__main__":
    run_benchmark()
