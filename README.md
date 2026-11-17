<p align="center"><img src="docs/mechanist-logo.png" alt="Mechanist" width="413" height="100"></p>

# Mechanist Light

**Autonomous mechanistic research, supported by tools and human expertise.**

Mechanist Light supplies research resources without prescribing a pipeline. The model chooses strategy, task organization, method combinations, and whether and how to keep information. There are no required stages, step types, memory schemas, or experimental record files.

## Start

Mechanist is a Claude Code plugin. In Claude Code:

```text
/plugin marketplace add zjunlp/Mechanist
/plugin install mechanist@mechanist
/reload-plugins
/mechanist:mechanist Investigate the internal mechanism behind this behavior: ...
```

For this checkout of the Light branch, launch Claude Code with `claude --plugin-dir /absolute/path/to/Mechanist`; do not assume the marketplace contains these changes. Skills invoke their attached Python scripts directly. Install each script's dependencies in the Python environment used by the host terminal when needed.

For another host, use [the Mechanist skill](skills/mechanist/SKILL.md) as the scientist prompt and resource entry, expose the desired tools, and make the linked files accessible. This is a prompt and resource library, not a standalone research daemon.

## Resources

- [Mechanism methods](skills/mechanism-methods/SKILL.md): method routing, eleven families, thirty-two submethods, papers, API references, and code templates, loaded as needed.
- [Model consultation](skills/model-consultation/SKILL.md): optional external consultation about uncertain questions, code, explanations, and designs. Calls are stateless; send relevant text because the model cannot read local files.
- [Information retrieval](skills/information-retrieval/SKILL.md): one entry for finding and obtaining papers, blog posts, GitHub projects, documentation, and other web information. Use host search/browsing tools or the bundled source-specific scripts as appropriate.
- [Human expertise](skills/human-expertise/SKILL.md): a discoverable skill with a short situation-based index and eleven supporting notes. Detailed Experiment tips cover feature selection, steering strength and sites, fine-tuning LR sweeps, answer measurement, and image preprocessing, alongside broader research experience. Relevant notes load on demand rather than all at once.

Method scripts are reference templates with model and library assumptions, not a universally tested execution API. Unimplemented measurement paths report that limitation. Install dependencies for selected methods in suitable environments; root requirements are a small common starting point, not every method's environment.

## External services

Set variables in the environment inherited by the scripts:

| Variable | Purpose |
| --- | --- |
| `LLM_API_KEY` | Enable Model consultation with your provider key. |
| `LLM_BASE_URL` | Compatible API base URL; default `https://api.openai.com/v1`. |
| `LLM_MODEL` | External consultation model; default `gpt-6.1-sol`. |
| `LLM_FALLBACK_MODEL` | Optional explicit fallback; no model substitution unless configured. |
| `MECHANIC_DB_API_KEY` | Optional key for higher retrieval limits. |
| `MECHANIC_DB_BASE_URL` | Optional search-service URL override. |

Missing consultation credentials do not prevent using the prompt or method library. Mechanic DB supports anonymous access with lower limits; availability and quotas depend on the service. It writes retrievals to caller-selected absolute paths without imposing a research-wide directory. Ordinary file, terminal, web, and delegation tools are supplied by the host when available.

## Script calls

Resolve scripts from their skill directories; the host's terminal runs them directly:

```text
python /path/to/skills/model-consultation/scripts/chat.py --prompt-file /path/to/question.txt
python /path/to/skills/information-retrieval/sources/mechanic_db/search.py --query "feature steering" --output /path/to/papers.json
```

Each skill links its scripts and any required dependencies. Both commands return JSON, report failures with a nonzero exit status, and use environment variables for credentials. Saving an LLM response is optional; retrieval writes its full paper bundle to the caller's chosen output file.

## Example

“Investigate why this model enters repetitive reasoning. Choose methods that distinguish a specific internal signal from generic generation suppression. Use available resources within my compute budget and explain what the evidence supports.”

The model chooses the investigation, method combinations, external consultations, experiments, and notes.


---

## 中文

**为自主机理研究提供工具、人类经验和完整方法库。**

Mechanist Light 不规定科研流水线。基模自主决定研究路线、任务拆分、方法组合，以及是否和如何记录信息；不要求 Stage、Step、全局记忆格式或实验记录文件。

### 使用

在 Claude Code 中安装插件后，通过 `/mechanist:mechanist` 交付自然语言目标。使用本地 Light 分支时，以 `claude --plugin-dir /仓库绝对路径` 加载当前仓库；市场版本不一定包含本分支修改。工具直接调用所属 Skill 的 Python 脚本，按需在宿主终端所用的 Python 环境安装对应依赖。

其他宿主可将 [Mechanist Skill](skills/mechanist/SKILL.md) 用作科学家提示和资源入口，提供需要的工具并开放资料访问。它是提示词与资源库，不是独立科研服务。

### 脚本调用

从对应 Skill 目录定位脚本，用宿主终端执行上面的 Python 命令即可。两个脚本返回 JSON，失败时以非零状态退出，凭证从环境变量读取。LLM 回答按需保存，数据库检索的完整结果写入调用者指定的文件。

### 能力

- 完整保留机理方法选择与路由、11 个家族、32 个具体方法、论文、API 资料与代码模板，按需读取。
- 保留 [Model consultation](skills/model-consultation/SKILL.md)，通过附属脚本自主咨询外部模型。接口无会话记忆，也不能读取本地路径，需要发送实际文本。
- 外部信息检索与获取统一为 [Information retrieval](skills/information-retrieval/SKILL.md) 一个入口，覆盖论文、博客、GitHub 项目、文档和其他网页；按需使用宿主检索/浏览能力或内置来源脚本，提供信息获取与综合指导。
- [Human expertise](skills/human-expertise/SKILL.md) 作为可发现的 Skill，提供情境索引和十一份经验资料；恢复展开的 Experiment tips，涵盖特征选择、干预强度与位置、微调学习率搜索、答案测量和图像预处理，以及其他研究经验。按需读取正文，不一次性注入，也不规定科研阶段。

按需在脚本继承的执行环境中设置上表变量。未配置外部模型不影响方法库；文献服务支持较低限额的匿名检索。方法脚本是需核对依赖、模型和数据后适配的参考模板，不代表对所有环境验证。通用文件、终端、网络及委派能力由宿主提供。

例：“研究这个模型为什么陷入重复推理，区分特定内部信号和普遍生成抑制。在授权预算内自主选择方法，并说明证据支持什么。”


## Credits / 致谢

Mechanist contributors include Mengru Wang, Zhenqian Xu, and Haoxiong Wang. This project incorporates work from ARIS and the method libraries cited alongside the retained examples. Thanks to the community for its contributions and technical support.

感谢 Mechanist 贡献者、ARIS、方法库原作者及社区支持；各方法的论文与来源保留在对应目录。

## Citation / 引用

```bibtex
@article{wang2026mechanist,
  title={Mechanist: AI as a Scientific Instrument for Discovering the Mechanisms of Intelligence},
  author={Wang, Mengru and Fang, Junfeng and Qiao, Shuofei and Xu, Zhenqian and Xu, Haoming and Wang, Haoxiong and Deng, Shumin and Yang, Linyi and Cui, Zhixiang and Xu, Xin and others},
  journal={arXiv preprint arXiv:2608.12036},
  year={2026}
}
```

## License / 许可证

[MIT](LICENSE)
