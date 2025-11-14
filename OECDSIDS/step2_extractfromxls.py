#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OECD批量处理 - Excel版本
从Excel读取URL，批量提取数据和下载PDF，支持断点续传
"""

import os
import time
import json
import hashlib
import requests
import pandas as pd
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from bs4 import BeautifulSoup
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False
    print("⚠ 需要安装: pip install selenium webdriver-manager beautifulsoup4 pandas openpyxl")


def calculate_file_md5(filepath):
    """
    计算文件的MD5哈希值
    
    参数:
        filepath: 文件路径
    
    返回:
        MD5哈希值（32位小写十六进制字符串）
    """
    md5_hash = hashlib.md5()
    
    with open(filepath, "rb") as f:
        # 分块读取，适合大文件
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    
    return md5_hash.hexdigest()


def find_all_pdf_links(html_content, base_url):
    """从HTML中查找所有PDF链接，包括handler.axd格式"""
    soup = BeautifulSoup(html_content, 'html.parser')
    pdf_links = []
    
    # 查找所有<a>标签
    for link in soup.find_all('a', href=True):
        href = link['href']
        text = link.get_text(strip=True)
        
        if '.pdf' in href.lower() or 'handler.axd' in href.lower():
            full_url = urljoin(base_url, href)
            
            # 提取文件名
            if text and text.endswith('.pdf'):
                filename = text
            elif '.pdf' in href.lower():
                filename = href.split('/')[-1]
                if '?' in filename:
                    filename = filename.split('?')[0]
            else:
                filename = text if text else 'document.pdf'
                if not filename.endswith('.pdf'):
                    filename += '.pdf'
            
            pdf_links.append({
                'filename': filename,
                'url': full_url,
                'source': 'link'
            })
    
    # 查找embed、object、iframe标签
    for tag in ['embed', 'object', 'iframe']:
        for elem in soup.find_all(tag):
            src = elem.get('src') or elem.get('data')
            if src and ('.pdf' in src.lower() or 'handler.axd' in src.lower()):
                full_url = urljoin(base_url, src)
                filename = src.split('/')[-1] or 'document.pdf'
                if not filename.endswith('.pdf'):
                    filename += '.pdf'
                
                pdf_links.append({
                    'filename': filename,
                    'url': full_url,
                    'source': tag
                })
    
    # 去重
    seen_urls = set()
    unique_links = []
    for link in pdf_links:
        if link['url'] not in seen_urls:
            seen_urls.add(link['url'])
            unique_links.append(link)
    
    return unique_links


def extract_chemical_data(html_content):
    """从SIDS.aspx iframe提取化学品数据"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    data = {}
    
    fields = {
        'CasnumLabel': 'cas_number',
        'SYNONYMLLabel': 'chemical_name',
        'OtherSynonymsLabel': 'synonyms',
        'InHPVLabel': 'hpv_status',
        'RecoLowHazardLabel': 'recognized_low_hazard',
        'IndInitiativeLabel': 'on_icca_list',
        'AddremarksLabel': 'additional_information'
    }
    
    for span_id, field_name in fields.items():
        elem = soup.find('span', id=span_id)
        data[field_name] = elem.text.strip() if elem and elem.text.strip() else None
    
    return data


