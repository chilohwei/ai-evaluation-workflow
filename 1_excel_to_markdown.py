#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Excel表格转Markdown脚本
这个脚本负责读取Excel表格中的参赛作品信息，并将其转换为Markdown格式文件
"""

import os
import pandas as pd
import re
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("excel_to_markdown.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Excel转Markdown")

class ExcelToMarkdown:
    def __init__(self, excel_file="AI创意大赛全部已去重.xlsx", output_dir="参赛作品"):
        """
        初始化转换器
        
        参数:
            excel_file: Excel文件路径
            output_dir: 输出目录路径
        """
        self.excel_file = excel_file
        self.output_dir = output_dir
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"初始化完成，将从 {excel_file} 读取数据并输出到 {output_dir}")
    
    def load_excel_data(self):
        """
        加载Excel数据
        
        返回:
            包含参赛作品信息的DataFrame
        """
        try:
            # 读取Excel文件
            df = pd.read_excel(self.excel_file)
            logger.info(f"成功读取 {len(df)} 条记录")
            return df
        except Exception as e:
            logger.error(f"读取Excel文件时出错: {e}")
            return None
    
    def clean_project_name(self, name):
        """
        清理项目名称，移除无效字符
        
        参数:
            name: 原始项目名称
            
        返回:
            清理后的项目名称
        """
        if not isinstance(name, str):
            return "未命名项目"
        
        # 移除文件名中不允许的字符
        cleaned_name = re.sub(r'[\\/*?:"<>|]', '', name)
        # 移除多余的空格
        cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()
        # 如果名称为空，使用默认名称
        if not cleaned_name:
            cleaned_name = "未命名项目"
            
        return cleaned_name
    
    def create_markdown_content(self, row, index):
        """
        为每个参赛作品创建Markdown内容
        
        参数:
            row: DataFrame中的一行，包含项目信息
            index: 项目索引，用于生成文件名
            
        返回:
            Markdown格式的内容
        """
        # 从行数据中提取信息
        project_name = self.clean_project_name(row.get('1.创意名称', f"项目{index}"))
        submitter = row.get('发起人姓名', "未知")
        description = row.get('2.详细描述', "无描述")
        business_prospect = row.get('3.（选填）商业前景预测', "")
        development_method = row.get('4.（选填）开发与运营方法', "")
        additional_info = row.get('5.（选填）其他补充信息', "")
        
        # 创建Markdown内容
        content = f"""# {project_name}

## 基本信息
- **提交人**: {submitter}
- **提交时间**: {datetime.now().strftime('%Y-%m-%d')}

## 详细描述
{description}

"""
        # 添加可选字段（如果有内容）
        if pd.notna(business_prospect) and business_prospect.strip():
            content += f"""## 商业前景预测
{business_prospect}

"""
            
        if pd.notna(development_method) and development_method.strip():
            content += f"""## 开发与运营方法
{development_method}

"""
            
        if pd.notna(additional_info) and additional_info.strip():
            content += f"""## 补充信息
{additional_info}
"""
        
        return content
    
    def convert(self):
        """
        执行转换过程
        """
        # 加载Excel数据
        df = self.load_excel_data()
        if df is None:
            return
        
        # 成功转换计数
        success_count = 0
        
        # 处理每一行数据
        for index, row in df.iterrows():
            try:
                # 获取项目名称和索引号（从1开始）
                project_index = index + 1
                project_name = self.clean_project_name(row.get('1.创意名称', f"项目{project_index}"))
                
                # 格式化索引号为两位数字符串
                formatted_index = f"{project_index:02d}"
                
                # 创建文件名
                file_name = f"{formatted_index}_{project_name}.md"
                file_path = os.path.join(self.output_dir, file_name)
                
                # 创建Markdown内容
                content = self.create_markdown_content(row, project_index)
                
                # 写入文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                success_count += 1
                logger.info(f"成功转换: {file_name}")
                
            except Exception as e:
                logger.error(f"处理第 {index+1} 行数据时出错: {e}")
        
        logger.info(f"\n转换完成，共成功转换 {success_count}/{len(df)} 个项目")


def main():
    """
    主函数，执行Excel到Markdown的转换
    """
    logger.info("开始执行Excel到Markdown的转换...")
    converter = ExcelToMarkdown()
    converter.convert()
    logger.info("转换完成！")


if __name__ == "__main__":
    main() 