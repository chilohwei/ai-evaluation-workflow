#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
项目分类脚本
这个脚本负责根据评审结果文件，对所有参赛项目进行分类
"""

import os
import re
import json
import requests
import time
import random
import concurrent.futures
import threading
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class ProjectCategorizer:
    def __init__(self, review_dir="评审结果", output_dir="项目分类", project_data_dir="项目数据"):
        """
        初始化项目分类器
        
        参数:
            review_dir: 评审结果目录
            output_dir: 分类结果输出目录
            project_data_dir: 项目数据目录
        """
        # 设置目录
        self.review_dir = review_dir
        self.output_dir = output_dir
        self.project_data_dir = project_data_dir
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 定义遵循MECE原则的分类结构
        self.categories = {
            "图像类": [],      # 图像生成、处理、识别、视觉相关项目
            "音视频类": [],    # 音频、视频处理、生成、分析相关项目
            "文档类": [],      # 文档处理、分析、管理、知识库相关项目
            "思想类": [],      # 思维辅助、决策支持、创意生成相关的项目
            "生活类": [],      # 日常生活、健康、饮食、穿着相关项目
            "工作类": [],      # 职场、办公、生产力工具相关项目
            "教育类": [],      # 学习、教育、培训相关项目
            "社交类": []       # 社交、情感、交流相关项目
        }
        
        # Deepseek API配置
        self.deepseek_api_url = os.getenv("DEEPSEEK_API_BASE_URL")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        
        # 重试设置
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.retry_delay = int(os.getenv("RETRY_DELAY", "2"))
        
        # 并发设置
        self.max_workers = int(os.getenv("MAX_WORKERS", "3"))  # 默认3个并发线程
        
        # 验证API配置
        if not self.deepseek_api_url:
            raise ValueError("请在.env文件中设置DEEPSEEK_API_BASE_URL")
        if not self.deepseek_api_key:
            raise ValueError("请在.env文件中设置DEEPSEEK_API_KEY")
        
        # 线程锁，用于保护categories字典的并发访问
        self._lock = threading.Lock()
        
        print(f"项目分类器初始化完成，将处理 {review_dir} 中的评审结果，分类结果保存到 {output_dir}")
        print(f"并发线程数: {self.max_workers}")
    
    def ai_categorize(self, project_name, description):
        """
        使用Deepseek API进行智能分类
        
        参数:
            project_name: 项目名称
            description: 项目描述
            
        返回:
            项目类别
        """
        # 构建提示词
        prompt = f"""请将以下AI项目严格分类到最合适的类别中。只需返回一个类别名称，不要有任何解释。

可选类别：
1. 图像类 - 涉及图像生成、处理、识别、视觉相关的项目
2. 音视频类 - 涉及音频、视频处理、生成、分析相关的项目
3. 文档类 - 涉及文档处理、分析、管理、知识库相关的项目
4. 思想类 - 涉及思维辅助、决策支持、创意生成相关的项目
5. 生活类 - 涉及日常生活、健康、饮食、穿着相关的项目
6. 工作类 - 涉及职场、办公、生产力工具相关的项目
7. 教育类 - 涉及学习、教育、培训相关的项目
8. 社交类 - 涉及社交、情感、交流相关的项目

项目名称: {project_name}
项目描述: {description}

