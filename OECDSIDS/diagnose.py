"""
快速诊断和修复工具
用于诊断Selenium环境问题并提供修复建议
"""

import sys
import subprocess
import os
import platform

def print_section(title):
    """打印分隔标题"""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)

def check_python():
    """检查Python版本"""
    print_section("检查Python环境")
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print("✓ Python版本符合要求 (>= 3.8)")
        return True
    else:
        print("✗ Python版本过低，建议升级到3.8或更高")
        return False

def check_chrome():
    """检查Chrome浏览器"""
    print_section("检查Chrome浏览器")
    
    system = platform.system()
    
    if system == "Windows":
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
    elif system == "Darwin":  # Mac
        chrome_paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
    else:  # Linux
        chrome_paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
        ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            print(f"✓ Chrome已安装: {path}")
            
            # 尝试获取版本
            try:
                if system == "Windows":
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                        r"Software\Google\Chrome\BLBeacon")
                    version = winreg.QueryValueEx(key, "version")[0]
                    print(f"  版本: {version}")
                else:
                    result = subprocess.run([path, "--version"], 
                                          capture_output=True, text=True)
                    print(f"  版本: {result.stdout.strip()}")
            except:
                print("  (无法获取版本)")
            
            return True
    
    print("✗ Chrome未安装")
    print("  下载地址: https://www.google.com/chrome/")
    return False

def check_packages():
    """检查Python包"""
    print_section("检查Python包")
    
    required_packages = {
        'selenium': '4.0.0',
        'pandas': '1.3.0',
        'openpyxl': '3.0.0',
        'requests': '2.25.0',
    }
    
    optional_packages = {
        'webdriver-manager': '3.8.0',
        'playwright': '1.20.0',
        'beautifulsoup4': '4.9.0',
    }
    
    all_ok = True
    
    # 检查必需包
    print("\n必需包:")
    for package, min_version in required_packages.items():
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "show", package],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                # 从输出中提取版本
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        version = line.split(':')[1].strip()
                        print(f"  ✓ {package}: {version}")
                        break
            else:
                print(f"  ✗ {package}: 未安装")
                all_ok = False
        except:
            print(f"  ✗ {package}: 检查失败")
            all_ok = False
    
    # 检查可选包
    print("\n可选包:")
    for package, min_version in optional_packages.items():
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "show", package],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        version = line.split(':')[1].strip()
                        print(f"  ✓ {package}: {version}")
                        break
            else:
                print(f"  ⚠ {package}: 未安装（可选）")
        except:
            print(f"  ⚠ {package}: 检查失败（可选）")
    
    return all_ok

def test_selenium():
    """测试Selenium"""
    print_section("测试Selenium")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        print("正在测试Selenium + Chrome...")
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        try:
            # 尝试方法1: webdriver-manager
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            print("✓ 方法1成功: webdriver-manager")
            driver.quit()
            return True
            
        except Exception as e1:
            print(f"✗ 方法1失败: {e1}")
            
            try:
                # 尝试方法2: 直接启动
                driver = webdriver.Chrome(options=options)
                print("✓ 方法2成功: 直接启动Chrome")
                driver.quit()
                return True
                
            except Exception as e2:
                print(f"✗ 方法2失败: {e2}")
                return False
    
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False

def provide_solutions():
    """提供解决方案"""
    print_section("推荐的解决方案")
    
    print("\n方案1: 安装/更新所有依赖（推荐）")
    print("-" * 70)
    print("运行以下命令:")
    if platform.system() == "Windows":
        print("  pip install --upgrade selenium webdriver-manager pandas openpyxl requests")
    else:
        print("  pip install --upgrade selenium webdriver-manager pandas openpyxl requests --break-system-packages")
    
    print("\n方案2: 使用改进版程序")
    print("-" * 70)
    print("使用会自动尝试多种方法的改进版程序:")
    print("  python program1_scrape_oecd_improved.py")
    
    print("\n方案3: 使用简化版程序（无需浏览器）")
    print("-" * 70)
    print("如果浏览器方案都失败，使用:")
    print("  python program1_simple.py")
    
    print("\n方案4: 手动下载ChromeDriver")
    print("-" * 70)
    print("1. 访问: https://googlechromelabs.github.io/chrome-for-testing/")
    print("2. 下载与Chrome版本匹配的驱动")
    print("3. 将chromedriver.exe放到Python目录或PATH中")
    
    print("\n方案5: 使用Playwright（现代替代方案）")
    print("-" * 70)
    print("  pip install playwright")
    print("  playwright install chromium")

def auto_fix():
    """尝试自动修复"""
    print_section("自动修复")
    
    print("是否尝试自动安装/更新依赖包? (y/n): ", end="")
    try:
        choice = input().strip().lower()
    except:
        choice = 'n'
    
    if choice == 'y':
        print("\n正在安装/更新依赖包...")
        packages = [
            'selenium',
            'webdriver-manager', 
            'pandas',
            'openpyxl',
            'requests',
            'beautifulsoup4'
        ]
        
        for package in packages:
            print(f"\n安装 {package}...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", 
                              "--upgrade", package], check=True)
                print(f"  ✓ {package} 安装成功")
            except:
                print(f"  ✗ {package} 安装失败")
        
        print("\n完成！请重新运行诊断工具检查。")
        return True
    
    return False

def main():
    """主函数"""
    print("="*70)
    print(" OECD数据抓取工具 - 环境诊断")
    print("="*70)
    print(f" 操作系统: {platform.system()} {platform.release()}")
    print("="*70)
    
    # 运行检查
    python_ok = check_python()
    chrome_ok = check_chrome()
    packages_ok = check_packages()
    
    if python_ok and packages_ok:
        selenium_ok = test_selenium()
    else:
        selenium_ok = False
    
    # 总结
    print_section("诊断总结")
    
    checks = [
        ("Python环境", python_ok),
        ("Chrome浏览器", chrome_ok),
        ("Python包", packages_ok),
        ("Selenium测试", selenium_ok),
    ]
    
    for check_name, status in checks:
        symbol = "✓" if status else "✗"
        print(f"  {symbol} {check_name}: {'通过' if status else '失败'}")
    
    # 提供建议
    if all(status for _, status in checks):
        print("\n✓ 所有检查通过！您可以正常运行程序。")
        print("\n推荐运行:")
        print("  python program1_scrape_oecd_improved.py")
    else:
        print("\n✗ 发现问题，需要修复")
        provide_solutions()
        
        # 询问是否自动修复
        auto_fix()
    
    print("\n" + "="*70)
    print(" 诊断完成")
    print("="*70)
    print("\n查看详细故障排除指南: TROUBLESHOOTING.md")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n诊断已中断")
    except Exception as e:
        print(f"\n诊断出错: {e}")
        import traceback
        traceback.print_exc()