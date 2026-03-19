# Clone Judge

Clone Judge 这是一个使用大语言模型（如智谱 AI / ZhipuAI）来自动化判定代码克隆（Code Clone）关系的工具。
它可以读取包含代码块索引信息的大型 CSV 文件，从本地指定的目录库（`bcb_reduced`）中提取对应的代码片段，以高并发的方式向模型发送检测请求，并将返回判断结果（`TRUE`, `FALSE` 或 `ERROR`）原地回写到被检测的 CSV 文件中。

## 功能特性

- **异步与高并发请求**：利用 `asyncio` 以及可配置的并发度与批处理大小，高速完成针对海量代码对的大语言模型推断。
- **断点续传**：每次启动时会自动校验 CSV 中已有判定结果的行，跳过进度，保障被中断后可无缝恢复。
- **分块写入持久化**：采用 Chunk 机制，到达指定处理数量后会使用临时文件安全地覆写原 CSV，防止断电等意外造成数据丢失。
- **灵活的数据采样**：支持 `--lines` 参数，从提供的庞大数据集中随机抽取 n 行数据进行快速测试或小规模验证。

## 环境准备

1. **配置 Python 环境**：确保您的机器上安装了 Python 3.8 或以上版本。
2. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```
3. **设置 API Key**：
   工具默认从环境变量中读取智谱 AI 密钥。您也可以在运行时通过命令行参数指定。
   ```powershell
   # Windows (PowerShell)
   $env:ZHIPUAI_API_KEY="your_api_key_here"
   ```
   ```bash
   # Linux / macOS
   export ZHIPUAI_API_KEY="your_api_key_here"
   ```

## 数据目录结构

工具默认假定存在如下的数据目录结构，在 `--code-dir`（默认 `data`）下必须包含 `bcb_reduced` 文件夹：

```text
data/
 ├─ ccaligner.csv
 ├─ MSCCD.csv
 └─ bcb_reduced/
     ├─ 10/
     │   └─ selected/
     │       └─ 103760.java
     └─ ...
```

CSV 格式规范（要求至少包含前 8 列）：

1. `dir1`: 代码 1 所在子目录
2. `file1`: 代码 1 的文件名
3. `start1`: 代码 1 起始行号
4. `end1`: 代码 1 结束行号
5. `dir2`: 代码 2 所在子目录
6. `file2`: 代码 2 的文件名
7. `start2`: 代码 2 起始行号
8. `end2`: 代码 2 结束行号
9. _(可选)_ `result`: 判定结果 (`TRUE`, `FALSE` 等，运行本工具后会自动附加上这一列)

## 使用方法

### 基础运行

判定指定的某个或多个 CSV 文件：

```bash
python judge_clone.py --csv-files data/ccaligner.csv data/MSCCD.csv
```

### 随机抽样验证

如果您只想从每个指定的 CSV 文件中随机抽取 100 行样本进行测试：

```bash
python judge_clone.py --csv-files data/ccaligner.csv --lines 100
```

### 命令行参数一览

| 参数名                | 类型      | 默认值                 | 说明                                                        |
| --------------------- | --------- | ---------------------- | ----------------------------------------------------------- |
| `--csv-files`         | `Path(s)` | （必填）               | 需要处理的一个或多个 CSV 文件路径（支持空格分隔多个）。     |
| `--code-dir`          | `Path`    | `data`                 | 代码库的根目录（包含 `bcb_reduced` 的目录）。               |
| `--lines`             | `int`     | `None`                 | (可选) 从每个 CSV 中随机抽取的行数。若不填，则处理全部行。  |
| `--api-key`           | `str`     | `env: ZHIPUAI_API_KEY` | 智谱 AI (或其它支持的) API 密钥。                           |
| `--timeout`           | `int`     | `60`                   | 本次批次检测的超时时间（秒）。                              |
| `--batch-size`        | `int`     | `200`                  | 在一次并发循环中发送检测的代码对数量。                      |
| `--concurrency-limit` | `int`     | `200`                  | 最高允许的并发请求限制。                                    |
| `--prompt-file`       | `Path`    | `prompt_template.txt`  | Prompt 模板文件路径。                                       |
| `--csv-chunk-size`    | `int`     | `1000`                 | 设置每计算多少行就强制将结果保存/覆写回 CSV，防止中途断电。 |

## 结果查看

处理过程中，终端会打印出实时进度及预计完成情况。单个 CSV 文件执行完毕后，控制台会输出 `TRUE` 及 `FALSE` 的数量和比例分析。您可以直接打开源 CSV 文件，会在第九列看到追加的判定结果。
