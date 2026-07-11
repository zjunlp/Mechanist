# 任务:用特征 steering 生成 α 螺旋 DNA —— 验证 Evo2 内部特征能因果控制蛋白二级结构
<!-- 跑法: /auto — behavior-source: given-validation, mechanism: given -->

## 任务概述
在 Evo2-7B 的预训练 SAE 中,找到一组选择性响应"α螺旋"的特征,
再通过放大该特征去自回归生成 DNA,用蛋白质结构预测工具验证生成序列所编码蛋白的
α螺旋含量是否随放大强度升高,证明该特征是可因果操控的旋钮。

## 实验建议
- Steering 系数需要仔细选择，合适的 Steering 系数范围可能非常窄。不要在仅扫描几个 Steering 系数后就轻言放弃；
- 使用 Encoder-Clamp-Decoder 模式进行 Steering 注入。
- 为增强 Steering 的放大效应，可以同时对 5-8 个特征进行干预；
- 先确定找到合适的 Steering 系数范围，再在该 Steering 系数上开展对照实验；
- 使用简单而有说服力的对照实验，不必过于复杂。

## 参考论文
- `papers/Evo2.pdf` —— *Genome modelling and design across all domains of life with Evo 2*。
- `papers/InterPLM.pdf` —— *InterPLM: discovering interpretable features in protein language models*。

## 模型 / 数据
- **Evo2-7B**:`/mnt/quarkfs/share_models/evo2_7b_262k`;
- **SAE(第 26 层)**:`/mnt/quarkfs/share_models/evo2_sae_l26/sae-layer26-mixed-expansion_8-k_64.pt`。
- 其它所需的数据集和工具可参考两篇论文的配置，或自行调研并下载、使用。

## 环境
- conda 环境 `scientist`:torch+CUDA、vortex/evo2、transformers、biopython、DSSP。
- GPU:本机 8×A800-80GB，同时最多占用 4 张 GPU。

## Anti-Cheating Constraints for the Experiment  

- Do not read any datasets, experimental designs, experimental tools, or experimental data from parent folders, to ensure that all experiments are independently completed by you (the Mechanist).  

## 通知设置
- 向 wanghaoxiong@zju.edu.cn 汇报工作进展。