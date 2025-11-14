"""
HTML表格数据提取工具
从HTML文件中提取表格数据和链接，并保存到Excel文件
"""

from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
import sys

def extract_table_data(html_file_path, output_excel_path='output.xlsx'):
    """
    从HTML文件中提取表格数据和链接
    
    参数:
        html_file_path: HTML文件路径
        output_excel_path: 输出Excel文件路径
    """
    
    # 读取HTML文件
    print(f"正在读取HTML文件: {html_file_path}")
    with open(html_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 解析HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 查找主要数据表格（第一个表格）
    tables = soup.find_all('table')
    if not tables:
        print("错误: 未找到表格")
        return
    
    main_table = tables[0]
    rows = main_table.find_all('tr')
    print(f"找到 {len(rows)} 行数据（包含表头）")
    
    # 提取表头
    header_row = rows[0]
    headers = []
    for cell in header_row.find_all(['th', 'td']):
        header_text = cell.get_text(strip=True)
        headers.append(header_text)
    
    # 为链接列添加额外的表头
    headers.append('CAS Number Link')
    headers.append('Chemical Name Link')
    
    print(f"表头: {headers}")
    
    # 提取数据行
    data = []
    base_url = "https://hpvchemicals.oecd.org/ui/"
    
    for row_idx, row in enumerate(rows[1:], start=1):  # 跳过表头
        cells = row.find_all('td')
        if not cells:
            continue
        
        row_data = []
        cas_link = ''
        chem_link = ''
        
        for cell_idx, cell in enumerate(cells):
            # 提取文本
            text = cell.get_text(strip=True)
            row_data.append(text)
            
            # 提取链接
            link = cell.find('a')
            if link and link.get('href'):
                href = link.get('href')
                # 处理相对链接
                if not href.startswith('http') and not href.startswith('javascript'):
                    full_url = urljoin(base_url, href)
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = ''
                
                # 根据列位置保存链接
                if cell_idx == 0:  # CAS number列
                    cas_link = full_url
                elif cell_idx == 1:  # Chemical Name列
                    chem_link = full_url
        
        # 添加链接到行数据
        row_data.append(cas_link)
        row_data.append(chem_link)
        
        data.append(row_data)
        
        if row_idx % 20 == 0:
            print(f"已处理 {row_idx} 行...")
    
    print(f"共提取 {len(data)} 行数据")
    
    # 创建DataFrame
    df = pd.DataFrame(data, columns=headers)
    
    # 保存到Excel
    print(f"正在保存到Excel文件: {output_excel_path}")
    df.to_excel(output_excel_path, index=False, engine='openpyxl')
    
    print("完成！")
    print(f"\n数据预览:")
    print(df.head())
    print(f"\n总行数: {len(df)}")
    print(f"总列数: {len(df.columns)}")
    
    return df


if __name__ == "__main__":
    # 输入HTML文件路径
    if len(sys.argv) > 1:
        html_file = sys.argv[1]
    else:
        html_file = 'AllSponsoredGV.html'
    
    # 输出Excel文件路径
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        output_file = 'oecdsids.xlsx'
    
    # 执行提取
    extract_table_data(html_file, output_file)