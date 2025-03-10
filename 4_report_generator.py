#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
报告生成器
这个脚本负责生成HTML格式的评审报告，展示AI评审流程和获奖情况
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
import markdown
from markdown.extensions import fenced_code
from markdown.extensions import codehilite
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer

class ReportGenerator:
    """HTML报告生成器类"""
    
    def __init__(self, projects_dir="参赛作品", reviews_dir="评审结果", data_dir="项目数据", output_file="评审报告.html"):
        """初始化报告生成器
        
        Args:
            projects_dir: 参赛作品目录
            reviews_dir: 评审结果目录
            data_dir: 项目数据目录
            output_file: 输出文件名
        """
        self.projects_dir = projects_dir
        self.reviews_dir = reviews_dir
        self.data_dir = data_dir
        self.output_file = output_file
        
        # 项目数据
        self.projects = []
    
    def load_project_data(self):
        """从项目数据目录加载所有项目数据"""
        print("加载项目数据...")
        
        if not os.path.exists(self.data_dir):
            print(f"错误: 目录不存在 - {self.data_dir}")
            return False
        
        try:
            # 获取所有JSON文件
            json_files = [f for f in os.listdir(self.data_dir) if f.endswith('.json')]
            
            for json_file in json_files:
                file_path = os.path.join(self.data_dir, json_file)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # 提取项目信息
                    project = {
                        "id": data.get("id", ""),
                        "name": data.get("name", ""),
                        "category": data.get("category", "未分类"),
                        "total_score": data.get("total_score", 0),
                        "submitter": data.get("review_content", {}).get("basic_info", {}).get("submitter", "未知"),
                        "brief_review": data.get("review_content", {}).get("brief_review", ""),
                        "scores": data.get("scores", {}),
                        "original_file": os.path.join(self.projects_dir, json_file.replace(".json", ".md")),
                        "review_file": os.path.join(self.reviews_dir, json_file.replace(".json", "_评审.md"))
                    }
                    
                    self.projects.append(project)
            
            # 按总分降序排序
            self.projects.sort(key=lambda x: x.get("total_score", 0), reverse=True)
            
            print(f"成功加载 {len(self.projects)} 个项目")
            return True
            
        except Exception as e:
            print(f"加载项目数据时出错: {e}")
            return False
    
    def read_markdown_file(self, file_path):
        """读取Markdown文件并转换为HTML"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 使用Python-Markdown转换为HTML，启用代码高亮
                    html = markdown.markdown(
                        content,
                        extensions=['fenced_code', 'codehilite', 'tables'],
                        extension_configs={
                            'codehilite': {
                                'css_class': 'highlight',
                                'guess_lang': True
                            }
                        }
                    )
                    return html
            return "<p>文件不存在</p>"
        except Exception as e:
            print(f"读取文件时出错 {file_path}: {e}")
            return f"<p>读取文件时出错: {e}</p>"
    
    def generate_html_report(self):
        """生成HTML报告"""
        print("生成HTML报告...")
        
        # 加载项目数据
        if not self.load_project_data():
            print("生成报告失败: 无法加载项目数据")
            return False
        
        # 构建HTML报告
        html_content = self.generate_html_content(self.projects)
        
        # 写入HTML文件
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"报告已成功生成: {self.output_file}")
            return True
            
        except Exception as e:
            print(f"写入报告时出错: {e}")
            return False
    
    def generate_html_content(self, projects):
        """生成HTML内容"""
        
        # 计算统计数据
        total_projects = len(projects)
        avg_score = sum(p.get('total_score', 0) for p in projects) / total_projects if total_projects > 0 else 0
        max_score = max((p.get('total_score', 0) for p in projects), default=0)
        min_score = min((p.get('total_score', 0) for p in projects), default=0)
        
        return f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>项目评审报告</title>
            <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🏆</text></svg>">
            <style>
            {self.get_css_styles()}
            </style>
        </head>
        <body>
            <div class="container">
                <header class="report-header">
                    <h1>项目评审报告</h1>
                    <p class="report-date">生成日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </header>

                <!-- 评审流程说明 -->
                <section class="process-container">
                    <div class="process-item" data-step="1">
                        <div class="process-icon">📥</div>
                        <h3>数据预处理</h3>
                        <p>收集和整理所有参赛项目的提交材料，确保数据完整性和一致性。</p>
                    </div>
                    <div class="process-item" data-step="2">
                        <div class="process-icon">🤖</div>
                        <h3>AI智能评审</h3>
                        <p>使用AI模型对项目进行初步评估，生成评分和评语建议。</p>
                    </div>
                    <div class="process-item" data-step="3">
                        <div class="process-icon">🔍</div>
                        <h3>项目分类</h3>
                        <p>根据项目特点和评分结果进行分类，便于后续分析和展示。</p>
                    </div>
                    <div class="process-item" data-step="4">
                        <div class="process-icon">📊</div>
                        <h3>结果汇总</h3>
                        <p>汇总评审结果，生成最终报告和数据统计。</p>
                    </div>
                </section>

                <!-- 评审流程详细说明 -->
                <section class="process-details">
                    <h3>评审流程说明</h3>
                    <ol>
                        <li>
                            <strong>数据预处理阶段</strong>
                            <ul>
                                <li>读取Excel表格中的参赛作品信息</li>
                                <li>清理和标准化项目数据</li>
                                <li>生成规范的Markdown文件</li>
                            </ul>
                        </li>
                        <li>
                            <strong>AI智能评审阶段</strong>
                            <ul>
                                <li>使用多个AI模型进行评审：
                                    <ul>
                                        <li>DeepSeek：负责参赛作品"评审"，和"分类"</li>                                
                                        <li>Claude 3.5 Sonnet：负责"锐评"，撰写详细评审报告</li>
                                    </ul>
                                </li>
                                <li>评分维度与权重：
                                    <ul>
                                        <li>创新性 (20%)：评估项目的原创性和独特价值</li>
                                        <li>实用性 (30%)：评估解决实际问题的能力</li>
                                        <li>技术可行性 (25%)：评估技术实现的难度和可能性</li>
                                        <li>市场潜力 (15%)：评估商业化和市场接受度</li>
                                        <li>人文精神 (10%)：评估社会价值和伦理考量</li>
                                    </ul>
                                </li>
                                <li>评分策略：
                                    <ul>
                                        <li>每个维度采用百分制评分（0-100分）</li>
                                        <li>根据权重计算加权总分</li>
                                        <li>分数保留两位小数</li>
                                    </ul>
                                </li>
                                <li>同分处理规则：
                                    <ul>
                                        <li>优先考虑创新性得分</li>
                                        <li>其次考虑实用性得分</li>
                                        <li>再次考虑技术可行性得分</li>
                                        <li>最后参考提交时间先后</li>
                                    </ul>
                                </li>
                            </ul>
                        </li>
                        <li>
                            <strong>项目分类阶段</strong>
                            <ul>
                                <li>基于MECE原则进行项目分类：
                                    <ul>
                                        <li>图像类：图像生成、处理、识别相关</li>
                                        <li>音视频类：音频、视频处理相关</li>
                                        <li>文档类：文档处理、知识管理相关</li>
                                        <li>思想类：思维辅助、决策支持相关</li>
                                        <li>生活类：日常生活、健康相关</li>
                                        <li>工作类：职场、办公相关</li>
                                        <li>教育类：学习、培训相关</li>
                                        <li>社交类：社交、情感相关</li>
                                    </ul>
                                </li>
                                <li>确保分类的互斥性和完整性</li>
                                <li>使用DeepSeek模型进行智能分类</li>
                            </ul>
                        </li>
                        <li>
                            <strong>结果汇总阶段</strong>
                            <ul>
                                <li>生成评审报告：
                                    <ul>
                                        <li>项目基本信息</li>
                                        <li>各维度得分详情</li>
                                        <li>评审意见和建议</li>
                                        <li>改进方向指导</li>
                                    </ul>
                                </li>
                            </ul>
                        </li>
                    </ol>
                </section>

                <!-- 评审数据统计 -->
                <section class="evaluation-stats">
                    <h3>评审数据统计</h3>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <div class="stat-icon">📝</div>
                            <div class="stat-value">{total_projects}</div>
                            <div class="stat-label">参与项目数</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-icon">⭐</div>
                            <div class="stat-value">{max_score:.2f}</div>
                            <div class="stat-label">最高分</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-icon">📊</div>
                            <div class="stat-value">{avg_score:.2f}</div>
                            <div class="stat-label">平均分</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-icon">📉</div>
                            <div class="stat-value">{min_score:.2f}</div>
                            <div class="stat-label">最低分</div>
                        </div>
                    </div>
                </section>

                <!-- 项目列表 -->
                <section class="participants-section">
                    <h2>参与项目</h2>
                    <div class="results-table-container">
                        <table class="results-table">
                            <thead>
                                <tr>
                                    <th>排名</th>
                                    <th>项目名称</th>
                                    <th>提交人</th>
                                    <th>分类</th>
                                    <th>总分</th>
                                    <th>锐评</th>
                                    <th>操作</th>
                                </tr>
                            </thead>
                            <tbody>
                                {self.generate_table_rows_html(projects)}
                            </tbody>
                        </table>
                    </div>
                </section>

                <footer class="report-footer">
                    <p>本评审过程完全公开透明，评分标准统一，确保公平公正。</p>
                    <p>项目开源地址: <a href="https://github.com/chilohwei/ai-evaluation-workflow" target="_blank">GitHub</a></p>
                </footer>
            </div>

            <!-- Modal -->
            <div id="modal" class="modal">
                <div class="modal-content">
                    <span class="close">&times;</span>
                    <div class="tab-buttons">
                        <button id="proposal-tab" class="tab-button active">原始提交</button>
                        <button id="review-tab" class="tab-button">评审结果</button>
                    </div>
                    <div id="modal-content"></div>
                </div>
            </div>

            <script>
            {self.get_javascript_code()}
            </script>
        </body>
        </html>
        """
    
    def generate_award_cards_html(self, award_projects):
        """生成获奖项目卡片HTML"""
        cards_html = ""
        
        for project in award_projects:
            award = project.get("award", "")
            award_color = self.awards.get(award, {}).get("color", "#A5D6A7")
            prize = self.awards.get(award, {}).get("prize", "")
            
            # 读取原始提交和评审结果文件内容
            proposal_content = self.read_markdown_file(project.get('original_file', ''))
            review_content = self.read_markdown_file(project.get('review_file', ''))
            
            cards_html += f"""
            <div class="award-card" style="--award-color: {award_color}">
                <div class="award-header">
                    <div class="award-badge">{award}</div>
                    <div class="award-prize">{prize}</div>
                </div>
                <div class="award-content">
                    <h3 class="project-title">{project.get('name', '')}</h3>
                    <div class="project-meta">
                        <span class="project-category">{project.get('category', '未分类')}</span>
                        <span class="project-score">总分: {project.get('total_score', 0)}</span>
                    </div>
                    <div class="project-submitter">提交人: {project.get('submitter', '未知')}</div>
                    <div class="project-review">"{project.get('brief_review', '')}"</div>
                    <div class="project-actions">
                        <button class="view-proposal" 
                            data-file="{project.get('original_file', '')}"
                            data-content="{proposal_content.replace('"', '&quot;')}">原始提交</button>
                        <button class="view-review" 
                            data-file="{project.get('review_file', '')}"
                            data-content="{review_content.replace('"', '&quot;')}">评审结果</button>
                    </div>
                </div>
            </div>"""
        
        return cards_html
    
    def generate_table_rows_html(self, projects):
        """生成表格行HTML"""
        rows_html = ""
        
        for i, project in enumerate(projects, start=1):
            # 读取原始提交和评审结果文件内容
            proposal_content = self.read_markdown_file(project.get('original_file', ''))
            review_content = self.read_markdown_file(project.get('review_file', ''))
            
            # 使用项目ID作为锚点
            project_id = project.get('id', f"project-{i}")
            
            # 处理项目名称，移除前缀数字和下划线
            project_name = project.get('name', '')
            # 使用正则表达式移除前缀数字和下划线，如 "29_项目名称" 变成 "项目名称"
            clean_name = re.sub(r'^\d+_', '', project_name)
            
            rows_html += f"""
            <tr id="{project_id}">
                <td>{i}</td>
                <td>{clean_name}</td>
                <td>{project.get('submitter', '未知')}</td>
                <td>{project.get('category', '未分类')}</td>
                <td>{project.get('total_score', 0)}</td>
                <td class="brief-review">{project.get('brief_review', '')}</td>
                <td>
                    <button class="view-proposal" 
                        data-file="{project.get('original_file', '')}"
                        data-content="{proposal_content.replace('"', '&quot;')}"
                        data-project-id="{project_id}">原始提交</button>
                    <button class="view-review" 
                        data-file="{project.get('review_file', '')}"
                        data-content="{review_content.replace('"', '&quot;')}"
                        data-project-id="{project_id}">评审结果</button>
                </td>
            </tr>"""
        
        return rows_html
    
    def get_css_styles(self):
        """获取CSS样式"""
        # 添加Pygments的代码高亮样式
        pygments_css = HtmlFormatter().get_style_defs('.highlight')
        
        return pygments_css + """
    :root {
            --primary-color: #1a73e8;
            --primary-color-rgb: 26, 115, 232;
            --secondary-color: #4285f4;
            --text-color: #202124;
            --background-color: #ffffff;
            --border-color: #dadce0;
            --success-color: #0f9d58;
            --warning-color: #f4b400;
            --error-color: #d93025;
            --spacing-unit: 8px;
            --timeline-color: var(--primary-color);
            --timeline-dot-size: 20px;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }

        body {
            background-color: #f8f9fa;
            color: var(--text-color);
            line-height: 1.6;
            width: 100%;
            overflow-x: hidden;
        }

        .container {
            width: 100%;
            max-width: 1600px;
            margin: 0 auto;
            padding: calc(var(--spacing-unit) * 3);
        }

        .report-header {
            text-align: center;
            padding: calc(var(--spacing-unit) * 6) 0;
            margin-bottom: calc(var(--spacing-unit) * 6);
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            border-radius: 12px;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
            position: relative;
            overflow: hidden;
        }

        .report-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="none" stroke="white" stroke-width="1" opacity="0.2"/></svg>');
            background-size: 150px 150px;
            opacity: 0.1;
        }

        .report-header h1 {
            font-size: 3em;
            margin-bottom: calc(var(--spacing-unit) * 2);
            font-weight: 700;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }

        .report-date {
            font-size: 1.2em;
            opacity: 0.9;
        }

        section {
            background: var(--background-color);
            border-radius: 12px;
            padding: calc(var(--spacing-unit) * 4);
            margin-bottom: calc(var(--spacing-unit) * 6);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }

        section h2 {
            color: var(--primary-color);
            margin-bottom: calc(var(--spacing-unit) * 4);
            font-size: 2em;
            font-weight: 600;
            position: relative;
            padding-bottom: calc(var(--spacing-unit) * 1.5);
            text-align: center;
        }

        section h2::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 80px;
            height: 4px;
            background: var(--primary-color);
            border-radius: 2px;
        }

        /* 按钮样式 */
        button {
            padding: calc(var(--spacing-unit) * 1.5) calc(var(--spacing-unit) * 2);
            border: none;
            border-radius: 6px;
            font-size: 1em;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .view-proposal, .view-review {
            flex: 1;
            margin: 0 calc(var(--spacing-unit) * 0.5);
        }
        
        .view-proposal {
            background-color: #e8f0fe;
            color: var(--primary-color);
        }
        
        .view-proposal:hover {
            background-color: #d2e3fc;
            transform: translateY(-2px);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        .view-proposal::before {
            content: '📄';
            margin-right: calc(var(--spacing-unit) * 0.5);
        }
        
        .view-review {
            background-color: #e6f4ea;
            color: var(--success-color);
        }
        
        .view-review:hover {
            background-color: #ceead6;
            transform: translateY(-2px);
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        .view-review::before {
            content: '📝';
            margin-right: calc(var(--spacing-unit) * 0.5);
        }
        
        /* 参与项目表格样式 */
        .results-table-container {
            overflow-x: auto;
            margin-top: calc(var(--spacing-unit) * 4);
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }
        
        .results-table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            background: white;
        }
        
        .results-table th {
            background-color: #f1f3f4;
            padding: calc(var(--spacing-unit) * 2);
            font-weight: 600;
            color: var(--primary-color);
            border-bottom: 2px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 10;
        }
        
        .results-table td {
            padding: calc(var(--spacing-unit) * 2);
            border-bottom: 1px solid var(--border-color);
            vertical-align: middle;
        }
        
        .results-table tr:hover {
            background-color: #f8f9fa;
        }
        
        .results-table tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        
        .results-table tr:nth-child(even):hover {
            background-color: #f1f3f4;
        }
        
        .brief-review {
            max-width: 300px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        /* 表格操作列样式 */
        .results-table td:last-child {
            display: flex;
            gap: calc(var(--spacing-unit));
            justify-content: center;
            min-width: 220px;
        }
        
        /* 模态对话框 */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.6);
            z-index: 1000;
            backdrop-filter: blur(4px);
        }
        
        /* 模态对话框内容样式 */
        .modal-content {
            position: relative;
            background-color: var(--background-color);
            margin: 5vh auto;
            padding: calc(var(--spacing-unit) * 4);
            width: 90%;
            max-width: 1000px;
            max-height: 90vh;
            overflow-y: auto;
            border-radius: 12px;
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.2);
            animation: modalFadeIn 0.3s ease;
        }
        
        @keyframes modalFadeIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .close {
            position: absolute;
            right: 15px;
            top: 15px;
            font-size: 1.8em;
            font-weight: bold;
            color: var(--text-color);
            cursor: pointer;
            z-index: 1010;
            background-color: var(--background-color);
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        
        .close:hover {
            color: var(--primary-color);
            transform: scale(1.1);
        }
        
        /* Markdown 内容样式 */
        .markdown-content {
            background: white;
            border-radius: 8px;
            padding: calc(var(--spacing-unit) * 3);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            line-height: 1.6;
        }
        
        .markdown-content h1 {
            font-size: 2em;
            color: var(--primary-color);
            margin-bottom: calc(var(--spacing-unit) * 2);
            padding-bottom: calc(var(--spacing-unit));
            border-bottom: 1px solid #eee;
        }
        
        .markdown-content h2 {
            font-size: 1.5em;
            color: var(--primary-color);
            margin: calc(var(--spacing-unit) * 3) 0 calc(var(--spacing-unit) * 2);
            padding-bottom: calc(var(--spacing-unit) * 0.5);
            border-bottom: 1px solid #eee;
        }
        
        .markdown-content h3 {
            font-size: 1.3em;
            color: var(--text-color);
            margin: calc(var(--spacing-unit) * 2) 0 calc(var(--spacing-unit));
        }
        
        .markdown-content h4 {
            font-size: 1.1em;
            color: var(--text-color);
            margin: calc(var(--spacing-unit) * 1.5) 0 calc(var(--spacing-unit));
            font-weight: 600;
        }
        
        .markdown-content p {
            margin-bottom: calc(var(--spacing-unit) * 1.5);
        }
        
        .markdown-content ul, .markdown-content ol {
            margin-bottom: calc(var(--spacing-unit) * 2);
            padding-left: calc(var(--spacing-unit) * 3);
        }
        
        .markdown-content li {
            margin-bottom: calc(var(--spacing-unit) * 0.5);
        }
        
        .markdown-content table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: calc(var(--spacing-unit) * 2);
        }
        
        .markdown-content table td, .markdown-content table th {
            border: 1px solid #ddd;
            padding: calc(var(--spacing-unit));
        }
        
        .markdown-content table tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        
        .markdown-content strong {
            font-weight: 600;
            color: #333;
        }
        
        .markdown-content em {
            font-style: italic;
        }
        
        /* 基本信息表格样式 */
        .basic-info-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin: calc(var(--spacing-unit) * 3) 0;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }
        
        .basic-info-table tr {
            background: white;
        }
        
        .basic-info-table tr:nth-child(even) {
            background: #f8f9fa;
        }
        
        .basic-info-table td {
            padding: calc(var(--spacing-unit) * 1.5);
            border: 1px solid #eee;
        }
        
        .basic-info-table td:first-child {
            width: 120px;
            font-weight: 600;
            color: var(--primary-color);
            background: #f1f3f4;
        }
        
        .basic-info-table tr.separator {
            display: none;
        }
        
        /* 搜索和筛选样式 */
        .filter-container {
            display: flex;
            flex-wrap: wrap;
            gap: calc(var(--spacing-unit) * 2);
            margin-bottom: calc(var(--spacing-unit) * 3);
            padding: calc(var(--spacing-unit) * 2);
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        
        .search-container {
            display: flex;
            flex: 1;
            min-width: 250px;
        }
        
        .search-input-wrapper {
            position: relative;
            display: flex;
            align-items: center;
            flex: 1;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            background-color: white;
            transition: box-shadow 0.3s ease;
        }
        
        .search-input-wrapper:focus-within {
            box-shadow: 0 0 0 2px rgba(var(--primary-color-rgb), 0.3);
            border-color: var(--primary-color);
        }
        
        .search-icon {
            position: absolute;
            left: 10px;
            color: #888;
            font-style: normal;
        }
        
        .search-container input {
            flex: 1;
            padding: calc(var(--spacing-unit) * 1.5);
            padding-left: 35px;
            border: none;
            border-radius: 4px;
            font-size: 1em;
            outline: none;
            background: transparent;
        }
        
        .category-container {
            display: flex;
            align-items: center;
            margin-left: calc(var(--spacing-unit) * 2);
        }
        
        .category-container label {
            font-weight: 500;
            color: var(--text-color);
        }
        
        .category-container select {
            padding: calc(var(--spacing-unit) * 1.5);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            background: white;
            font-size: 1em;
            min-width: 150px;
        }
        
        /* 确保锐评列全部可见 */
        .brief-review {
            white-space: normal !important;
            max-width: none !important;
            overflow: visible !important;
            text-overflow: clip !important;
        }
        
        /* 页脚 */
        .report-footer {
            text-align: center;
            margin-top: calc(var(--spacing-unit) * 6);
            padding-top: calc(var(--spacing-unit) * 4);
            border-top: 1px solid var(--border-color);
            color: #5f6368;
        }
        
        .report-footer a {
            color: var(--primary-color);
            text-decoration: none;
            transition: color 0.3s ease;
        }
        
        .report-footer a:hover {
            color: var(--secondary-color);
            text-decoration: underline;
        }
        
        /* 响应式设计 */
        @media (max-width: 1200px) {
            .results-table-container {
                overflow-x: auto;
            }
            
            .results-table {
                width: 100%;
            }
        }
        
        @media (max-width: 768px) {
            .container {
                padding: var(--spacing-unit);
            }
            
            .results-table-container {
                overflow-x: auto;
            }
            
            .results-table {
                width: 100%;
            }
            
            .modal-content {
                width: 95%;
                margin: 2.5vh auto;
                padding: calc(var(--spacing-unit) * 2);
            }
            
            .tab-buttons {
                flex-wrap: wrap;
            }
            
            .results-table td:last-child {
                flex-direction: column;
                min-width: 120px;
            }
        }
        
        /* 添加tab和表格相关的CSS样式 */
        .tab-buttons {
            display: flex;
            gap: calc(var(--spacing-unit) * 1);
            margin-bottom: calc(var(--spacing-unit) * 2);
            border-bottom: 1px solid var(--border-color);
            padding: calc(var(--spacing-unit) * 1) 0;
        }
        
        .tab-button {
            padding: calc(var(--spacing-unit) * 1) calc(var(--spacing-unit) * 2);
            border: none;
            border-radius: 6px;
            font-size: 1em;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            background-color: #f1f3f4;
            color: #5f6368;
            display: flex;
            align-items: center;
            gap: calc(var(--spacing-unit));
        }
        
        .tab-button.active {
            background-color: var(--primary-color);
            color: white;
        }
        
        .tab-button:hover:not(.active) {
            background-color: #e8eaed;
        }
        
        /* 高亮行样式 */
        .highlight-row {
            background-color: #ffeeba !important;
            transition: background-color 0.5s ease;
        }
        
        /* 评审流程样式 */
        .process-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: calc(var(--spacing-unit) * 4);
            margin: calc(var(--spacing-unit) * 4) 0;
            position: relative;
        }

        .process-item {
            background: white;
            padding: calc(var(--spacing-unit) * 3);
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            text-align: center;
            position: relative;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .process-item:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
        }

        .process-item::before {
            content: attr(data-step);
            position: absolute;
            top: -15px;
            left: 50%;
            transform: translateX(-50%);
            width: 30px;
            height: 30px;
            background: var(--primary-color);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .process-icon {
            font-size: 2.5em;
            margin-bottom: calc(var(--spacing-unit) * 2);
            color: var(--primary-color);
        }

        .process-item h3 {
            color: var(--primary-color);
            margin-bottom: calc(var(--spacing-unit));
            font-size: 1.2em;
        }

        .process-item p {
            color: #5f6368;
            font-size: 0.95em;
            line-height: 1.5;
        }

        /* 流程详细说明样式 */
        .process-details {
            background: white;
            padding: calc(var(--spacing-unit) * 4);
            border-radius: 12px;
            margin-top: calc(var(--spacing-unit) * 4);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }

        .process-details h3 {
            color: var(--primary-color);
            margin-bottom: calc(var(--spacing-unit) * 3);
            font-size: 1.4em;
            text-align: center;
        }

        .process-details ol {
            counter-reset: process-counter;
            list-style: none;
            padding: 0;
        }

        .process-details ol > li {
            counter-increment: process-counter;
            position: relative;
            padding-left: calc(var(--spacing-unit) * 5);
            margin-bottom: calc(var(--spacing-unit) * 4);
        }

        .process-details ol > li::before {
            content: counter(process-counter);
            position: absolute;
            left: 0;
            top: 0;
            width: 30px;
            height: 30px;
            background: var(--primary-color);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
        }

        .process-details ul {
            list-style: none;
            padding-left: calc(var(--spacing-unit) * 2);
            margin-top: calc(var(--spacing-unit));
        }

        .process-details ul li {
            position: relative;
            padding-left: calc(var(--spacing-unit) * 2);
            margin-bottom: calc(var(--spacing-unit));
        }

        .process-details ul li::before {
            content: '•';
            position: absolute;
            left: 0;
            color: var(--primary-color);
            font-weight: bold;
        }

        .process-details ul ul {
            margin-top: calc(var(--spacing-unit));
        }

        .process-details strong {
            color: var(--primary-color);
            font-weight: 600;
        }

        /* 评审数据统计样式 */
        .evaluation-stats {
            margin-top: calc(var(--spacing-unit) * 4);
            background: white;
            padding: calc(var(--spacing-unit) * 4);
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }

        .evaluation-stats h3 {
            color: var(--primary-color);
            text-align: center;
            margin-bottom: calc(var(--spacing-unit) * 4);
            font-size: 1.4em;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: calc(var(--spacing-unit) * 3);
        }

        .stat-item {
            text-align: center;
            padding: calc(var(--spacing-unit) * 3);
            background: #f8f9fa;
            border-radius: 12px;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }

        .stat-item:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
        }

        .stat-icon {
            font-size: 2.5em;
            margin-bottom: calc(var(--spacing-unit) * 2);
            color: var(--primary-color);
        }

        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: var(--primary-color);
            margin-bottom: calc(var(--spacing-unit));
        }

        .stat-label {
            color: #5f6368;
            font-size: 1.1em;
        }

        @media (max-width: 768px) {
            .process-container {
                grid-template-columns: 1fr;
            }

            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }

            .process-details ol > li {
                padding-left: calc(var(--spacing-unit) * 4);
            }
        }

        @media (max-width: 480px) {
            .stats-grid {
                grid-template-columns: 1fr;
            }
        }
        """
    
    def get_javascript_code(self):
        """获取JavaScript代码"""
        return """
        // 获取模态框元素
        const modal = document.getElementById('modal');
        const modalContent = document.getElementById('modal-content');
        const closeBtn = document.getElementsByClassName('close')[0];
        
        // 当前查看的项目数据
        let currentProjectData = {
            projectName: '',
            proposalContent: '',
            reviewContent: '',
            activeTab: 'proposal', // 当前激活的tab
            projectId: '' // 项目ID，用于锚点
        };
        
        // 为所有"原始提交"和"评审结果"按钮添加点击事件
        document.querySelectorAll('.view-proposal, .view-review').forEach(button => {
            button.addEventListener('click', function() {
                const filePath = this.getAttribute('data-file');
                const isProposal = this.classList.contains('view-proposal');
                const projectId = this.getAttribute('data-project-id');
                
                // 提取项目名称和基础文件路径
                const projectName = filePath.match(/\d+_(.+?)(?:_评审)?\\.md$/)[1];
                
                // 找到对应的另一个按钮
                const parentElement = this.parentElement;
                const proposalButton = parentElement.querySelector('.view-proposal');
                const reviewButton = parentElement.querySelector('.view-review');
                
                // 获取两个内容
                currentProjectData = {
                    projectName: projectName,
                    proposalContent: proposalButton.getAttribute('data-content'),
                    reviewContent: reviewButton.getAttribute('data-content'),
                    activeTab: isProposal ? 'proposal' : 'review',
                    projectId: projectId
                };
                
                // 更新URL锚点，不刷新页面
                if (history.pushState) {
                    history.pushState(null, null, '#' + projectId);
                } else {
                    location.hash = '#' + projectId;
                }
                
                // 显示模态框
                showModal();
            });
        });
        
        // 显示模态框
        function showModal() {
            // 设置激活的tab
            document.querySelectorAll('.tab-button').forEach(button => {
                const isProposalTab = button.id === 'proposal-tab';
                button.classList.toggle('active', 
                    (isProposalTab && currentProjectData.activeTab === 'proposal') || 
                    (!isProposalTab && currentProjectData.activeTab === 'review')
                );
            });
            
            // 更新内容
            modalContent.innerHTML = `
                <div class="markdown-content">
                    ${currentProjectData.activeTab === 'proposal' ? currentProjectData.proposalContent : currentProjectData.reviewContent}
                </div>
            `;
            
            // 显示模态框
            modal.style.display = 'block';
            
            // 如果是评审结果，检查并转换基本信息表格
            if (currentProjectData.activeTab === 'review') {
                const basicInfoTable = modalContent.querySelector('table');
                if (basicInfoTable) {
                    basicInfoTable.className = 'basic-info-table';
                }
            }
        }
        
        // 关闭模态框
        closeBtn.addEventListener('click', function() {
            modal.style.display = 'none';
            // 移除URL锚点，但不刷新页面
            if (history.pushState) {
                history.pushState("", document.title, window.location.pathname + window.location.search);
            }
            resetCurrentProjectData();
        });
        
        // 点击模态框外部关闭
        window.addEventListener('click', function(event) {
            if (event.target === modal) {
                modal.style.display = 'none';
                // 移除URL锚点，但不刷新页面
                if (history.pushState) {
                    history.pushState("", document.title, window.location.pathname + window.location.search);
                }
                resetCurrentProjectData();
            }
        });
        
        // 重置项目数据
        function resetCurrentProjectData() {
            currentProjectData = {
                projectName: '',
                proposalContent: '',
                reviewContent: '',
                activeTab: 'proposal',
                projectId: ''
            };
        }
        
        // 检查URL锚点并自动打开相应的模态框
        function checkUrlHash() {
            if (window.location.hash) {
                const projectId = window.location.hash.substring(1); // 去掉#号
                const projectRow = document.getElementById(projectId);
                if (projectRow) {
                    // 滚动到对应的行
                    projectRow.scrollIntoView({behavior: 'smooth'});
                    
                    // 高亮该行
                    projectRow.classList.add('highlight-row');
                    setTimeout(() => {
                        projectRow.classList.remove('highlight-row');
                    }, 3000);
                    
                    // 如果需要，自动点击查看按钮
                    const viewButton = projectRow.querySelector('.view-proposal');
                    if (viewButton) {
                        // 延迟一点时间再点击，让用户看到高亮的行
                        setTimeout(() => {
                            viewButton.click();
                        }, 800);
                    }
                }
            }
        }
        
        // 页面加载完成后检查URL锚点
        document.addEventListener('DOMContentLoaded', function() {
            // 添加高亮样式
            const style = document.createElement('style');
            style.textContent = `
                .highlight-row {
                    background-color: #ffeeba !important;
                    transition: background-color 0.5s ease;
                }
            `;
            document.head.appendChild(style);
            
            // 添加tab切换事件监听器
            document.querySelectorAll('.tab-button').forEach(button => {
                button.addEventListener('click', function() {
                    const isProposalTab = this.id === 'proposal-tab';
                    const newTab = isProposalTab ? 'proposal' : 'review';
                    
                    if (newTab !== currentProjectData.activeTab) {
                        currentProjectData.activeTab = newTab;
                        
                        // 更新tab按钮状态
                        document.querySelectorAll('.tab-button').forEach(btn => {
                            btn.classList.toggle('active', 
                                (btn.id === 'proposal-tab' && newTab === 'proposal') || 
                                (btn.id === 'review-tab' && newTab === 'review')
                            );
                        });
                        
                        // 更新内容
                        modalContent.innerHTML = `
                            <div class="markdown-content">
                                ${newTab === 'proposal' ? currentProjectData.proposalContent : currentProjectData.reviewContent}
                            </div>
                        `;
                        
                        // 如果是评审结果，检查并转换基本信息表格
                        if (newTab === 'review') {
                            const basicInfoTable = modalContent.querySelector('table');
                            if (basicInfoTable) {
                                basicInfoTable.className = 'basic-info-table';
                            }
                        }
                    }
                });
            });
            
            // 创建搜索和筛选控件
            const participantsSection = document.querySelector('.participants-section');
            const tableContainer = document.querySelector('.results-table-container');
            
            if (participantsSection && tableContainer) {
                // 创建搜索和筛选容器
                const filterContainer = document.createElement('div');
                filterContainer.className = 'filter-container';
                
                // 创建搜索框
                const searchContainer = document.createElement('div');
                searchContainer.className = 'search-container';
                searchContainer.innerHTML = `
                    <div class="search-input-wrapper">
                        <i class="search-icon">🔍</i>
                        <input type="text" id="search-input" placeholder="搜索项目名称或提交人..." />
                    </div>
                `;
                
                // 创建分类筛选下拉框
                const categoryContainer = document.createElement('div');
                categoryContainer.className = 'category-container';
                
                // 获取所有分类
                const categories = new Set();
                document.querySelectorAll('.results-table tbody tr').forEach(row => {
                    const category = row.querySelector('td:nth-child(4)').textContent;
                    categories.add(category);
                });
                
                // 创建分类下拉框
                let categoryOptions = '<option value="">所有分类</option>';
                categories.forEach(category => {
                    categoryOptions += `<option value="${category}">${category}</option>`;
                });
                
                categoryContainer.innerHTML = `
                    <label for="category-select">分类筛选:</label>
                    <select id="category-select">
                        ${categoryOptions}
                    </select>
                `;
                
                // 添加到筛选容器
                filterContainer.appendChild(searchContainer);
                filterContainer.appendChild(categoryContainer);
                
                // 插入到表格前
                participantsSection.insertBefore(filterContainer, tableContainer);
                
                // 添加搜索和筛选事件
                const searchInput = document.getElementById('search-input');
                const categorySelect = document.getElementById('category-select');
                
                // 搜索函数
                function filterTable() {
                    const searchTerm = searchInput.value.toLowerCase();
                    const selectedCategory = categorySelect.value;
                    
                    document.querySelectorAll('.results-table tbody tr').forEach(row => {
                        const projectName = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
                        const submitter = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
                        const category = row.querySelector('td:nth-child(4)').textContent;
                        
                        const matchesSearch = projectName.includes(searchTerm) || submitter.includes(searchTerm);
                        const matchesCategory = selectedCategory === '' || category === selectedCategory;
                        
                        row.style.display = matchesSearch && matchesCategory ? '' : 'none';
                    });
                }
                
                // 添加事件监听器
                // 实时搜索：在输入时触发搜索
                searchInput.addEventListener('input', filterTable);
                searchInput.addEventListener('keyup', function(event) {
                    if (event.key === 'Enter') {
                        filterTable();
                    }
                });
                categorySelect.addEventListener('change', filterTable);
            }
            
            // 确保锐评列全部可见
            document.querySelectorAll('.brief-review').forEach(cell => {
                cell.style.whiteSpace = 'normal';
                cell.style.maxWidth = 'none';
                cell.style.overflow = 'visible';
                cell.style.textOverflow = 'clip';
            });
            
            // 检查URL锚点
            checkUrlHash();
        });
        
        // 监听URL锚点变化
        window.addEventListener('hashchange', checkUrlHash);
        """

def main():
    """主函数"""
    generator = ReportGenerator()
    generator.generate_html_report()

if __name__ == "__main__":
    main() 
