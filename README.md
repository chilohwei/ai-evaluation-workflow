# AI创意大赛评审系统

这是一个用于AI创意大赛的智能评审系统，可以自动化处理参赛作品的评审、分类和报告生成过程。

## 功能特点

1. **Excel转Markdown**
   - 自动将Excel格式的参赛作品信息转换为Markdown文件
   - 支持批量处理和自动编号
   - 智能清理和格式化项目名称

2. **AI智能评审**
   - 使用多个AI模型（Deepseek和Claude）进行评审
   - 多维度评分系统（创新性、实用性、可行性等）
   - 生成详细的评审意见和建议

3. **智能分类**
   - 自动将项目分类为不同类别（图像类、音视频类等）
   - 使用AI进行智能分类
   - 生成分类统计报告

4. **评审报告生成**
   - 生成美观的HTML格式评审报告
   - 包含数据可视化和统计分析
   - 自动计算和分配奖项

## 安装说明

1. 克隆项目并安装依赖：
```bash
git clone [项目地址]
cd ai-evaluation-workflow
pip install -r requirements.txt
```

2. 配置环境变量：
   - 复制`.env.example`为`.env`
   - 填写必要的API密钥和配置信息

## 使用方法

1. **准备数据**
   - 将参赛作品信息整理到Excel文件中
   - 确保Excel文件格式符合要求

2. **转换格式**
```bash
python 1_excel_to_markdown.py
```

3. **执行评审**
```bash
python 2_ai_evaluator.py
```

4. **项目分类**
```bash
python 3_project_categorizer.py
```

5. **生成报告**
```bash
python 4_report_generator.py
```

## 目录结构

```
ai-evaluation-workflow/
├── 1_excel_to_markdown.py    # Excel转Markdown脚本
├── 2_ai_evaluator.py         # AI评审脚本
├── 3_project_categorizer.py  # 项目分类脚本
├── 4_report_generator.py     # 报告生成脚本
├── requirements.txt          # 项目依赖
├── .env.example             # 环境变量示例
├── 参赛作品/                 # 转换后的Markdown文件
├── 评审结果/                 # AI评审结果
├── 项目分类/                 # 分类结果
└── 评审报告/                 # 生成的HTML报告
```

## 评分标准

系统使用以下维度进行评分：

- 创新性 (20%): 项目的创新程度和独特性
- 实用性 (30%): 解决实际问题的能力
- 技术可行性 (25%): 技术实现的难度和可能性
- 市场潜力 (15%): 商业化和市场发展前景
- 人文精神 (10%): 社会价值和伦理考量

### 同分处理规则
1. 优先考虑创新性得分
2. 其次考虑实用性得分
3. 再次考虑技术可行性得分
4. 最后参考提交时间先后

### 奖项设置
- 一等奖（1名）：总分排名第1，奖金3000元
- 二等奖（2名）：总分排名2-3，奖金2000元
- 三等奖（3名）：总分排名4-6，奖金1000元
- 参与奖：其他参赛项目

## 注意事项

1. 确保API密钥配置正确
2. 评审过程可能需要较长时间，请耐心等待
3. 建议定期备份评审数据
4. 如遇到API限制，可适当调整请求间隔

## 贡献指南

欢迎提交Issue和Pull Request来改进系统。在提交代码前，请确保：

1. 代码符合PEP 8规范
2. 添加必要的注释和文档
3. 更新requirements.txt（如有新依赖）
4. 测试所有功能正常

## 许可证

本项目采用 MIT 许可证。

MIT License

Copyright (c) 2025 AI创意大赛评审系统

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## 联系方式

- 项目维护者: chilohwei
- 邮箱: chilohwei@gmail.com
- 项目链接: https://github.com/chilohwei/ai-evaluation-workflow 
