# filename: Python/gen_samples.py
"""
样本生成脚本。

该脚本用于生成两组随机的 MD5 哈希值（集合 A 和集合 B），
作为 BitmaskHunter 算法的输入数据。集合 A 代表"负样本"（不应被匹配），
集合 B 代表"正样本"（需要被匹配）。
"""

import hashlib
import random
import os


def generate_random_md5s(count):
    """
    生成指定数量的随机 MD5 哈希字符串。

    Args:
        count (int): 需要生成的 MD5 哈希数量。

    Returns:
        list: 包含 count 个 MD5 十六进制字符串的列表。
    """
    samples = []
    for _ in range(count):
        random_data = os.urandom(16)
        samples.append(hashlib.md5(random_data).hexdigest())
    return samples


def generate_and_save(total_count, file_a="A.txt", file_b="B.txt"):
    """
    生成随机 MD5 样本并保存到两个文件中。

    Args:
        total_count (int): 总样本数量，会平分为 A、B 两份。
        file_a (str): 负样本输出文件路径。
        file_b (str): 正样本输出文件路径。
    """
    all_hashes = generate_random_md5s(total_count)
    random.shuffle(all_hashes)

    # 将样本平分为两部分：一半给 A，一半给 B
    mid = total_count // 2
    with open(file_a, "w") as f:
        f.write("\n".join(all_hashes[:mid]))
    with open(file_b, "w") as f:
        f.write("\n".join(all_hashes[mid:]))

    print(f"[INFO] 已生成样本：{file_a} ({mid}条), {file_b} ({total_count - mid}条)")


def main():
    """
    主函数：默认生成 200 条样本。
    """
    generate_and_save(200)


if __name__ == "__main__":
    main()
