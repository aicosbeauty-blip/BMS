#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OECD网站完整解决方案 - 带JSON导出
自动提取数据、下载PDF，并生成JSON报告
"""

import os
import time
import json
import requests
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
    print("⚠ 需要安装: pip install selenium webdriver-manager beautifulsoup4")


def find_all_pdf_links(html_content, base_url):
    """
    从HTML中查找所有PDF链接，包括handler.axd格式
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    pdf_links = []
    
    # 查找所有<a>标签
    for link in soup.find_all('a', href=True):
        href = link['href']
        text = link.get_text(strip=True)
        
        # 检查是否为PDF链接（.pdf结尾或包含handler.axd）
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
                'source': 'link',
                'link_text': text
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
                    'source': tag,
                    'link_text': ''
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
    
    # 提取关键字段
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
    
    # 提取关键字段
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


def download_pdf(url, output_path, session):
    """
    下载PDF文件
    
    返回: (success, file_size, error_message)
    """
    try:
        response = session.get(url, timeout=60, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(8192):
                if chunk:
                    f.write(chunk)
        
        file_size = os.path.getsize(output_path)
        return True, file_size, None
        
    except Exception as e:
        return False, 0, str(e)


def test_oecd_with_json(url, output_folder="oecd_json_test"):
    """
    完整的OECD网站测试，生成JSON报告
    """
    if not DEPS_AVAILABLE:
        print("\n❌ 缺少必要的库")
        print("请运行: pip install selenium webdriver-manager beautifulsoup4 requests")
        return None
    
    print("=" * 80)
    print("OECD完整测试 - 带JSON导出")
    print("=" * 80)
    print(f"URL: {url}\n")
    
    # 创建输出文件夹
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    
    # 初始化结果数据结构
    result = {
        'metadata': {
            'source_url': url,
            'extraction_time': datetime.now().isoformat(),
            'version': '1.0'
        },
        'chemical_info': {},
        'assessment_info': {},
        'pdf_files': [],
        'iframes': []
    }
    
    driver = None
    all_pdf_links = []
    
    try:
        # 1. 初始化Selenium
        print("步骤1: 初始化浏览器...")
        service = Service(ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(service=service, options=options)
        print("✓ 浏览器已启动\n")
        
        # 2. 访问主页面
        print("步骤2: 访问主页面...")
        driver.get(url)
        time.sleep(3)
        
        main_html = driver.page_source
        print(f"✓ 主页面大小: {len(main_html)} 字符\n")
        
        # 3. 查找所有iframe
        print("步骤3: 查找并访问iframe...")
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"找到 {len(iframes)} 个iframe\n")
        
        # 4. 访问每个iframe
        for i, iframe in enumerate(iframes, 1):
            try:
                iframe_id = iframe.get_attribute('id') or f"iframe_{i}"
                iframe_src = iframe.get_attribute('src')
                
                if not iframe_src or 'about:blank' in iframe_src:
                    continue
                
                print(f"[iframe {i}] {iframe_id}")
                print(f"  SRC: {iframe_src}")
                
                # 切换到iframe
                driver.switch_to.default_content()
                driver.switch_to.frame(iframe)
                time.sleep(2)
                
                # 获取内容
                iframe_html = driver.page_source
                iframe_base_url = urljoin(url, iframe_src)
                
                # 保存iframe HTML
                filename = f"iframe_{i}_{iframe_id.replace(':', '_')}.html"
                filepath = os.path.join(output_folder, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(iframe_html)
                
                print(f"  ✓ 已保存: {filename} ({len(iframe_html)} 字符)")
                
                # 记录iframe信息
                iframe_info = {
                    'index': i,
                    'id': iframe_id,
                    'src': iframe_src,
                    'html_file': filename,
                    'html_size': len(iframe_html)
                }
                
                # 查找PDF链接
                pdfs = find_all_pdf_links(iframe_html, iframe_base_url)
                if pdfs:
                    print(f"  ✓ 找到 {len(pdfs)} 个PDF:")
                    for pdf in pdfs:
                        print(f"    - {pdf['filename']}")
                    all_pdf_links.extend(pdfs)
                    iframe_info['pdf_count'] = len(pdfs)
                else:
                    iframe_info['pdf_count'] = 0
                
                # 提取数据
                if 'SIDS.aspx' in iframe_src:
                    result['chemical_info'] = extract_chemical_data(iframe_html)
                    iframe_info['type'] = 'chemical_info'
                    print(f"  ✓ 提取了化学品数据")
                elif 'SidsOrganigrame.aspx' in iframe_src:
                    result['assessment_info'] = extract_assessment_data(iframe_html)
                    iframe_info['type'] = 'assessment_info'
                    print(f"  ✓ 提取了评估数据")
                else:
                    iframe_info['type'] = 'other'
                
                result['iframes'].append(iframe_info)
                print()
                
                # 切换回主页面
                driver.switch_to.default_content()
                
            except Exception as e:
                print(f"  ✗ 处理失败: {e}\n")
                driver.switch_to.default_content()
                continue
        
        # 5. 直接访问iframe URL
        print("步骤4: 直接访问iframe URL...")
        
        soup = BeautifulSoup(main_html, 'html.parser')
        direct_urls = []
        for iframe_elem in soup.find_all('iframe'):
            src = iframe_elem.get('src')
            if src and 'about:blank' not in src:
                full_url = urljoin(url, src)
                direct_urls.append(full_url)
        
        for i, direct_url in enumerate(direct_urls, 1):
            try:
                print(f"\n[直接访问 {i}] {direct_url}")
                driver.get(direct_url)
                time.sleep(2)
                
                direct_html = driver.page_source
                
                # 保存HTML
                filename = f"direct_iframe_{i}.html"
                filepath = os.path.join(output_folder, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(direct_html)
                
                print(f"  ✓ 已保存: {filename} ({len(direct_html)} 字符)")
                
                # 查找PDF
                pdfs = find_all_pdf_links(direct_html, direct_url)
                if pdfs:
                    print(f"  ✓ 找到 {len(pdfs)} 个PDF:")
                    for pdf in pdfs:
                        print(f"    - {pdf['filename']}")
                    all_pdf_links.extend(pdfs)
                
                # 提取数据（补充或更新）
                if 'SIDS.aspx' in direct_url:
                    chem_data = extract_chemical_data(direct_html)
                    if chem_data:
                        result['chemical_info'].update(chem_data)
                elif 'SidsOrganigrame.aspx' in direct_url:
                    assess_data = extract_assessment_data(direct_html)
                    if assess_data:
                        result['assessment_info'].update(assess_data)
                
            except Exception as e:
                print(f"  ✗ 访问失败: {e}")
                continue
        
        # 6. 去重PDF链接
        seen = set()
        unique_pdfs = []
        for pdf in all_pdf_links:
            if pdf['url'] not in seen:
                seen.add(pdf['url'])
                unique_pdfs.append(pdf)
        
        all_pdf_links = unique_pdfs
        
        # 7. 显示提取的数据
        print("\n" + "=" * 80)
        print("提取的化学品数据")
        print("=" * 80)
        for key, value in result['chemical_info'].items():
            print(f"{key:.<35} {value}")
        
        print("\n" + "=" * 80)
        print("提取的评估数据")
        print("=" * 80)
        for key, value in result['assessment_info'].items():
            print(f"{key:.<35} {value}")
        
        # 8. 显示PDF链接
        print("\n" + "=" * 80)
        print(f"找到 {len(all_pdf_links)} 个PDF文件")
        print("=" * 80)
        
        if not all_pdf_links:
            print("\n⚠ 未找到PDF链接")
        else:
            # 准备下载
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            # 下载每个PDF
            print("\n步骤5: 下载PDF文件...\n")
            
            for i, pdf in enumerate(all_pdf_links, 1):
                print(f"[PDF {i}/{len(all_pdf_links)}]")
                print(f"  文件名: {pdf['filename']}")
                print(f"  URL: {pdf['url']}")
                
                # 生成安全的文件名
                safe_filename = pdf['filename'].replace('/', '_').replace('\\', '_')
                local_path = os.path.join(output_folder, safe_filename)
                
                print(f"  正在下载...")
                success, file_size, error = download_pdf(pdf['url'], local_path, session)
                
                # 准备PDF信息
                pdf_info = {
                    'index': i,
                    'filename': safe_filename,
                    'original_filename': pdf['filename'],
                    'url': pdf['url'],
                    'link_text': pdf.get('link_text', ''),
                    'source': pdf.get('source', ''),
                    'local_path': os.path.abspath(local_path),
                    'download_success': success
                }
                
                if success:
                    pdf_info['file_size_bytes'] = file_size
                    pdf_info['file_size_kb'] = round(file_size / 1024, 2)
                    pdf_info['file_size_mb'] = round(file_size / (1024 * 1024), 2)
                    print(f"  ✓ 成功!")
                    print(f"     大小: {file_size:,} 字节 ({pdf_info['file_size_kb']:.2f} KB)")
                    print(f"     路径: {pdf_info['local_path']}")
                else:
                    pdf_info['error'] = error
                    print(f"  ✗ 失败: {error}")
                
                result['pdf_files'].append(pdf_info)
                print()
                
                time.sleep(1)
            
            # 统计
            success_count = sum(1 for p in result['pdf_files'] if p['download_success'])
            print(f"下载完成: {success_count}/{len(all_pdf_links)} 个PDF")
        
        # 9. 保存JSON
        print("\n" + "=" * 80)
        print("保存JSON报告")
        print("=" * 80)
        
        json_path = os.path.join(output_folder, "oecd_data.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"✓ JSON已保存: {os.path.abspath(json_path)}")
        
        # 也保存一个格式化的易读版本
        pretty_json_path = os.path.join(output_folder, "oecd_data_pretty.json")
        with open(pretty_json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4, sort_keys=True)
        
        print(f"✓ 格式化JSON已保存: {os.path.abspath(pretty_json_path)}")
        
        # 10. 最终总结
        print("\n" + "=" * 80)
        print("测试完成！")
        print("=" * 80)
        print(f"\n📁 所有文件保存在: {os.path.abspath(output_folder)}\n")
        
        # 统计信息
        print("📊 统计信息:")
        print(f"  - 化学品字段: {len(result['chemical_info'])} 个")
        print(f"  - 评估字段: {len(result['assessment_info'])} 个")
        print(f"  - 处理的iframe: {len(result['iframes'])} 个")
        print(f"  - PDF文件: {len(result['pdf_files'])} 个")
        if result['pdf_files']:
            success_pdfs = [p for p in result['pdf_files'] if p['download_success']]
            print(f"  - 成功下载: {len(success_pdfs)} 个")
            total_size = sum(p.get('file_size_kb', 0) for p in success_pdfs)
            print(f"  - 总大小: {total_size:.2f} KB")
        
        # 列出文件
        files = os.listdir(output_folder)
        html_files = [f for f in files if f.endswith('.html')]
        pdf_files = [f for f in files if f.endswith('.pdf')]
        json_files = [f for f in files if f.endswith('.json')]
        
        print(f"\n📝 生成的文件:")
        if json_files:
            print(f"  JSON文件 ({len(json_files)}个):")
            for f in sorted(json_files):
                size = os.path.getsize(os.path.join(output_folder, f))
                print(f"    - {f} ({size:,} 字节)")
        
        if pdf_files:
            print(f"  PDF文件 ({len(pdf_files)}个):")
            for f in sorted(pdf_files):
                size = os.path.getsize(os.path.join(output_folder, f))
                print(f"    - {f} ({size:,} 字节)")
        
        if html_files:
            print(f"  HTML文件 ({len(html_files)}个): {len(html_files)}个iframe内容")
        
        print("\n" + "=" * 80)
        
        return result
        
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        if driver:
            driver.quit()
            print("\n浏览器已关闭")


def main():
    """主函数"""
    import sys
    
    print("\n" + "=" * 80)
    print("OECD完整测试 - 带JSON导出")
    print("=" * 80)
    print("\n功能:")
    print("  ✓ 自动处理iframe结构")
    print("  ✓ 识别handler.axd格式PDF链接")
    print("  ✓ 提取完整化学品和评估数据")
    print("  ✓ 下载所有PDF文件（支持多个）")
    print("  ✓ 生成JSON报告（包含所有数据和PDF信息）")
    print("\n" + "=" * 80 + "\n")
    
    # 默认URL
    test_url = "https://hpvchemicals.oecd.org/ui/SIDS_Details.aspx?id=b1b28e5c-118a-4d76-ad61-e9fe4cb9aa30"
    
    # 命令行参数
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    
    result = test_oecd_with_json(test_url)
    
    if result:
        print("\n✅ JSON数据结构:")
        print(f"  - metadata: 元数据（URL、时间等）")
        print(f"  - chemical_info: 化学品基本信息")
        print(f"  - assessment_info: 赞助和评估信息")
        print(f"  - pdf_files: PDF文件列表（{len(result['pdf_files'])}个）")
        print(f"  - iframes: iframe处理信息")
        print("\n可以使用以下命令查看JSON:")
        print("  cat oecd_json_test/oecd_data.json")
        print("  cat oecd_json_test/oecd_data_pretty.json")


if __name__ == "__main__":
    main()