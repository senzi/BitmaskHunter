# BitmaskHunter

**BitmaskHunter** 是一个基于贪心策略的位掩码发现算法，用于从固定长度二进制指纹（如 MD5、SHA-256、SimHash 等）中自动提取一组碰撞-free 的指纹规则，以实现对特定数据集的高效过滤与区分。

## 核心思想

给定一组"正样本"（必须命中）和一组"负样本"（必须排除），算法从指纹的每一位中贪婪地选取少量关键比特位，构造出仅覆盖正样本、不覆盖负样本的位掩码规则集合。规则以 `(bits, value)` 形式存储，匹配时只需提取固定位并做整数比较，速度极快、存储极小。

## 项目结构

```
BitmaskHunter/
├── Python/          # Python 参考实现
│   ├── README.md
│   ├── 00_gen_samples.py
│   ├── 01_train_mask.py
│   ├── 02_benchmark.py
│   └── 03_verify.py
└── Rust/            # Rust 实现（如有）
    └── ...
```

## 各语言实现

| 语言 | 路径 | 说明 |
|------|------|------|
| Python | [`Python/`](./Python/) | 完整实现，含样本生成、训练、验证、压测脚本 |

## License

MIT