请注意：
1. 必须且只能从以上8个类别中选择一个
2. 如果项目跨越多个类别，请选择其最主要的核心功能所属类别
3. 只返回类别名称，不要包含任何解释或描述"""

        # 使用提供的API调用策略
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}"
        }
        
        payload = {
            "messages": [
                {
                    "content": "你是一个专业的项目分类助手。你的任务是将项目严格分类到指定的类别中，确保分类结果符合MECE原则。只返回类别名称，不要有任何解释。",
                    "role": "system"
                },
                {
                    "content": prompt,
                    "role": "user"
                }
            ],
            "model": "deepseek-chat",
            "frequency_penalty": 0,
            "max_tokens": 50,
            "presence_penalty": 0,
            "response_format": {
                "type": "text"
            },
            "stop": None,
            "stream": False,
            "stream_options": None,
            "temperature": 0.3,
            "top_p": 1,
            "tools": None,
            "tool_choice": "none",
            "logprobs": False,
            "top_logprobs": None
        }
        
        # 增强重试机制，无限重试直到成功
        max_attempts = 10  # 设置一个较大的尝试次数上限，避免无限循环
        attempt = 0
        backoff_factor = 1.5  # 指数退避因子
        initial_delay = self.retry_delay
        
        while attempt < max_attempts:
            try:
                # 添加随机抖动，避免多个请求同时发送
                jitter = random.uniform(0.5, 1.5)
                current_delay = initial_delay * (backoff_factor ** attempt) * jitter
                
                # 如果不是第一次尝试，先等待
                if attempt > 0:
                    print(f"第 {attempt+1} 次尝试分类 {project_name}，等待 {current_delay:.2f} 秒...")
                    time.sleep(current_delay)
                
                # 构建完整的API URL
                api_url = self.deepseek_api_url
                if not api_url.endswith('/'):
                    api_url += '/'
                if not api_url.endswith('chat/completions'):
                    if api_url.endswith('/'):
                        api_url += 'chat/completions'
                    else:
                        api_url += '/chat/completions'
                
                print(f"调用API: {api_url}")
                
                response = requests.post(
                    api_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    category = result["choices"][0]["message"]["content"].strip()
                    
                    # 统一类别名称格式
                    if category in self.categories:
                        return category
                    else:
                        # 如果返回的类别不在预定义类别中，尝试映射到最接近的类别
                        category_mapping = {
                            "文本类": "文档类",
                            "知识类": "教育类",
                            "决策类": "思想类",
                            "交互类": "社交类",
                            "其他类": "生活类"
                        }
                        if category in category_mapping:
                            mapped_category = category_mapping[category]
                            print(f"将分类 '{category}' 映射为 '{mapped_category}'")
                            return mapped_category
                        
                        # 如果无法映射，修改提示词，强调必须从预定义类别中选择
                        print(f"API返回了未知分类: {category}，将重试...")
                        # 更新提示词，强调必须从预定义类别中选择
                        prompt = f"""请将以下AI项目严格分类到最合适的类别中。只需返回一个类别名称，不要有任何解释。

你必须且只能从以下8个类别中选择一个，不要创建新的类别：
- 图像类
- 音视频类
- 文档类
- 思想类
- 生活类
- 工作类
- 教育类
- 社交类

项目名称: {project_name}
项目描述: {description}