def extract_assessment_data(html_content):
    """从SidsOrganigrame.aspx iframe提取评估数据"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    data = {}
    
    fields = {
        'SponsorsLabel': 'sponsors',
        'SponsorshipDateLabel': 'sponsorship_date',
        'CurrentStatusLabel': 'current_status',
        'MeetingSIAMLabel': 'assessment_meeting',
        'DatePublishedLabel': 'date_published',
        'TargetedAssessmentLabel': 'targeted_assessment',
    }
    
    for span_id, field_name in fields.items():
        elem = soup.find('span', id=span_id)
        data[field_name] = elem.text.strip() if elem and elem.text.strip() else None
    
    # 提取Category
    category_link = soup.find('a', id='CategoryHL')
    if category_link:
        data['category'] = category_link.text.strip()
        data['category_link'] = category_link.get('href', '')
    else:
        data['category'] = None
        data['category_link'] = None
    
    # 提取ICCA备注
    icca_label = soup.find('span', id='SidsOrganigrame_ICCA_Label')
    if icca_label:
        data['icca_note'] = icca_label.text.strip()
    else:
        data['icca_note'] = None
    
    return data


def download_pdf_with_md5(url, output_folder, session):
    """
    下载PDF文件并用MD5命名
    
    返回: (success, original_filename, md5_filename, file_size, error_message)
    """
    try:
        response = session.get(url, timeout=60, stream=True)
        response.raise_for_status()
        
        # 先下载到临时文件
        temp_path = os.path.join(output_folder, f"temp_{int(time.time())}.pdf")
        
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(8192):
                if chunk:
                    f.write(chunk)
        
        # 计算MD5
        md5_hash = calculate_file_md5(temp_path)
        
        # 重命名为MD5
        md5_filename = f"{md5_hash}.pdf"
        final_path = os.path.join(output_folder, md5_filename)
        
        # 如果MD5文件已存在，删除临时文件
        if os.path.exists(final_path):
            os.remove(temp_path)
            file_size = os.path.getsize(final_path)
            return True, None, md5_filename, file_size, None
        else:
            # 重命名临时文件
            os.rename(temp_path, final_path)
            file_size = os.path.getsize(final_path)
            return True, None, md5_filename, file_size, None
        
    except Exception as e:
        # 清理临时文件
        if 'temp_path' in locals() and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return False, None, None, 0, str(e)


def process_single_url(url, pdf_folder, driver, session):
    """
    处理单个URL，提取数据和下载PDF
    
    参数:
        url: OECD URL
        pdf_folder: PDF保存文件夹
        driver: Selenium WebDriver
        session: requests Session
    
    返回:
        result dict 或 None（如果失败）
    """
    result = {
        'metadata': {
            'source_url': url,
            'extraction_time': datetime.now().isoformat(),
            'version': '1.0'
        },
        'chemical_info': {},
        'assessment_info': {},
        'pdf_files': []
    }
    
    all_pdf_links = []
    
    try:
        # 访问主页面
        driver.get(url)
        time.sleep(3)
        
        main_html = driver.page_source
        
        # 查找所有iframe
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        
        # 访问每个iframe（不保存HTML）
        for i, iframe in enumerate(iframes, 1):
            try:
                iframe_src = iframe.get_attribute('src')
                
                if not iframe_src or 'about:blank' in iframe_src:
                    continue
                
                # 切换到iframe
                driver.switch_to.default_content()
                driver.switch_to.frame(iframe)
                time.sleep(2)
                
                # 获取内容
                iframe_html = driver.page_source
                iframe_base_url = urljoin(url, iframe_src)
                
                # 查找PDF链接
                pdfs = find_all_pdf_links(iframe_html, iframe_base_url)
                if pdfs:
                    all_pdf_links.extend(pdfs)
                
                # 提取数据
                if 'SIDS.aspx' in iframe_src:
                    result['chemical_info'] = extract_chemical_data(iframe_html)
                elif 'SidsOrganigrame.aspx' in iframe_src:
                    result['assessment_info'] = extract_assessment_data(iframe_html)
                
                # 切换回主页面
                driver.switch_to.default_content()
                
            except Exception as e:
                driver.switch_to.default_content()
                continue
        
        # 直接访问iframe URL
        soup = BeautifulSoup(main_html, 'html.parser')
        direct_urls = []
        for iframe_elem in soup.find_all('iframe'):
            src = iframe_elem.get('src')
            if src and 'about:blank' not in src:
                full_url = urljoin(url, src)
                direct_urls.append(full_url)
        
        for direct_url in direct_urls:
            try:
                driver.get(direct_url)
                time.sleep(2)
                
                direct_html = driver.page_source
                
                # 查找PDF
                pdfs = find_all_pdf_links(direct_html, direct_url)
                if pdfs:
                    all_pdf_links.extend(pdfs)
                
                # 提取数据
                if 'SIDS.aspx' in direct_url:
                    chem_data = extract_chemical_data(direct_html)
                    if chem_data:
                        result['chemical_info'].update(chem_data)
                elif 'SidsOrganigrame.aspx' in direct_url:
                    assess_data = extract_assessment_data(direct_html)
                    if assess_data:
                        result['assessment_info'].update(assess_data)
                
            except Exception as e:
                continue
        
        # 去重PDF链接
        seen = set()
        unique_pdfs = []
        for pdf in all_pdf_links:
            if pdf['url'] not in seen:
                seen.add(pdf['url'])
                unique_pdfs.append(pdf)
        
        all_pdf_links = unique_pdfs
        
        # 下载PDF
        for i, pdf in enumerate(all_pdf_links, 1):
            success, orig_name, md5_name, size, error = download_pdf_with_md5(
                pdf['url'], pdf_folder, session
            )
            
            pdf_info = {
                'index': i,
                'original_filename': pdf['filename'],
                'url': pdf['url'],
                'download_success': success
            }
            
            if success:
                pdf_info['filemd5'] = md5_name.replace('.pdf', '')  # 只保存MD5值
                pdf_info['saved_filename'] = md5_name
                pdf_info['file_size_bytes'] = size
                pdf_info['file_size_kb'] = round(size / 1024, 2)
            else:
                pdf_info['error'] = error
                pdf_info['filemd5'] = None
                pdf_info['saved_filename'] = None
            
            result['pdf_files'].append(pdf_info)
            
            time.sleep(1)
        
        return result
        
    except Exception as e:
        print(f"    ✗ 处理失败: {e}")
        return None


def process_excel_batch(excel_file, pdf_folder="oecdpdfs"):
    """
    批量处理Excel文件，支持断点续传
    
    参数:
        excel_file: Excel文件路径
        pdf_folder: PDF保存文件夹
    """
    if not DEPS_AVAILABLE:
        print("\n❌ 缺少必要的库")
        print("请运行: pip install selenium webdriver-manager beautifulsoup4 pandas openpyxl requests")
        return
    
    print("=" * 80)
    print("OECD批量处理 - Excel版本")
    print("=" * 80)
    print(f"Excel文件: {excel_file}")
    print(f"PDF文件夹: {pdf_folder}\n")
    
    # 创建PDF文件夹
    Path(pdf_folder).mkdir(parents=True, exist_ok=True)
    
    # 读取Excel
    print("步骤1: 读取Excel文件...")
    try:
        df = pd.read_excel(excel_file, engine='openpyxl')
        print(f"✓ 成功读取，共 {len(df)} 行数据\n")
    except Exception as e:
        print(f"✗ 读取Excel失败: {e}")
        return
    
    # 确保M列存在
    if 'M' not in df.columns:
        df['M'] = None
    
    # 检查断点续传
    total_rows = len(df)
    processed_rows = df['M'].notna().sum()
    remaining_rows = total_rows - processed_rows
    
    print(f"📊 数据统计:")
    print(f"  总行数: {total_rows}")
    print(f"  已处理: {processed_rows}")
    print(f"  待处理: {remaining_rows}\n")
    
    if remaining_rows == 0:
        print("✓ 所有数据已处理完成！")
        return
    
    # 初始化Selenium
    print("步骤2: 初始化浏览器...")
    try:
        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(service=service, options=options)
        print("✓ 浏览器已启动\n")
    except Exception as e:
        print(f"✗ 浏览器初始化失败: {e}")
        return
    
    # 初始化requests session
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    try:
        # 处理每一行
        print("步骤3: 开始批量处理...\n")
        print("=" * 80)
        
        success_count = 0
        error_count = 0
        
        # 从第2行开始（索引1），跳过表头
        for idx in range(1, len(df)):
            row = df.iloc[idx]
            
            # 检查M列是否已有数据（断点续传）
            if pd.notna(row.get('M')):
                continue  # 跳过已处理的行
            
            # 获取K列的URL（索引10，因为K是第11列）
            url = row.iloc[10] if len(row) > 10 else None
            
            if pd.isna(url) or not url:
                print(f"[行 {idx + 1}] 跳过：URL为空")
                continue
            
            print(f"\n[行 {idx + 1}/{total_rows}]")
            print(f"  URL: {url}")
            print(f"  处理中...")
            
            # 处理URL
            result = process_single_url(url, pdf_folder, driver, session)
            
            if result:
                # 转换为JSON字符串
                json_str = json.dumps(result, ensure_ascii=False)
                
                # 写入M列
                df.at[idx, 'M'] = json_str
                
                # 保存Excel（增量保存）
                df.to_excel(excel_file, index=False, engine='openpyxl')
                
                # 统计信息
                pdf_count = len(result['pdf_files'])
                success_pdfs = sum(1 for p in result['pdf_files'] if p['download_success'])
                
                print(f"  ✓ 成功!")
                print(f"     化学品: {result['chemical_info'].get('chemical_name', 'N/A')}")
                print(f"     PDF: {success_pdfs}/{pdf_count} 个下载成功")
                
                if result['pdf_files']:
                    for pdf in result['pdf_files']:
                        if pdf['download_success']:
                            print(f"       - {pdf['original_filename']} → {pdf['filemd5']}.pdf")
                
                success_count += 1
            else:
                print(f"  ✗ 失败")
                error_count += 1
            
            print(f"  进度: {success_count + error_count}/{remaining_rows}")
            
            # 添加延迟
            time.sleep(2)
        
        print("\n" + "=" * 80)
        print("批量处理完成！")
        print("=" * 80)
        print(f"\n📊 最终统计:")
        print(f"  成功: {success_count}")
        print(f"  失败: {error_count}")
        print(f"  总计: {success_count + error_count}")
        print(f"\n📁 PDF保存在: {os.path.abspath(pdf_folder)}")
        print(f"📄 Excel已更新: {os.path.abspath(excel_file)}")
        
        # 统计PDF
        pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith('.pdf')]
        if pdf_files:
            total_size = sum(os.path.getsize(os.path.join(pdf_folder, f)) for f in pdf_files)
            print(f"\n📄 PDF文件统计:")
            print(f"  文件数量: {len(pdf_files)}")
            print(f"  总大小: {total_size / (1024*1024):.2f} MB")
        
        print("\n" + "=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n⚠ 用户中断")
        print("已处理的数据已保存到Excel，可以稍后继续运行（支持断点续传）")
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print("\n浏览器已关闭")


def main():
    """主函数"""
    import sys
    
    print("\n" + "=" * 80)
    print("OECD批量处理工具")
    print("=" * 80)
    print("\n功能:")
    print("  ✓ 从Excel的K列读取URL")
    print("  ✓ 提取化学品和评估数据")
    print("  ✓ 下载PDF（用MD5命名）")
    print("  ✓ JSON结果写入M列")
    print("  ✓ 支持断点续传")
    print("\n" + "=" * 80 + "\n")
    
    # Excel文件路径
    excel_file = "oecdsids.xlsx"
    
    # 命令行参数
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    
    # 检查文件是否存在
    if not os.path.exists(excel_file):
        print(f"❌ Excel文件不存在: {excel_file}")
        print(f"\n请确保文件存在，或指定正确的文件路径:")
        print(f"  python batch_process_excel.py your_file.xlsx")
        return
    
    # 开始处理
    process_excel_batch(excel_file)


if __name__ == "__main__":
    main()