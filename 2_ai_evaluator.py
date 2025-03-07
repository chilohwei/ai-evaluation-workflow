import os
import json
import requests
from datetime import datetime
import markdown
import re
import time
import random
import pandas as pd
from difflib import SequenceMatcher
from pathlib import Path
import openai
from openai import OpenAI
from tqdm import tqdm
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

class AIEvaluator:
    def __init__(self):
        # 从.env文件加载配置
        self.deepseek_api_base_url = os.getenv("DEEPSEEK_API_BASE_URL")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.claude_api_base_url = os.getenv("CLAUDE_API_BASE_URL")
        self.claude_api_key = os.getenv("CLAUDE_API_KEY")
        self.max_retries = int(os.getenv("MAX_RETRIES", "5"))
        self.retry_delay = int(os.getenv("RETRY_DELAY", "3"))
        
        if not self.deepseek_api_base_url:
            raise ValueError("请在.env文件中设置DEEPSEEK_API_BASE_URL")
        if not self.deepseek_api_key:
            raise ValueError("请在.env文件中设置DEEPSEEK_API_KEY")
        if not self.claude_api_base_url:
            raise ValueError("请在.env文件中设置CLAUDE_API_BASE_URL")
        if not self.claude_api_key:
            raise ValueError("请在.env文件中设置CLAUDE_API_KEY")
            
        self.client = OpenAI(api_key=self.claude_api_key)
        self.submissions_dir = "参赛作品"
        self.results_dir = "评审结果"
        self.project_data_dir = "项目数据"  # 添加项目数据目录
        self.weights = {
            "创新性": 0.20,
            "实用性": 0.30,
            "技术可行性": 0.25,
            "市场潜力": 0.15,
            "人文精神": 0.10
        }
        
        # 提交人信息映射
        self.excel_file = 'AI创意大赛全部已去重.xlsx'
        self.project_to_submitter = {}   # 项目名称到提交人的映射
        self.normalized_projects = {}    # 标准化项目名称到原始名称的映射
        self.submitter_projects = {}     # 提交人到项目列表的映射（反向查找）
        
        # 特殊映射处理 - 手动定义一些特殊情况的项目名称匹配
        self.special_mappings = {
            'AI个性化健康教练轻量化版': 'AI个性化健康教练（轻量化版）',
            'AI_Hug__Kiss': 'AI Hug & Kiss',
            'OutfitFlow_AI_服饰流AI': 'OutfitFlow AI （服饰流AI）',
            'AI学习伙伴SkillSpark': 'AI学习伙伴——SkillSpark',
            'AI_智能菜谱': '智能菜谱',
            'AI_智能衣橱规划师': '智能衣橱规划师',
            'AI_博物馆讲解员': 'AI博物馆讲解员',
            'AI_梗图表情包生成器': 'AI梗图表情包生成器',
            'AI_文件整理工具': 'AI文件整理工具',
            'AI_助眠让AI哄你入梦乡': 'AI助眠',
            'AI陪伴__AI同龄人': 'AI同龄人',
            'aixx视频新闻自动生成or生成工具类': 'AI视频新闻自动生成',
            'AI截图笔记AI截图整理AI随拍随记': 'AI截图笔记',
            'PDF处理工具垂直场景文档自动化': 'PDF处理工具',
            'AI赋能PDF智能审查多语言支持语音交互与3D可视化文档管理革命': 'AI赋能PDF智能审查',
            'AI运势管家StarForYou': 'AI运势管家',
            '灵伴AI情感陪伴助手': 'AI情感陪伴助手',
            '科学家连夜下架用手机摄像头就能看穿你未来10年当玄学遇上AI科技与人文的十字路口': '科学家连夜下架',
            'Recraft_like的产品': 'Recraft',
            'Walles_like的产品': 'Walles'
        }
        
        # 加载提交人信息
        print("初始化项目与提交人映射关系...")
        if os.path.exists(self.excel_file):
            self.load_submitter_info()
        else:
            print(f"警告: Excel文件 '{self.excel_file}' 不存在，无法加载提交人信息")
        
    def similar(self, a, b):
        """计算两个字符串的相似度"""
        return SequenceMatcher(None, a, b).ratio()

    def normalize_string(self, s):
        """标准化字符串，移除特殊字符和空格，转为小写"""
        if not isinstance(s, str):
            return ""
        # 替换特殊字符
        s = s.replace('_', ' ').replace('（', '(').replace('）', ')').replace('&', 'and')
        s = s.replace('-', ' ').replace('—', ' ').replace('－', ' ').replace('·', ' ')
        s = s.replace('：', ' ').replace(':', ' ').replace('，', ' ').replace(',', ' ')
        # 移除其他特殊字符
        s = re.sub(r'[^\w\s()]', '', s)
        # 转为小写并移除多余空格
        return ' '.join(s.lower().split())
    
    def load_submitter_info(self):
        """从Excel文件中加载提交人信息"""
        try:
            print(f"从Excel文件 '{self.excel_file}' 中加载提交人信息...")
            df = pd.read_excel(self.excel_file)
            
            # 确保必要的列存在
            if '1.创意名称' not in df.columns or '发起人姓名' not in df.columns:
                print("错误: Excel文件缺少必要的列 '1.创意名称' 或 '发起人姓名'")
                return
            
            # 初始化计数器
            project_count = 0
            
            # 遍历Excel行，建立项目名称到提交人的映射
            for index, row in df.iterrows():
                project_name = row['1.创意名称']
                submitter = row['发起人姓名']
                
                # 确保值不为空
                if pd.notna(project_name) and pd.notna(submitter):
                    # 清理提交人和项目名称
                    submitter = submitter.strip()
                    
                    # 清理原始项目名称
                    clean_project_name = project_name.strip()
                    self.project_to_submitter[clean_project_name] = submitter
                    project_count += 1
                    
                    # 创建标准化的项目名称映射 - 移除特殊字符和空格
                    normalized_name = self.normalize_string(clean_project_name)
                    self.normalized_projects[normalized_name] = clean_project_name
                    
                    # 创建项目名称的多种变体，增加匹配成功率
                    # 1. 移除括号内容
                    no_brackets = re.sub(r'[\(（].*?[\)）]', '', clean_project_name).strip()
                    if no_brackets != clean_project_name:
                        self.project_to_submitter[no_brackets] = submitter
                        
                    # 2. 只保留主要名称 (通常是第一个短语)
                    main_name = clean_project_name.split('—')[0].split('-')[0].split('_')[0].strip()
                    if main_name != clean_project_name and len(main_name) > 2:  # 确保不是空字符串
                        self.project_to_submitter[main_name] = submitter
                    
                    # 3. 处理中英文混合项目名
                    # 提取中文部分
                    chinese_only = ''.join(re.findall(r'[\u4e00-\u9fff]', clean_project_name))
                    if chinese_only and len(chinese_only) > 1:
                        self.project_to_submitter[chinese_only] = submitter
                        
                    # 4. 提取英文部分
                    english_only = ' '.join(re.findall(r'[a-zA-Z]+', clean_project_name))
                    if english_only and len(english_only) > 2:  # 确保不是单个字母
                        self.project_to_submitter[english_only] = submitter
            
            print(f"成功从Excel文件中提取了{project_count}个项目基础映射，扩展为{len(self.project_to_submitter)}个项目名称变体到提交人的映射")
            
            # 打印部分映射示例（最多显示5个）
            sample_mappings = list(self.project_to_submitter.items())[:5]
            if sample_mappings:
                print("映射示例:")
                for project, submitter in sample_mappings:
                    print(f"  - '{project}' => '{submitter}'")
                    
        except Exception as e:
            print(f"加载Excel文件时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def get_submitter_name(self, project_name_from_file):
        """根据文件名中的项目名称获取提交人姓名，使用多种匹配策略"""
        if not self.project_to_submitter:
            # 如果没有加载提交人信息，则返回从文件名中提取的项目名称
            return project_name_from_file
        
        print(f"寻找项目 '{project_name_from_file}' 的提交人...")
        submitter_name = None
        match_reason = None
        
        # 清理和预处理文件名中的项目名
        clean_project_name = project_name_from_file.strip()
        
        # 1. 首先检查特殊映射
        if clean_project_name in self.special_mappings:
            mapped_name = self.special_mappings[clean_project_name]
            if mapped_name in self.project_to_submitter:
                submitter_name = self.project_to_submitter[mapped_name]
                match_reason = f"特殊映射: '{clean_project_name}' -> '{mapped_name}'"
        
        # 2. 尝试直接匹配
        if not submitter_name and clean_project_name in self.project_to_submitter:
            submitter_name = self.project_to_submitter[clean_project_name]
            match_reason = f"直接匹配: '{clean_project_name}'"
        
        # 3. 尝试多种变体匹配
        if not submitter_name:
            # 3.1 去除括号内容
            no_brackets = re.sub(r'[\(（].*?[\)）]', '', clean_project_name).strip()
            if not submitter_name and no_brackets in self.project_to_submitter:
                submitter_name = self.project_to_submitter[no_brackets]
                match_reason = f"去括号匹配: '{clean_project_name}' -> '{no_brackets}'"
                
            # 3.2 主要名称匹配
            main_name = clean_project_name.split('—')[0].split('-')[0].split('_')[0].strip()
            if not submitter_name and main_name != clean_project_name and main_name in self.project_to_submitter:
                submitter_name = self.project_to_submitter[main_name]
                match_reason = f"主要名称匹配: '{clean_project_name}' -> '{main_name}'"
                
            # 3.3 中文部分匹配
            chinese_only = ''.join(re.findall(r'[\u4e00-\u9fff]', clean_project_name))
            if not submitter_name and chinese_only and chinese_only in self.project_to_submitter:
                submitter_name = self.project_to_submitter[chinese_only]
                match_reason = f"中文部分匹配: '{clean_project_name}' -> '{chinese_only}'"
                
            # 3.4 英文部分匹配
            english_only = ' '.join(re.findall(r'[a-zA-Z]+', clean_project_name))
            if not submitter_name and english_only and english_only in self.project_to_submitter:
                submitter_name = self.project_to_submitter[english_only]
                match_reason = f"英文部分匹配: '{clean_project_name}' -> '{english_only}'"
        
        # 4. 尝试部分包含匹配
        if not submitter_name:
            # 4.1 子串匹配 - 项目名包含在表格项目中
            matching_projects = [
                (name, self.project_to_submitter[name]) 
                for name in self.project_to_submitter
                if (clean_project_name in name and len(clean_project_name) > 3) or
                   (name in clean_project_name and len(name) > 3)
            ]
            
            if matching_projects:
                # 选择最长的匹配（更具体的名称）
                longest_match = max(matching_projects, key=lambda x: len(x[0]))
                submitter_name = longest_match[1]
                match_reason = f"包含匹配: '{clean_project_name}' 与 '{longest_match[0]}'"
        
        # 5. 如果仍未找到，尝试基于相似度的匹配
        if not submitter_name:
            normalized_file_name = self.normalize_string(clean_project_name)
            
            # 先找出潜在的相似项目
            potential_matches = []
            
            # 5.1 标准化名称相似度匹配
            for norm_name, orig_name in self.normalized_projects.items():
                score = self.similar(normalized_file_name, norm_name)
                if score > 0.5:  # 降低阈值，扩大匹配范围
                    potential_matches.append((orig_name, score, "标准化相似度匹配"))
            
            # 5.2 分词相似度 - 比较关键词重叠程度
            for proj_name in self.project_to_submitter:
                # 提取词组（中文按字符，英文按单词）
                file_words = set(re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+', clean_project_name))
                proj_words = set(re.findall(r'[\u4e00-\u9fff]|[a-zA-Z]+', proj_name))
                
                # 如果有共同词，计算Jaccard相似系数
                if file_words and proj_words:
                    common_words = file_words & proj_words
                    if common_words:
                        jaccard = len(common_words) / len(file_words | proj_words)
                        if jaccard > 0.3:  # 至少30%的词重叠
                            potential_matches.append((proj_name, jaccard, "关键词匹配"))
            
            # 选择最佳匹配
            if potential_matches:
                best_match = max(potential_matches, key=lambda x: x[1])
                submitter_name = self.project_to_submitter[best_match[0]]
                match_reason = f"{best_match[2]}: '{clean_project_name}' 与 '{best_match[0]}' 相似度为 {best_match[1]:.2f}"
        
        # 输出匹配结果
        if submitter_name:
            print(f"  √ 找到{match_reason}")
            print(f"  提交人: {submitter_name}")
        else:
            print(f"  ! 警告: 无法为项目 '{clean_project_name}' 找到匹配的提交人")
            # 如果找不到匹配的提交人，则使用文件名中的项目名称
            return clean_project_name
        
        return submitter_name

    def get_deepseek_evaluation(self, content):
        """使用Deepseek进行评审"""
        url = f"{self.deepseek_api_base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}"
        }
        
        # 将提示词拆分为多个部分
        prompt_base = """作为AI项目评估专家，请对以下项目进行严格、公正、有理有据的评估。请严格按照指定的JSON格式输出评估结果。

待评估项目内容：
"""

        prompt_content = content

        prompt_requirements = """
评分要求：
1. 每个维度根据得分点和扣分点的整体情况，直接给出0-100的评分
2. 每个得分点和扣分点必须提供至少2-3条具体的、可验证的依据
3. 评分要客观公正，有理有据，避免主观臆测
4. 改进建议要具体可行，有明确的实施方向和预期效果
5. 评价时必须结合项目具体内容，不要泛泛而谈
6. 对于创新点，必须说明与现有产品的具体区别
7. 对于技术可行性，必须指出具体的技术路径和潜在挑战
8. 对于市场潜力，必须有具体的市场数据或趋势支撑
9. 评审内容应当专业、深入、有洞见，使用行业术语和数据支撑观点
10. 每个维度的评价应当有深度，不仅指出现象，还要分析原因和影响

评分维度和标准：

1. 创新性(20%)：评估项目的创新程度和独特价值
   得分点参考：
   - 技术驱动的创新：必须说明项目如何利用技术创造新价值
   - 用户体验创新：必须说明项目如何改变用户交互方式或体验
   - 商业模式创新：必须说明项目如何创新性地解决商业问题
   - 与竞品差异：必须详细对比与市场现有产品的具体差异点
   扣分点参考：
   - 创新局限性：必须指出创新的边界和局限
   - 技术依赖：必须分析对第三方技术的依赖程度及风险
   - 模仿风险：必须评估创新被模仿的难度和防御措施

2. 实用性(30%)：评估项目解决实际问题的能力
   得分点参考：
   - 痛点精准定位：必须说明项目如何精确识别并解决用户痛点
   - 场景适用性：必须列举具体的应用场景和使用案例
   - 用户价值：必须量化分析项目为用户创造的具体价值
   - 易用性设计：必须说明如何降低用户使用门槛
   扣分点参考：
   - 使用门槛：必须指出可能阻碍用户采用的技术或认知障碍
   - 场景局限：必须说明项目在哪些场景下效果有限
   - 价值兑现挑战：必须分析用户获取价值的难度和周期

3. 技术可行性(25%)：评估项目的技术实现难度
   得分点参考：
   - 技术方案合理性：必须评估所选技术栈的适用性和成熟度
   - 架构设计：必须分析系统架构的可扩展性和稳定性
   - 资源需求合理性：必须提供具体的技术资源评估
   - 技术风险管控：必须说明如何应对技术实现中的潜在风险
   扣分点参考：
   - 技术复杂度：必须指出实现过程中的技术难点和挑战
   - 技术依赖风险：必须评估对第三方技术或平台的依赖风险
   - 性能瓶颈：必须分析可能的性能瓶颈及其影响
   - 安全与合规风险：必须评估数据安全和法规合规方面的挑战

4. 市场潜力(15%)：评估项目的商业价值
   得分点参考：
   - 市场规模与增长性：必须提供具体的市场数据和增长预测
   - 目标用户精准度：必须分析目标用户特征与产品匹配度
   - 竞争优势：必须详细说明与竞品相比的差异化优势
   - 商业模式可行性：必须评估收入模式的可持续性和盈利能力
   扣分点参考：
   - 市场竞争格局：必须分析现有竞争对手的实力和市场份额
   - 获客挑战：必须评估用户获取的难度和成本
   - 商业化障碍：必须指出从产品到盈利的转化障碍
   - 市场教育成本：必须分析用户认知培养的难度和成本

5. 人文精神(10%)：评估项目的人文价值
   得分点参考：
   - 用户洞察深度：必须说明项目如何深入理解并满足用户深层次需求
   - 情感连接：必须分析项目如何与用户建立情感共鸣和连接
   - 社会价值：必须评估项目对社会发展和人文进步的积极影响
   - 用户成长：必须说明项目如何促进用户能力提升和个人发展
   扣分点参考：
   - 表面需求：必须指出项目仅停留在满足用户表面需求的层面
   - 技术与人文失衡：必须分析技术与人文关怀之间的平衡问题
   - 潜在负面影响：必须评估项目可能带来的社会或心理负面效应
   - 价值观导向：必须分析项目隐含的价值观导向是否积极健康

请输出以下格式的JSON（注意：不要包含任何其他文字，只输出JSON）：
{
    "dimensions": {
        "创新性": {
            "score": 85,
            "scoring_points": [
                {
                    "point": "技术驱动的创新",
                    "evidence": [
                        "项目首创性地将情感计算应用于职场社交场景，填补了市场空白",
                        "创新性地引入'情绪地图'功能，可视化展示用户情绪变化轨迹",
                        "独特的'情绪预警'机制，提前30分钟预测可能的情绪波动"
                    ]
                }
            ],
            "deduction_points": [
                {
                    "point": "创新局限性",
                    "evidence": [
                        "核心的情绪识别算法与竞品'心情助手'使用相同的开源模型",
                        "用户界面设计与主流APP相似，缺乏明显特色",
                        "数据分析方法较为传统，未充分利用最新的机器学习技术"
                    ]
                }
            ],
            "suggestions": [
                "建议引入个性化的情绪干预模型，根据用户历史数据定制干预策略",
                "可以考虑集成最新的多模态情感分析技术，提升识别准确度",
                "建议开发独特的情绪可视化界面，提升产品识别度"
            ]
        }
    },
    "total_score": 81.0
}"""

        # 组合完整的提示词
        prompt = prompt_base + prompt_content + prompt_requirements

        # 使用环境变量中的重试次数
        max_retries = self.max_retries
        retry_count = 0
        
        # 添加请求限速
        min_request_interval = 1.0  # 最小请求间隔（秒）
        last_request_time = 0
        
        while retry_count < max_retries:
            try:
                # 实现请求限速
                current_time = time.time()
                time_since_last_request = current_time - last_request_time
                if time_since_last_request < min_request_interval:
                    time.sleep(min_request_interval - time_since_last_request)
                
                print(f"  - API调用尝试 {retry_count + 1}/{max_retries}...")
                
                # 更新最后请求时间
                last_request_time = time.time()
                
                response = requests.post(url, headers=headers, json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system", 
                            "content": "你是一个专业的AI项目评审专家。请严格按照JSON格式输出评估结果，确保评分客观公正，依据充分具体。"
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,  # 降低温度以获得更稳定的输出
                    "max_tokens": 4000,
                    "response_format": {"type": "json_object"},
                    "stream": False,  # 禁用流式输出以提高效率
                    "timeout": 30  # 设置超时时间
                })
                
                response.raise_for_status()
                result = response.json()
                
                if 'choices' not in result or not result['choices']:
                    raise ValueError("API响应缺少choices字段")
                
                evaluation = result["choices"][0]["message"]["content"]
                
                # 清理可能的非JSON内容
                evaluation = re.sub(r'^[^{]*({.*})[^}]*$', r'\1', evaluation.strip())
                
                # 在JSON验证部分添加更严格的得分验证
                try:
                    eval_json = json.loads(evaluation)
                    
                    # 验证JSON结构
                    if "dimensions" not in eval_json:
                        raise ValueError("评估结果缺少dimensions字段")
                    if "total_score" not in eval_json:
                        raise ValueError("评估结果缺少total_score字段")
                        
                    required_dimensions = ["创新性", "实用性", "技术可行性", "市场潜力", "人文精神"]
                    for dim in required_dimensions:
                        if dim not in eval_json["dimensions"]:
                            raise ValueError(f"评估结果缺少{dim}维度")
                        dim_data = eval_json["dimensions"][dim]
                        
                        # 验证必要字段
                        required_fields = ["score", "scoring_points", "deduction_points", "suggestions"]
                        for field in required_fields:
                            if field not in dim_data:
                                raise ValueError(f"{dim}维度缺少{field}字段")
                        
                        # 验证得分点和扣分点的结构
                        for point in dim_data["scoring_points"]:
                            if not isinstance(point.get("evidence", []), list):
                                point["evidence"] = [point.get("evidence", "")]
                        
                        for point in dim_data["deduction_points"]:
                            if not isinstance(point.get("evidence", []), list):
                                point["evidence"] = [point.get("evidence", "")]
                        
                        # 确保维度得分在0-100之间
                        if not isinstance(dim_data["score"], (int, float)):
                            raise ValueError(f"{dim}维度的得分必须是数字")
                        dim_data["score"] = max(0, min(100, float(dim_data["score"])))
                        
                        # 验证总分计算
                        calculated_total = sum(
                            eval_json["dimensions"][dim]["score"] * self.weights[dim]
                            for dim in required_dimensions
                        )
                        # 四舍五入到小数点后2位
                        calculated_total = round(calculated_total, 2)
                        if calculated_total != eval_json["total_score"]:
                            print(f"  ! 警告：总分计算有误")
                            print(f"    - 声明总分: {eval_json['total_score']}")
                            print(f"    - 计算总分: {calculated_total}")
                            eval_json["total_score"] = calculated_total
                            print(f"    √ 修正后总分: {calculated_total}")
                        
                        print("  √ API调用成功，评估结果格式正确")
                        return eval_json
                        
                except json.JSONDecodeError as e:
                    print(f"  ! JSON解析错误: {str(e)}")
                    print(f"  ! 原始响应内容: {evaluation}")
                    raise ValueError("评估结果不是有效的JSON格式")
                
            except requests.exceptions.RequestException as e:
                print(f"  ! API请求异常: {str(e)}")
            except ValueError as e:
                print(f"  ! 评估结果验证失败: {str(e)}")
            except Exception as e:
                print(f"  ! 未预期的错误: {str(e)}")
            
            retry_count += 1
            if retry_count < max_retries:
                # 使用指数退避策略，但设置最大延迟时间
                delay = min(self.retry_delay * (2 ** retry_count) + random.uniform(0, 1), 60)
                print(f"  - 等待 {delay:.1f} 秒后重试...")
                time.sleep(delay)
            else:
                print("  × 达到最大重试次数，评估失败")
                raise Exception("无法获取有效的AI评估结果")

    def get_claude_review(self, content):
        """使用Claude进行锐评"""
        url = f"{self.claude_api_base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.claude_api_key}"
        }
        
        prompt = f"""请作为一个尖锐的AI项目评审专家，对以下项目进行简短但一针见血的锐评。

要求：
1. 必须且只能输出一句话（以句号、感叹号或问号结尾）
2. 语气必须尖锐、幽默，可使用反讽和比喻
3. 准确抓住项目最关键的问题或特点进行评价
4. 控制在50个字以内
5. 评论必须让人印象深刻、一针见血
6. 不要客套话，直接切入要害
7. 特别关注项目的"人文精神"，即项目是否用心洞见和满足用户深层次需求，是否有文化价值和社会影响

评论风格指南：
- 使用反问、夸张或反讽的修辞手法
- 善用比喻将项目与某些荒谬事物进行对比
- 指出产品可能存在的明显缺陷或市场难点
- 揭示项目宣传中可能隐藏的自相矛盾之处
- 用幽默的方式点出项目背后的真实商业逻辑
- 评价项目是否真正关注人文价值和社会影响

示例锐评：
1. "又一个想靠'轻量化'包装的健康类应用，看起来很懂你，实则只懂如何让你的钱包轻量化！"
2. "AI当保姆，还自称'轻量化'？这不就是把用户当婴儿，还美其名曰'高效健康管理'吗？"
3. "用AI来哄人睡觉，这是嫌现在的失眠人群睡得还不够难吗？"
4. "打着关怀老人旗号，却只是用冰冷算法代替真情实感，这种'人文关怀'令人窒息！"

待评项目：
{content}

请直接输出锐评内容，不要有任何其他文字。"""

        # 使用环境变量中的重试次数
        max_retries = self.max_retries
        retry_count = 0
        
        # 添加请求限速
        min_request_interval = 1.0  # 最小请求间隔（秒）
        last_request_time = 0
        
        while retry_count < max_retries:
            try:
                # 实现请求限速
                current_time = time.time()
                time_since_last_request = current_time - last_request_time
                if time_since_last_request < min_request_interval:
                    time.sleep(min_request_interval - time_since_last_request)
                
                print(f"  - Claude API调用尝试 {retry_count + 1}/{max_retries}...")
                
                # 更新最后请求时间
                last_request_time = time.time()
        
                data = {
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个资深的AI项目评审专家，善于用生动、有个性的语言评价项目。你的评论既有专业深度，又有人文温度。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "model": "claude-3-5-sonnet-20240620",
                    "temperature": 0.7,  # 稍微降低温度以提高稳定性
                    "max_tokens": 250,   # 增加token数量，允许更长的输出
                    "stream": False,     # 禁用流式输出以提高效率
                    "timeout": 30        # 设置超时时间
                }
                
                response = requests.post(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                if 'choices' not in result or not result['choices']:
                    raise ValueError("API响应缺少choices字段")
                
                review = result["choices"][0]["message"]["content"]
                
                # 清理和验证响应
                review = review.strip().strip('"').strip()
                
                # 验证响应是否符合要求
                if len(review) > 300:  # 允许更长的锐评（约250-300字）
                    review = review[:300] + "..."
                
                print("  √ Claude锐评生成成功")
                return review
                
            except requests.exceptions.RequestException as e:
                print(f"  ! Claude API请求异常: {str(e)}")
            except ValueError as e:
                print(f"  ! Claude API响应验证失败: {str(e)}")
            except Exception as e:
                print(f"  ! Claude API未预期的错误: {str(e)}")
            
            retry_count += 1
            if retry_count < max_retries:
                # 使用指数退避策略，但设置最大延迟时间
                delay = min(self.retry_delay * (2 ** retry_count) + random.uniform(0, 1), 60)
                print(f"  - 等待 {delay:.1f} 秒后重试...")
                time.sleep(delay)
            else:
                print("  × Claude API达到最大重试次数，评估失败")
                return "锐评生成失败，请检查API服务状态。"

    def calculate_total_score(self, scores):
        """计算总分"""
        total = 0
        for dimension, score in scores.items():
            total += score * self.weights[dimension]
        return round(total, 2)
        
    def evaluate_all_submissions(self):
        """评估所有提交的作品"""
        # 确保输出目录存在
        os.makedirs(self.results_dir, exist_ok=True)
        
        # 确保项目数据目录存在
        os.makedirs(self.project_data_dir, exist_ok=True)
        
        # 获取所有提交文件
        submissions = []
        for file in os.listdir(self.submissions_dir):
            if file.endswith('.md'):
                submissions.append(os.path.join(self.submissions_dir, file))
        
        if not submissions:
            print("没有找到任何提交作品")
            return []
        
        # 按编号排序
        submissions.sort(key=lambda x: int(os.path.basename(x).split('_')[0]))
        
        # 评估结果列表
        all_results = []
        
        # 统计信息
        total_submissions = len(submissions)
        skipped_count = 0
        
        print(f"\n开始评估 {total_submissions} 个提交作品...")
        
        # 遍历所有提交
        for i, submission in enumerate(submissions, 1):
            file_name = os.path.basename(submission)
            submission_number = int(file_name.split('_')[0])
            
            print(f"\n[{i}/{total_submissions}] 评估: {file_name}")
            
            # 构建输出文件路径
            review_file = os.path.join(self.results_dir, f"{file_name.replace('.md', '')}_评审.md")
            json_file = os.path.join(self.project_data_dir, f"{file_name.replace('.md', '')}.json")
            
            # 检查是否已经评估过
            if os.path.exists(review_file) and os.path.exists(json_file):
                print(f"  - 已存在评审结果，跳过")
                
                # 读取已有的评审结果
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                        
                    all_results.append({
                        'file_name': file_name,
                        'submission_number': submission_number,
                        'submitter_name': json_data['review_content']['basic_info']['submitter'],
                        'total_score': json_data['total_score'],
                        'scores': json_data['scores'],
                        'review_file': review_file,
                        'json_file': json_file
                    })
                    
                    skipped_count += 1
                    continue
                except Exception as e:
                    print(f"  ! 读取已有评审结果失败: {str(e)}")
                    print("  - 将重新评估")
            
            # 读取提交内容
            try:
                with open(submission, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f"  ! 读取提交内容失败: {str(e)}")
                continue
            
            # 获取提交人信息
            submitter_name = self.get_submitter_name(file_name)
            
            # 使用DeepSeek进行评估
            print(f"  - 使用DeepSeek进行评估...")
            try:
                deepseek_eval = self.get_deepseek_evaluation(content)
            except Exception as e:
                print(f"  ! DeepSeek评估失败: {str(e)}")
                
                # 创建错误结果
                error_result = {
                    'file_name': file_name,
                    'submission_number': submission_number,
                    'submitter_name': submitter_name,
                    'total_score': 0,
                    'review_file': review_file,
                    'json_file': json_file
                }
                
                # 生成错误报告
                error_report = f"""# {file_name} - 评估失败

## 错误信息

评估过程中发生错误: {str(e)}

请联系管理员手动评估此提交。
"""
                
                # 保存错误报告
                with open(error_result['review_file'], 'w', encoding='utf-8') as f:
                    f.write(error_report)
                
                all_results.append(error_result)
                continue
            
            # 使用Claude进行锐评
            print(f"  - 使用Claude进行锐评...")
            try:
                claude_review = self.get_claude_review(content)
            except Exception as e:
                print(f"  ! Claude锐评失败: {str(e)}")
                claude_review = "锐评生成失败，请联系管理员。"
            
            # 生成评审报告
            print(f"  - 生成评审报告...")
            report = self.generate_evaluation_report(submission, deepseek_eval, claude_review, submitter_name)
            
            # 生成JSON数据
            print(f"  - 生成JSON数据...")
            json_data = self.generate_json_data(submission, deepseek_eval, claude_review, submitter_name)
            
            # 保存评审报告
            with open(review_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            # 保存JSON数据
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            # 提取各维度得分
            scores = {}
            for dimension in deepseek_eval['dimensions']:
                scores[dimension] = deepseek_eval['dimensions'][dimension]['score']
            
            # 添加到结果列表
            all_results.append({
                'file_name': file_name,
                'submission_number': submission_number,
                'submitter_name': submitter_name,
                'total_score': deepseek_eval['total_score'],
                'scores': scores,
                'evaluations': deepseek_eval['dimensions'],
                'review_file': review_file,
                'json_file': json_file
            })
            
            print(f"  √ 评审完成! 总分: {deepseek_eval['total_score']:.2f}")
        
        print(f"\n所有作品评估完成! (跳过: {skipped_count}, 处理: {total_submissions - skipped_count})")
        
        # 生成评审总结
        print("\n正在生成评审总结...")
        summary_file = os.path.join(self.results_dir, "评审总结.md")
        
        # 定义排序函数
        def get_sort_key(result):
            # 1. 总分
            total_score = -result['total_score']  # 负号使其降序排列
            
            # 2. 按权重从高到低的维度得分
            dimension_scores = []
            if result.get('scores'):
                # 按权重从高到低排序的维度
                weighted_dimensions = [
                    ('实用性', 0.30),
                    ('技术可行性', 0.25),
                    ('创新性', 0.20),
                    ('市场潜力', 0.15),
                    ('人文精神', 0.10)
                ]
                for dim, weight in weighted_dimensions:
                    score = result['scores'].get(dim, 0)
                    dimension_scores.append(-score)  # 负号使其降序排列
            else:
                dimension_scores = [0] * 5
            
            # 3. 得分点数量
            scoring_points_count = 0
            if result.get('evaluations'):
                for dim_data in result['evaluations'].values():
                    scoring_points_count += len(dim_data.get('scoring_points', []))
            scoring_points_count = -scoring_points_count  # 负号使其降序排列
            
            # 4. 提交编号
            submission_number = result['submission_number']
            
            return (total_score, *dimension_scores, scoring_points_count, submission_number)
        
        # 按多级排序规则排序
        sorted_results = sorted(all_results, key=get_sort_key)
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("# AI创意大赛评审总结\n\n")
            f.write(f"## 评审时间\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## 参赛项目数量\n共评审 {len(all_results)} 个项目（跳过: {skipped_count}, 新评审: {total_submissions - skipped_count}）\n\n")
            
            # 添加排序规则说明
            f.write("## 排名规则\n\n")
            f.write("同分情况下的排序依据（优先级从高到低）：\n")
            f.write("1. 总评分\n")
            f.write("2. 分维度得分（按权重从高到低）：\n")
            f.write("   - 实用性（30%）\n")
            f.write("   - 技术可行性（25%）\n")
            f.write("   - 创新性（20%）\n")
            f.write("   - 市场潜力（15%）\n")
            f.write("   - 人文精神（10%）\n")
            f.write("3. 得分点数量（反映评分依据的充分性）\n")
            f.write("4. 提交编号（较早提交优先）\n\n")
            
            # 添加统计信息
            valid_scores = [r['total_score'] for r in all_results if r['total_score'] > 0]
            if valid_scores:
                avg_score = sum(valid_scores) / len(valid_scores)
                max_score = max(valid_scores)
                min_score = min(valid_scores)
                f.write(f"## 评分统计\n")
                f.write(f"- 平均分：{avg_score:.2f}\n")
                f.write(f"- 最高分：{max_score:.2f}\n")
                f.write(f"- 最低分：{min_score:.2f}\n\n")
            
            # 各维度平均分
            f.write("## 维度评分统计\n")
            for dimension in self.weights.keys():
                valid_dim_scores = [r['scores'][dimension] for r in all_results if r.get('scores', {}).get(dimension, 0) > 0]
                if valid_dim_scores:
                    avg_dim_score = sum(valid_dim_scores) / len(valid_dim_scores)
                    f.write(f"- {dimension}（权重：{self.weights[dimension]*100}%）：{avg_dim_score:.2f}\n")
            f.write("\n")
            
            # 评分排名
            f.write("## 评分排名\n\n")
            current_rank = 1
            current_score = None
            same_rank_count = 0
            
            for i, result in enumerate(sorted_results, 1):
                if result['total_score'] > 0:
                    # 处理同分显示
                    if result['total_score'] != current_score:
                        current_score = result['total_score']
                        current_rank = i - same_rank_count
                        same_rank_count = 0
                    else:
                        same_rank_count += 1
                    
                    # 获取各维度得分
                    scores_str = ""
                    if result.get('scores'):
                        scores_str = " ["
                        for dim in ['实用性', '技术可行性', '创新性', '市场潜力', '人文精神']:
                            scores_str += f"{dim[0]}{result['scores'].get(dim, 0):.1f} "
                        scores_str = scores_str.strip() + "]"
                    
                    f.write(f"{current_rank}. {result['file_name']} (提交人：{result['submitter_name']}) - 得分：{result['total_score']:.2f}{scores_str}\n")
                else:
                    f.write(f"--. {result['file_name']} (提交人：{result['submitter_name']}) - 评估失败\n")
        
        print(f"√ 评审总结已保存到：{summary_file}")
        return all_results

    def generate_evaluation_report(self, submission_content, deepseek_eval, claude_review, submitter_name):
        """生成评审报告内容"""
        # 从文件名中提取项目名称（去掉编号和扩展名）
        file_name = os.path.basename(submission_content)
        project_name = '_'.join(file_name.split('_')[1:]).replace('.md', '')
        
        # 生成报告
        report = f"""# {project_name}

## 基本信息

| 项目 | 内容 |
|------|------|
| 提交人 | {submitter_name} |
| 评审时间 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
| 总评分 | {deepseek_eval['total_score']:.2f} |

## 锐评

{claude_review}

## 详细评分

"""
        # 添加各维度的评分和详细内容
        weights = {
            "创新性": "20.0%",
            "实用性": "30.0%",
            "技术可行性": "25.0%",
            "市场潜力": "15.0%",
            "人文精神": "10.0%"
        }
        
        for dimension, weight in weights.items():
            dim_data = deepseek_eval['dimensions'][dimension]
            report += f"""### {dimension} (权重: {weight})

**得分**: {dim_data['score']:.2f}

#### ✓ 亮点

"""
            # 添加得分点（不显示分值）
            for point in dim_data['scoring_points']:
                report += f"* **{point['point']}**\n"
                if isinstance(point['evidence'], list):
                    for evidence in point['evidence']:
                        report += f"  * {evidence}\n"
                else:
                    report += f"  * {point['evidence']}\n"
            
            report += "\n#### ✗ 不足\n\n"
            # 添加扣分点（不显示分值）
            for point in dim_data['deduction_points']:
                report += f"* **{point['point']}**\n"
                if isinstance(point['evidence'], list):
                    for evidence in point['evidence']:
                        report += f"  * {evidence}\n"
                else:
                    report += f"  * {point['evidence']}\n"
            
            report += "\n#### ⚡ 改进建议\n\n"
            # 添加改进建议
            for suggestion in dim_data['suggestions']:
                report += f"* {suggestion}\n"
            
            report += "\n---\n\n"
        
        return report
        
    def generate_json_data(self, submission_content, deepseek_eval, claude_review, submitter_name):
        """生成JSON格式的评审数据"""
        # 从文件名中提取项目ID和名称
        file_name = os.path.basename(submission_content)
        submission_id = file_name.split('_')[0]
        project_name = file_name.replace('.md', '')
        
        # 读取提交内容
        with open(submission_content, 'r', encoding='utf-8') as f:
            proposal_content = f.read()
        
        # 构建JSON数据结构
        json_data = {
            "id": submission_id,
            "name": project_name,
            "total_score": round(deepseek_eval['total_score'], 2),
            "scores": {
                "创新性": round(deepseek_eval['dimensions']['创新性']['score'], 2),
                "实用性": round(deepseek_eval['dimensions']['实用性']['score'], 2),
                "技术可行性": round(deepseek_eval['dimensions']['技术可行性']['score'], 2),
                "市场潜力": round(deepseek_eval['dimensions']['市场潜力']['score'], 2),
                "人文精神": round(deepseek_eval['dimensions']['人文精神']['score'], 2)
            },
            "proposal_content": proposal_content,
            "review_content": {
                "basic_info": {
                    "submitter": submitter_name,
                    "review_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "total_score": round(deepseek_eval['total_score'], 2)
                },
                "brief_review": claude_review,
                "detailed_scores": []
            }
        }
        
        # 添加详细评分
        for dimension, weight_str in {
            "创新性": "20.0%",
            "实用性": "30.0%",
            "技术可行性": "25.0%",
            "市场潜力": "15.0%",
            "人文精神": "10.0%"
        }.items():
            dim_data = deepseek_eval['dimensions'][dimension]
            
            # 构建维度评分数据
            dimension_data = {
                "category": dimension,
                "weight": weight_str,
                "score": round(dim_data['score'], 2),
                "highlights": [],
                "weaknesses": [],
                "suggestions": dim_data['suggestions']
            }
            
            # 添加亮点
            for point in dim_data['scoring_points']:
                highlight = {
                    "aspect": point['point'],
                    "points": point['evidence'] if isinstance(point['evidence'], list) else [point['evidence']]
                }
                dimension_data["highlights"].append(highlight)
            
            # 添加不足
            for point in dim_data['deduction_points']:
                weakness = {
                    "aspect": point['point'],
                    "points": point['evidence'] if isinstance(point['evidence'], list) else [point['evidence']]
                }
                dimension_data["weaknesses"].append(weakness)
            
            # 添加到详细评分列表
            json_data["review_content"]["detailed_scores"].append(dimension_data)
        
        return json_data

    def process_submissions(self, submissions_dir, output_dir):
        """处理所有提交的作品"""
        try:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 确保项目数据目录存在
            os.makedirs(self.project_data_dir, exist_ok=True)
            
            # 获取所有评审结果
            results = self.evaluate_all_submissions()
            
            if not results:
                print("没有找到任何评审结果")
                return
            
            print("\n评审完成！正在生成总结...")
            
            # 按总分排序
            sorted_results = sorted(results, key=lambda x: x['total_score'], reverse=True)
            
            # 生成总结报告
            summary_file = os.path.join(output_dir, "评审总结.md")
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write("# AI创意大赛评审总结\n\n")
                f.write(f"## 评审时间\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"## 参赛项目数量\n共评审 {len(results)} 个项目\n\n")
                f.write("## 评分排名\n\n")
                
                for i, result in enumerate(sorted_results, 1):
                    f.write(f"{i}. {result['file_name']} - 得分：{result['total_score']:.2f}\n")
            
            print(f"评审总结已保存到：{summary_file}")
            
        except Exception as e:
            print(f"处理提交作品时出错: {str(e)}")
            import traceback
            traceback.print_exc()

def main():
    try:
        # 创建评审器实例
        evaluator = AIEvaluator()
        
        # 设置输入输出目录
        submissions_dir = "参赛作品"
        output_dir = "评审结果"
        
        # 处理所有提交
        evaluator.process_submissions(submissions_dir, output_dir)
        
    except Exception as e:
        print(f"错误: {str(e)}")
        print("请确保.env文件存在且包含必要的API密钥配置")

if __name__ == "__main__":
    main()