请注意：
1. 必须且只能从以上8个类别中选择一个，不要创建新的类别
2. 只返回类别名称，不要包含任何解释或描述
3. 确保返回的类别名称与上面列出的完全一致"""

                        # 更新payload
                        payload["messages"][1]["content"] = prompt
                else:
                    print(f"API调用未返回有效结果: {result}")
                
            except Exception as e:
                print(f"Deepseek API调用失败 (尝试 {attempt+1}/{max_attempts}): {e}")
            
            attempt += 1
        
        # 如果达到最大尝试次数仍未成功，抛出异常
        raise Exception(f"无法为项目 {project_name} 获取分类，请稍后再试")
    
    def categorize_project(self, file_path):
        """
        对单个项目进行分类
        
        参数:
            file_path: 评审结果文件路径
            
        返回:
            (项目名称, 类别)的元组
        """
        try:
            # 从文件中提取项目信息
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取项目名称
            project_match = re.search(r'# (.+?) - 评审结果', content)
            if not project_match:
                # 尝试从文件名提取
                filename = os.path.basename(file_path)
                project_name = filename.replace("_评审.md", "")
                # 移除ID前缀（如果有）
                project_name = re.sub(r'^\d+_', '', project_name)
            else:
                project_name = project_match.group(1).strip()
            
            # 提取项目描述（如果有）
            description_match = re.search(r'## 项目描述\s*\n\s*(.+?)(?=\n\n##|\Z)', content, re.DOTALL)
            description = description_match.group(1).strip() if description_match else ""
            
            # 使用AI分类或手动分类
            category = self.ai_categorize(project_name, description)
            
            print(f"已将 {project_name} 分类为: {category}")
            return project_name, category
            
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")
            # 如果无法读取文件，尝试从文件名提取项目名称
            filename = os.path.basename(file_path)
            project_name = filename.replace("_评审.md", "")
            # 移除ID前缀（如果有）
            project_name = re.sub(r'^\d+_', '', project_name)
            category = self.ai_categorize(project_name, "")
            return project_name, category
    
    def add_project_to_category(self, project_name, category):
        """
        将项目添加到对应的分类中
        
        参数:
            project_name: 项目名称
            category: 项目类别
        """
        # 使用线程锁保护对categories字典的访问
        with self._lock:
            if category in self.categories:
                self.categories[category].append(project_name)
            else:
                self.categories["生活类"].append(project_name)
    
    def update_project_json(self, project_name, category):
        """
        将分类信息添加到项目数据的JSON文件中
        
        参数:
            project_name: 项目名称
            category: 项目类别
            
        返回:
            是否成功更新
        """
        try:
            # 从项目名称中提取ID（如果有）
            id_match = re.match(r'^(\d+)_', project_name)
            project_id = id_match.group(1) if id_match else None
            
            # 查找对应的JSON文件
            json_files = [f for f in os.listdir(self.project_data_dir) if f.endswith('.json')]
            target_file = None
            
            # 首先尝试通过ID匹配
            if project_id:
                for file in json_files:
                    if file.startswith(f"{project_id}_"):
                        target_file = file
                        break
            
            # 如果没有通过ID找到，尝试通过名称匹配
            if not target_file:
                for file in json_files:
                    # 移除.json后缀进行比较
                    file_name = file[:-5]
                    if file_name == project_name or project_name in file_name:
                        target_file = file
                        break
            
            if not target_file:
                print(f"未找到项目 {project_name} 对应的JSON文件")
                return False
            
            # 使用线程锁保护文件读写操作
            with self._lock:
                # 读取JSON文件
                json_path = os.path.join(self.project_data_dir, target_file)
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 添加或更新分类信息
                data['category'] = category
                
                # 写回JSON文件
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"已将项目 {project_name} 的分类信息 {category} 添加到 {target_file}")
            return True
            
        except Exception as e:
            print(f"更新项目 {project_name} 的JSON文件时出错: {e}")
            return False
    
    def generate_category_files(self):
        """
        生成分类结果文件
        """
        # 生成分类汇总文件
        summary_file = os.path.join(self.output_dir, "分类汇总.md")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("# AI创意大赛项目分类汇总\n\n")
            
            # 添加分类统计
            total_projects = sum(len(projects) for projects in self.categories.values())
            f.write(f"## 总体统计\n\n共计: {total_projects} 个项目\n\n")
            
            for category, projects in self.categories.items():
                count = len(projects)
                percentage = (count / total_projects * 100) if total_projects > 0 else 0
                f.write(f"- {category}: {count} 个项目 ({percentage:.1f}%)\n")
            
            # 添加详细分类列表
            f.write("\n## 详细分类\n\n")
            for category, projects in self.categories.items():
                f.write(f"### {category}\n\n")
                if projects:
                    for project in sorted(projects):
                        f.write(f"- {project}\n")
                else:
                    f.write("*暂无此类项目*\n")
                f.write("\n")
    
    def process_project(self, file_path):
        """
        处理单个项目的分类和JSON更新
        
        参数:
            file_path: 评审结果文件路径
            
        返回:
            (项目名称, 类别)的元组
        """
        try:
            filename = os.path.basename(file_path)
            print(f"正在分类: {filename}")
            
            project_name, category = self.categorize_project(file_path)
            self.add_project_to_category(project_name, category)
            self.update_project_json(project_name, category)
            
            print(f"完成分类: {filename} -> {category}")
            return project_name, category
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")
            return None, None
    
    def categorize_all_projects(self):
        """
        分类所有项目，使用线程池并发处理
        """
        # 获取所有评审结果文件
        review_files = [f for f in os.listdir(self.review_dir) if f.endswith("_评审.md")]
        total_files = len(review_files)
        
        print(f"\n开始分类，共 {total_files} 个项目，使用 {self.max_workers} 个并发线程\n")
        
        # 创建文件路径列表
        file_paths = [os.path.join(self.review_dir, filename) for filename in sorted(review_files)]
        
        # 使用线程池并发处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            futures = {executor.submit(self.process_project, file_path): file_path for file_path in file_paths}
            
            # 处理完成的任务
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                file_path = futures[future]
                try:
                    project_name, category = future.result()
                    completed += 1
                    print(f"进度: [{completed}/{total_files}] - {(completed/total_files)*100:.1f}%")
                except Exception as e:
                    print(f"处理文件 {file_path} 时出错: {e}")
        
        # 生成分类结果文件
        self.generate_category_files()
        
        print(f"\n分类完成，结果已保存到 {self.output_dir} 目录")
        print(f"分类信息已添加到 {self.project_data_dir} 目录下的JSON文件中")
        
        # 输出分类统计信息
        print("\n分类统计:")
        for category, projects in self.categories.items():
            count = len(projects)
            print(f"- {category}: {count} 个项目")


def main():
    """
    主函数，执行项目分类
    """
    print("开始项目分类过程...")
    
    # 确保从.env文件加载API配置
    load_dotenv(override=True)
    
    # 检查API配置是否存在
    api_url = os.getenv("DEEPSEEK_API_BASE_URL")
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_url or not api_key:
        print("错误: 未找到API配置，请在.env文件中设置DEEPSEEK_API_BASE_URL和DEEPSEEK_API_KEY")
        print("API调用格式示例:")
        print("DEEPSEEK_API_BASE_URL=https://api.deepseek.com")
        print("DEEPSEEK_API_KEY=your_api_key")
        return
    
    print(f"使用API端点: {api_url}")
    
    categorizer = ProjectCategorizer(review_dir="评审结果", output_dir="项目分类", project_data_dir="项目数据")
    categorizer.categorize_all_projects()
    print("分类过程完成！")


if __name__ == "__main__":
    main() 