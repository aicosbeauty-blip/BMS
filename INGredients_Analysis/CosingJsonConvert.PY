# =================================================================================
# --- COSING JSON 批量转换器 (Python 版) ---
#
# [V8.0 - 新增 403 错误处理]
# 移植自 Google Apps Script (GAS)
# - 使用 openpyxl 读写 Excel
# - 使用 asyncio 和 httpx 实现并发 API 请求
# - 使用 config.json 替代 PropertiesService 来管理状态
# - [!] Schema 从外部 'schema.json' 加载
# - [!] API Keys 从外部 'api_keys.json' 加载
# - [!] 移除 5.5 分钟运行限制
# - [!] 新增 连续 6 次失败则停止的逻辑 (全局)
# - [!] [V5 变更] 输入源从 A-J 列改为 K 列
# - [!] [V6 变更] 新增 API 密钥管理器 (单个Key连续失败10次则禁用)
# - [!] [V6 变更] 批次间延迟改为 4 秒
# - [!] [V7 变更] JSON格式错误时调用PRO模型重新生成，不再尝试修复
# - [!] [V7.1 变更] PRO模型失败2次后标记失败并跳过该行
# - [!] [V7.2 变更] 修复MAX_TOKENS和超时异常处理，增加maxOutputTokens
# - [!] [V7.3 变更] KEY 失效逻辑改为：连续 3 次 QUOTA 错误 (429) 则禁用
# - [!] [V7.4 变更] 将 maxOutputTokens 调整为 8192 (模型上限)
# - [!] [V7.4 变更] MAX_TOKENS 错误将立即失败，不再重试 (因为重试也无效)
# - [!] [V7.5 变更] 将 maxOutputTokens 调整为 65536
# - [!] [V8.0 变更] 新增 403 (Forbidden) 错误处理，遇到 403 立即禁用该 Key
# =================================================================================

import os
import sys
import json
import logging
import re
import time
import argparse
import asyncio
import httpx
from openpyxl import load_workbook, Workbook
from openpyxl.utils.cell import get_column_letter
from datetime import datetime

# --- 常量定义 (Constants) ---
# [!] 配置文件路径 (Configuration File Paths)
EXCEL_FILE_PATH = "Cosing数据库XLS.xlsx"  # [!] 请将此更改为您的 Excel 文件名
CONFIG_FILE_PATH = 'cosing_config.json'
SCHEMA_FILE_PATH = "schema.json" # [!] Schema 文件路径
API_KEYS_FILE_PATH = "api_keys.json" # [!] API 密钥文件路径

# --- 表格列定义 (Sheet Columns) ---
SHEET_NAME = "COSING"
HEADER_ROW = 1
DATA_START_ROW = 2

DATA_START_COL = 1
DATA_END_COL_LETTER = 'J' # A-J 列（用于清理表头，但不由 API 使用）
SCCS_OPINION_COL = 8  # H列 (用于模型选择)
K_COL = 11            # K列 (新的 API 输入源)
TARGET_COL = 12       # L列 (用于存放JSON)
STATUS_COL = 13       # M列 (用于存放状态)

# --- API 与并发配置 ---
# [!] API_KEYS 将从 api_keys.json 加载
CONCURRENCY_LEVEL = 8
BATCH_DELAY_SEC = 2  # [!] V6 变更：批次间延迟 4 秒
API_TIMEOUT_SEC = 120 # API 请求超时时间
API_MAX_RETRIES = 3   # API 请求最大重试次数（仅用于网络错误等）

# --- 模型定义 (Models) ---
MODEL_DEFAULT = "gemini-2.5-flash"
MODEL_ADVANCED = "gemini-2.5-flash"
RETRY_MODEL = "gemini-2.5-pro"

# --- 运行控制 (Runtime Control) ---
MAX_CONSECUTIVE_FAILURES = 6 # [!] 全局连续失败 6 次则停止
# [!] V7.3 变更：失效逻辑基于 QUOTA (429 错误)
API_KEY_MAX_QUOTA_FAILURES = 3 # [!] V7.3 变更：单个 API Key 连续 QUOTA 失败 3 次则禁用
MAX_PRO_ATTEMPTS = 2        # [!] V7.1 新增：PRO 模型最大尝试次数

# --- 日志配置 (Logging Config) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# =================================================================================
# --- [!] JSON Schema 加载 ---
# =================================================================================

def load_json_schema(schema_path: str) -> dict:
    """
    从外部文件加载 JSON Schema。
    Loads the JSON Schema from an external file.
    """
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        logging.info(f"[初始化] 成功从 {schema_path} 加载 JSON Schema。")
        return schema
    except FileNotFoundError:
        logging.error(f"[致命错误] Schema 文件未找到: {schema_path}")
        logging.error("请确保 'schema.json' 文件与 .py 脚本在同一目录中。")
        sys.exit(1) # 退出程序
    except json.JSONDecodeError as e:
        logging.error(f"[致命错误] Schema 文件 {schema_path} 格式错误，无法解析 JSON: {e}")
        sys.exit(1) # 退出程序
    except Exception as e:
        logging.error(f"[致命错误] 加载 Schema 时发生未知错误: {e}")
        sys.exit(1) # 退出程序

# [!] 全局变量：在脚本开始时加载 Schema
COSMETIC_REGULATION_SCHEMA = load_json_schema(SCHEMA_FILE_PATH)

if not COSMETIC_REGULATION_SCHEMA:
    logging.error("[致命错误] JSON Schema 未能成功加载，程序无法继续。")
    sys.exit(1)

# =================================================================================
# --- [!] API 密钥加载 (新增) ---
# =================================================================================

def load_api_keys(keys_path: str) -> list:
    """
    从外部文件加载 API 密钥。
    Loads the API keys from an external file.
    """
    try:
        with open(keys_path, 'r', encoding='utf-8') as f:
            keys_data = json.load(f)
            if "api_keys" not in keys_data or not isinstance(keys_data["api_keys"], list):
                raise ValueError("文件 'api_keys.json' 必须包含一个名为 'api_keys' 的 JSON 列表。")
            
            keys_list = keys_data["api_keys"]
            if not keys_list:
                raise ValueError("'api_keys' 列表不能为空。")

            logging.info(f"[初始化] 成功从 {keys_path} 加载 {len(keys_list)} 个 API 密钥。")
            return keys_list
    except FileNotFoundError:
        logging.error(f"[致命错误] API 密钥文件未找到: {keys_path}")
        logging.error("请创建 'api_keys.json' 文件，并按格式填入您的 API 密钥。")
        sys.exit(1) # 退出程序
    except json.JSONDecodeError as e:
        logging.error(f"[致命错误] 密钥文件 {keys_path} 格式错误，无法解析 JSON: {e}")
        sys.exit(1) # 退出程序
    except ValueError as e:
        logging.error(f"[致命错误] 密钥文件 {keys_path} 内容无效: {e}")
        sys.exit(1) # 退出程序
    except Exception as e:
        logging.error(f"[致命错误] 加载 API 密钥时发生未知错误: {e}")
        sys.exit(1) # 退出程序

# [!] 全局变量：在脚本开始时加载 API 密钥
API_KEYS = load_api_keys(API_KEYS_FILE_PATH)

if not API_KEYS:
    logging.error("[致命错误] API 密钥未能成功加载，程序无法继续。")
    sys.exit(1)

# [!] V6 变更：API 密钥管理器
# (在脚本运行时在内存中跟踪状态)
# [!] V7.3 变更：'consecutive_failures' 重命名为 'consecutive_quota_failures'
MANAGED_API_KEYS = [
    {"key": key_str, "consecutive_quota_failures": 0, "is_active": True} 
    for key_str in API_KEYS
]
current_key_index = 0 # 用于轮换 API 密钥的全局索引

# =================================================================================
# --- [!] API 密钥管理器函数 (V6 新增) ---
# =================================================================================

def get_next_active_key_info() -> dict | None:
    """
    从管理器中获取下一个"活跃"的 API 密钥信息（用于轮换）。
    这会遍历所有密钥，找到下一个可用的。
    Returns:
        dict: {"index": 密钥索引, "key": 密钥字符串}
        None: 如果所有密钥都已被禁用
    """
    global current_key_index
    
    # 循环检查所有密钥，最多检查 N 次 (N=密钥总数)
    # 这是一个"环形"查找
    start_index = current_key_index
    for i in range(len(MANAGED_API_KEYS)):
        key_index = (start_index + i) % len(MANAGED_API_KEYS)
        key_obj = MANAGED_API_KEYS[key_index]
        
        if key_obj["is_active"]:
            # 找到了一个活跃的密钥
            # 将"下一个"索引设置为这个活跃密钥的下一个，以便下次轮换
            current_key_index = (key_index + 1) % len(MANAGED_API_KEYS)
            return {"index": key_index, "key": key_obj["key"]}
    
    # 如果循环结束都没有找到活跃密钥
    logging.warning("[API 密钥] 警告：在管理器中未找到任何活跃的 API 密钥。")
    return None

# [!] V7.3 变更：更新函数以处理不同的失败类型
# [!] V8.0 变更：新增 'forbidden' (403) 错误类型
def update_key_status(key_index: int, failure_type: str | None):
    """
    根据 API 调用的结果（失败类型）更新密钥的状态。
    failure_type: 'quota' (429), 'forbidden' (403), 'other' (其他错误), or None (成功)
    """
    key_obj = MANAGED_API_KEYS[key_index]
    
    # 如果密钥已经被禁用了，就不要再更新它了
    if not key_obj["is_active"]:
        return

    if failure_type == 'quota':
        key_obj["consecutive_quota_failures"] += 1
        logging.warning(f"[API 密钥] ...{key_obj['key'][-4:]} 连续 QUOTA 失败 {key_obj['consecutive_quota_failures']}/{API_KEY_MAX_QUOTA_FAILURES} 次。")
        
        if key_obj["consecutive_quota_failures"] >= API_KEY_MAX_QUOTA_FAILURES:
            key_obj["is_active"] = False
            logging.error(f"[API 密钥] ...{key_obj['key'][-4:]} 已连续 QUOTA 失败 {API_KEY_MAX_QUOTA_FAILURES} 次，已将其禁用！")
    
    # [!] V8.0 新增：处理 403 Forbidden 错误
    elif failure_type == 'forbidden':
        key_obj["is_active"] = False
        # [!] V8.0: 立即禁用，并重置 quota 计数（因为状态已变为 "非活跃"）
        key_obj["consecutive_quota_failures"] = 0 
        logging.error(f"[API 密钥] ...{key_obj['key'][-4:]} 返回 403 Forbidden (密钥不可用)，已将其立即禁用！")

    elif failure_type == 'other':
        # 其他失败（如超时、500错误），我们不禁用，但重置 QUOTA 计数
        # 因为连续 QUOTA 失败的链条被打破了
        if key_obj["consecutive_quota_failures"] > 0:
            key_obj["consecutive_quota_failures"] = 0
            logging.info(f"[API 密钥] ...{key_obj['key'][-4:]} 发生其他错误，重置其 QUOTA 失败计数。")
    
    else: # 成功 (failure_type is None)
        # 成功了！重置计数器
        if key_obj["consecutive_quota_failures"] > 0:
            key_obj["consecutive_quota_failures"] = 0
            logging.info(f"[API 密钥] ...{key_obj['key'][-4:]} 运行成功，重置其 QUOTA 失败计数。")

# =================================================================================
# --- 状态管理 (State Management) ---
# =================================================================================

class ProgressTracker:
    """
    用于跟踪进度的类，替代 GAS 的 PropertiesService。
    Class to track progress, replacing GAS PropertiesService.
    """
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """加载配置文件，如果不存在则创建。"""
        if not os.path.exists(self.config_path):
            logging.warning(f"未找到配置文件 {self.config_path}，将创建新文件。")
            return {"start_time": None, "total_processed": 0}
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error(f"配置文件 {self.config_path} 损坏，将重置。")
            return {"start_time": None, "total_processed": 0}

    def _save_config(self):
        """保存当前配置到文件。"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logging.error(f"无法写入配置文件 {self.config_path}: {e}")

    def get_property(self, key: str) -> any:
        """获取配置项。"""
        return self.config.get(key)

    def set_property(self, key: str, value: any):
        """设置配置项并立即保存。"""
        self.config[key] = value
        self._save_config()

    def delete_property(self, key: str):
        """删除配置项并立即保存。"""
        if key in self.config:
            del self.config[key]
            self._save_config()

    def start_timer_if_not_set(self):
        """如果计时未开始，则设置开始时间。"""
        if not self.get_property("start_time"):
            self.set_property("start_time", datetime.now().isoformat())

    def increment_processed(self, count: int):
        """增加已处理的总数。"""
        current_total = self.get_property("total_processed") or 0
        self.set_property("total_processed", current_total + count)

# =================================================================================
# --- Excel 辅助函数 (Excel Helper Functions) ---
# =================================================================================

def get_col_index(col_letter: str) -> int:
    """将 Excel 列字母（如 'J'）转换为数字索引（从 1 开始）。"""
    col_index = 0
    for char in col_letter.upper():
        col_index = col_index * 26 + (ord(char) - ord('A') + 1)
    return col_index

def get_excel_data(file_path: str, sheet_name: str) -> tuple:
    """
    加载 Excel 工作簿和工作表。
    返回 (workbook, worksheet, last_row)
    """
    try:
        wb = load_workbook(file_path)
        if sheet_name not in wb.sheetnames:
            logging.error(f"[错误] 在 {file_path} 中找不到工作表: {sheet_name}")
            return None, None, 0
        ws = wb[sheet_name]
        last_row = ws.max_row
        return wb, ws, last_row
    except FileNotFoundError:
        logging.error(f"[错误] Excel 文件未找到: {file_path}")
        return None, None, 0
    except Exception as e:
        logging.error(f"[错误] 加载 Excel 文件时出错: {e}")
        return None, None, 0

def clean_header(header: str) -> str:
    """清理表头字符串，用于 JSON 键。"""
    if not header or not isinstance(header, str):
        return ''
    return re.sub(r'_+', '_', re.sub(r'[\s/,\(\)]+', '_', header.strip().lower())).strip('_')

def format_cell_value(cell_value) -> str:
    """将单元格值格式化为字符串，处理日期。"""
    if isinstance(cell_value, datetime):
        return cell_value.strftime("%Y-%m-%d")
    return str(cell_value or '').strip()

# =================================================================================
# --- API 请求与响应处理 (API Request & Response) ---
# =================================================================================

def create_gemini_request(context_data: str, model: str, api_key: str, is_json_fix: bool = False) -> tuple:
    """
    创建 Gemini API 请求所需的 URL 和载荷 (payload)。
    [!] context_data 现在是来自 K 列的字符串。
    [!] V7 变更：新增 is_json_fix 参数，用于 JSON 修复模式
    [!] V7.4 变更：maxOutputTokens 调整为 8192 (模型的实际硬上限)
    """
    system_prompt = (
        "你是专业的 JSON 转换助手。严格按照 Schema 生成有效的 JSON。\n\n"
        "【关键要求】\n"
        "1. 输出必须是100%有效的JSON，没有任何语法错误\n"
        "2. 字符串中的所有特殊字符必须正确转义：换行符用\\n，双引号用\\\"\n"
        "3. 不要在JSON中包含真实的换行符\n"
        "4. 不要添加markdown标记\n\n"
        "【数据转换规则】\n"
        "1. 固定值：country='EU', dataSource='EU Cosing'\n"
        "2. 双语字段：所有eng/chs对必须同时填充\n"
        "3. annexType推断：II=Prohibited, III=Restricted, IV=Color, V=Preservative, VI=Sunblock\n"
        "4. identifiedIngredients：收集所有成分，过滤脚注(1)(a)(*)\n"
        "5. 所有中文使用简体\n\n"
        "【输出】仅返回JSON对象，确保所有字符串正确转义"
    )
    
    # [!] V7 变更：如果是 JSON 修复调用，添加额外的指令
    if is_json_fix:
        system_prompt += (
            "\n\n【JSON 修复模式 - 极其重要】\n"
            "之前的模型返回了格式错误的 JSON。请特别注意：\n"
            "1. 确保所有换行符都使用 \\n 而不是真实换行\n"
            "2. 确保所有双引号都正确转义\n"
            "3. 不要使用任何控制字符\n"
            "4. 输出必须是100%有效的JSON，可以直接被 JSON.parse() 解析\n"
            "5. 仔细检查字符串的开始和结束引号\n"
            "6. 确保所有逗号、括号、方括号都正确配对\n"
            "7. 特别注意：字符串值中的换行必须用\\n替代，不能是真实换行\n"
            "8. 如果遇到复杂的多行文本，将每个换行都替换为\\n\n"
        )

    # [!] 变更：用户提示现在使用来自 K 列的原始文本
    user_query = f"根据以下文本内容，转换为JSON。重要：确保所有特殊字符正确转义。\n\n{context_data}"

    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": user_query}]
        }],
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": COSMETIC_REGULATION_SCHEMA, # [!] 使用加载的 Schema
            "maxOutputTokens": 65536,  # [!] V7.5 变更：根据要求调整
            "temperature": 0.0,
            "topP": 0.1,
            "topK": 1
        }
    }
    
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'
    
    return url, payload

def clean_json_string(json_text: str) -> str:
    """
    清理 API 返回的 JSON 字符串（去除 markdown 标记等）。
    [!] V7 变更：不再尝试修复，遇到错误直接抛出异常
    """
    if not json_text:
        return json_text
    
    # 移除 ```json ... ``` 标记
    json_text = re.sub(r'^```json\s*|```\s*$', '', json_text.strip())
    
    try:
        # 尝试解析
        json.loads(json_text)
        return json_text
    except json.JSONDecodeError as e:
        logging.warning(f"  [JSON清理] 检测到格式问题: {e}")
        # [!] V7 变更：不尝试修复，直接抛出异常，让上层调用 PRO 模型
        raise ValueError(f"JSON格式无效: {e}")


async def process_row_api_call(
    client: httpx.AsyncClient, 
    context_data: str,
    model: str, 
    api_key: str, 
    is_retry: bool = False,
    is_json_fix: bool = False
) -> dict:
    """
    执行单次 API 调用（带重试逻辑）。
    [!] V7.3 变更：新增 quota_error 状态
    [!] V7.4 变更：新增 max_tokens_error 状态
    [!] V8.0 变更：新增 forbidden_error 状态
    """
    url, payload = create_gemini_request(context_data, model, api_key, is_json_fix)
    
    for attempt in range(API_MAX_RETRIES):
        try:
            response = await client.post(
                url, 
                json=payload, 
                timeout=API_TIMEOUT_SEC
            )
            response.raise_for_status() # 对 4xx/5xx 错误抛出异常
            
            # 成功
            result = response.json()
            
            # [!] V7.2 新增：检查 finishReason
            finish_reason = result.get("candidates", [{}])[0].get("finishReason")
            
            # [!] V7.2 新增：处理 MAX_TOKENS 情况
            # [!] V7.4 变更：检测到 MAX_TOKENS 时，立即返回特定状态
            if finish_reason == "MAX_TOKENS":
                error_msg = "输出超过最大token限制 (MAX_TOKENS)，内容被截断"
                logging.error(f"  [API 调试] {error_msg}")
                logging.error(f"  [API 调试] 使用的 tokens: {result.get('usageMetadata', {})}")
                # [!] V7.4 变更：立即返回，不重试
                return {"status": "max_tokens_error", "message": error_msg, "model": model}
            
            # [!] V7.2 新增：检查是否为安全阻断（移到前面）
            if finish_reason == "SAFETY":
                error_msg = "响应被安全设置阻断 (SAFETY)"
                logging.error(f"  [API 调试] {error_msg}")
                raise ValueError(error_msg)
            
            # 提取响应文本
            json_text = None
            try:
                json_text = result["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError, TypeError) as e:
                logging.error(f"  [API 调试] 无法从 API 响应中提取 'text': {e}")
                logging.error(f"  [API 调试] 完整的 API 响应: {json.dumps(result, ensure_ascii=False)}")
                
                # [!] V7.2 新增：更详细的错误信息
                if finish_reason:
                    error_msg = f"API 响应结构异常 (finishReason: {finish_reason})"
                else:
                    error_msg = "API 响应结构异常，无法提取文本内容"
                raise ValueError(error_msg)

            if not json_text:
                raise ValueError("响应内容为空 (Empty response text)")
            
            # [!] V7.1 变更：直接尝试清理和验证，JSON错误立即返回
            try:
                cleaned_json = clean_json_string(json_text)
                json.loads(cleaned_json)  # 验证清理后的 JSON 是否有效
            except (json.JSONDecodeError, ValueError) as json_err:
                # [!] V7.1 变更：JSON 格式错误，直接返回 json_error 状态，不重试
                error_msg = f"JSON_FORMAT_ERROR: {json_err}"
                logging.warning(f"  [API] JSON 格式错误（不重试）: {json_err}")
                return {"status": "json_error", "message": error_msg, "model": model}
            
            return {
                "status": "success", 
                "json": cleaned_json, 
                "model": model, 
                "retry": is_retry, 
                "json_fix": is_json_fix
            }

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            
            # [!] V7.3 变更：检查 QUOTA 错误 (429)
            if e.response.status_code == 429:
                logging.warning(f"  [API] 第 {attempt + 1} 次尝试失败 (QUOTA_EXCEEDED): {error_msg}")
                # 这是配额错误，立即返回特定状态，不再重试
                return {"status": "quota_error", "message": error_msg, "model": model}

            # [!] V8.0 新增：检查 FORBIDDEN 错误 (403)
            elif e.response.status_code == 403:
                logging.error(f"  [API] 第 {attempt + 1} 次尝试失败 (FORBIDDEN): {error_msg}")
                # 这是密钥不可用错误，立即返回特定状态，不再重试
                return {"status": "forbidden_error", "message": error_msg, "model": model}

            logging.warning(f"  [API] 第 {attempt + 1} 次尝试失败 (HTTP 错误): {error_msg}")

        except httpx.RequestError as e:
            error_msg = f"请求错误: {type(e).__name__}"
            logging.warning(f"  [API] 第 {attempt + 1} 次尝试失败 ({error_msg})")
        # [!] V7.2 修复：正确捕获超时异常
        except (httpx.TimeoutException, httpx.ReadTimeout, httpx.WriteTimeout, httpx.ConnectTimeout) as e:
            error_msg = f"请求超时: {type(e).__name__}"
            logging.warning(f"  [API] 第 {attempt + 1} 次尝试失败 ({error_msg})")
        except ValueError as e:
            error_msg = str(e)
            # 对于非 JSON 格式错误的 ValueError（如安全阻断、MAX_TOKENS），继续重试
            logging.warning(f"  [API] 第 {attempt + 1} 次尝试失败: {error_msg}")
        except (TypeError, KeyError) as e:
            error_msg = f"响应解析失败: {e}"
            logging.warning(f"  [API] 第 {attempt + 1} 次尝试失败 ({error_msg})")
        
        if attempt < API_MAX_RETRIES - 1:
            await asyncio.sleep(2 ** attempt) # 指数退避
        
    return {"status": "error", "message": error_msg, "model": model}


async def handle_row_processing(
    client: httpx.AsyncClient, 
    row_info: dict, 
    key_index: int,
    key_string: str
) -> dict:
    """
    处理单行数据，包括初始尝试和失败后的重试逻辑。
    [!] V7.3 变更：处理 quota_error，返回 failure_type
    [!] V7.4 变更：处理 max_tokens_error，立即失败
    [!] V8.0 变更：处理 forbidden_error，立即失败
    返回一个字典，包含行结果 和 调用的密钥信息。
    """
    row_num = row_info['row_number']
    context_data = row_info['context_data']
    model_to_use = row_info['model_used']

    # 检查 K 列内容是否为空
    if not context_data:
        logging.warning(f"[失败] 第 {row_num} 行 K 列为空，无法处理。")
        final_row_result = {
            "row_number": row_num, 
            "status": "error", 
            "message": "Error: K 列为空 (K Column is empty)"
        }
        # [!] V7.3 变更：返回 failure_type: None (K列为空不计入KEY失败)
        return {"row_result": final_row_result, "key_index": key_index, "failure_type": None}

    retry_key = API_KEYS[0]  # PRO 模型统一使用第一个密钥
    pro_attempt_count = 0    # [!] V7.1 新增：PRO 模型尝试计数器

    # 1. 初始尝试 (使用轮换的密钥)
    result = await process_row_api_call(client, context_data, model_to_use, key_string)
    
    # [!] V7.3 变更：确定初始失败类型
    # [!] V8.0 变更：新增 'forbidden'
    if result['status'] == 'quota_error':
        initial_failure_type = 'quota'
    # [!] V8.0 新增
    elif result['status'] == 'forbidden_error':
        initial_failure_type = 'forbidden'
    elif result['status'] == 'error':
        initial_failure_type = 'other'
    # [!] V7.4 变更：max_tokens 也算作 'other' 失败 (因为它不是配额问题)
    elif result['status'] == 'max_tokens_error':
        initial_failure_type = 'other' # [!] V7.4 变更
    else: # 'success' or 'json_error'
        initial_failure_type = None
    
    # [!] V7 新增：如果是 JSON 格式错误，使用 PRO 模型重新生成
    if result['status'] == 'json_error':
        pro_attempt_count += 1
        logging.warning(
            f"[JSON修复 {pro_attempt_count}/{MAX_PRO_ATTEMPTS}] 第 {row_num} 行 "
            f"({model_to_use} 返回了无效JSON)，使用 {RETRY_MODEL} 重新生成..."
        )
        
        json_fix_result = await process_row_api_call(
            client, 
            context_data, 
            RETRY_MODEL, 
            retry_key, 
            is_retry=True,
            is_json_fix=True
        )
        
        if json_fix_result['status'] == 'success':
            logging.info(f"[成功] 第 {row_num} 行 ({RETRY_MODEL} JSON修复成功)")
            final_row_result = {"row_number": row_num, **json_fix_result}
            # [!] V7.3 变更：返回 failure_type: None (初始调用是 json_error)
            return {"row_result": final_row_result, "key_index": key_index, "failure_type": None}
        else:
            # [!] V7.1 变更：第一次 JSON 修复失败
            logging.error(
                f"[失败] 第 {row_num} 行 "
                f"({RETRY_MODEL} 第 {pro_attempt_count} 次尝试失败: "
                f"{json_fix_result.get('message', 'Unknown error')})"
            )
            
            # [!] V7.1 变更：检查是否达到最大尝试次数
            if pro_attempt_count >= MAX_PRO_ATTEMPTS:
                logging.error(
                    f"[跳过] 第 {row_num} 行 PRO 模型已尝试 {MAX_PRO_ATTEMPTS} 次，标记失败并跳过。"
                )
                final_row_result = {
                    "row_number": row_num, 
                    "status": "error", 
                    "message": f"Error: PRO模型尝试{MAX_PRO_ATTEMPTS}次均失败"
                }
                # [!] V7.3 变更：返回 failure_type: None (初始调用是 json_error)
                return {"row_result": final_row_result, "key_index": key_index, "failure_type": None}
    
    if result['status'] == 'success':
        # 初始调用成功
        logging.info(f"[成功] 第 {row_num} 行 ({result['model']})")
        final_row_result = {"row_number": row_num, **result}
        # [!] V7.3 变更：返回 failure_type: None
        return {"row_result": final_row_result, "key_index": key_index, "failure_type": None}

    # [!] V7.3 变更：如果初始调用是 QUOTA 错误，不要重试，立即失败
    if initial_failure_type == 'quota':
        logging.error(
            f"[跳过] 第 {row_num} 行 "
            f"({model_to_use} 失败: QUOTA_EXCEEDED)，标记失败并跳过。"
        )
        final_row_result = {
            "row_number": row_num, 
            "status": "error", 
            "message": f"Error: {result['message']}"
        }
        # [!] V7.3 变更：返回 failure_type: 'quota'
        return {"row_result": final_row_result, "key_index": key_index, "failure_type": "quota"}

    # [!] V8.0 新增：如果初始调用是 403 错误，不要重试，立即失败
    if initial_failure_type == 'forbidden':
        logging.error(
            f"[跳过] 第 {row_num} 行 "
            f"({model_to_use} 失败: 403 FORBIDDEN)，标记失败并跳过。"
        )
        final_row_result = {
            "row_number": row_num, 
            "status": "error", 
            "message": f"Error: {result['message']}"
        }
        # [!] V8.0 变更：返回 failure_type: 'forbidden'
        return {"row_result": final_row_result, "key_index": key_index, "failure_type": "forbidden"}

    # [!] V7.4 变更：如果初始调用是 MAX_TOKENS 错误，不要重试，立即失败
    if result['status'] == 'max_tokens_error':
        logging.error(
            f"[跳过] 第 {row_num} 行 "
            f"({model_to_use} 失败: MAX_TOKENS)，标记失败并跳过。"
        )
        final_row_result = {
            "row_number": row_num, 
            "status": "error", 
            "message": f"Error: {result['message']}"
        }
        # [!] V7.4 变更：返回 'other' 类型的失败
        return {"row_result": final_row_result, "key_index": key_index, "failure_type": "other"}


    # 2. 初始调用失败（非 JSON, 非 QUOTA, 非 MAX_TOKENS, 非 FORBIDDEN 错误），记录并准备重试
    pro_attempt_count += 1
    logging.warning(
        f"[重试 {pro_attempt_count}/{MAX_PRO_ATTEMPTS}] 第 {row_num} 行 "
        f"({model_to_use} 失败: {result['message']})，使用 {RETRY_MODEL} 重试..."
    )
    
    retry_result = await process_row_api_call(
        client, 
        context_data, 
        RETRY_MODEL, 
        retry_key, 
        is_retry=True
    )
    
    # [!] V7 新增：重试后如果还是 JSON 错误，再尝试一次 JSON 修复
    if retry_result['status'] == 'json_error':
        pro_attempt_count += 1
        
        # [!] V7.1 变更：检查是否已达到最大尝试次数
        if pro_attempt_count > MAX_PRO_ATTEMPTS:
            logging.error(
                f"[跳过] 第 {row_num} 行 PRO 模型已尝试 {MAX_PRO_ATTEMPTS} 次（仍返回无效JSON），"
                f"标记失败并跳过。"
            )
            final_row_result = {
                "row_number": row_num, 
                "status": "error", 
                "message": f"Error: PRO模型尝试{MAX_PRO_ATTEMPTS}次仍返回无效JSON"
            }
            # [!] V7.3 变更：返回 initial_failure_type
            return {"row_result": final_row_result, "key_index": key_index, "failure_type": initial_failure_type}
        
        logging.warning(
            f"[JSON修复 {pro_attempt_count}/{MAX_PRO_ATTEMPTS}] 第 {row_num} 行 "
            f"(重试后仍返回无效JSON)，最后一次尝试..."
        )
        
        json_fix_result = await process_row_api_call(
            client, 
            context_data, 
            RETRY_MODEL, 
            retry_key, 
            is_retry=True,
            is_json_fix=True
        )
        
        if json_fix_result['status'] == 'success':
            logging.info(f"[成功] 第 {row_num} 行 ({RETRY_MODEL} 最终JSON修复成功)")
            final_row_result = {"row_number": row_num, **json_fix_result}
        else:
            # [!] V7.1 变更：所有尝试均失败
            logging.error(
                f"[跳过] 第 {row_num} 行 PRO 模型尝试 {pro_attempt_count} 次均失败，标记失败并跳过。"
            )
            final_row_result = {
                "row_number": row_num, 
                "status": "error", 
                "message": f"Error: PRO模型尝试{pro_attempt_count}次均失败"
            }
        # [!] V7.3 变更：返回 initial_failure_type
        return {"row_result": final_row_result, "key_index": key_index, "failure_type": initial_failure_type}
    
    if retry_result['status'] == 'success':
        # 重试成功
        logging.info(f"[成功] 第 {row_num} 行 ({retry_result['model']} 重试成功)")
        final_row_result = {"row_number": row_num, **retry_result}
    else:
        # [!] V7.1 变更：重试失败，标记并跳过
        logging.error(
            f"[跳过] 第 {row_num} 行 ({RETRY_MODEL} 尝试 {pro_attempt_count} 次失败: "
            f"{retry_result['message']})，标记失败并跳过。"
        )
        final_row_result = {
            "row_number": row_num, 
            "status": "error", 
            "message": f"Error: {retry_result['message']}"
        }

    # [!] V7.3 变更：返回 initial_failure_type
    return {"row_result": final_row_result, "key_index": key_index, "failure_type": initial_failure_type}


# =================================================================================
# --- 主处理引擎 (Core Processing Engine) ---
# =================================================================================

async def process_cosing_jsons_async(progress: ProgressTracker):
    """
    核心处理函数 (异步)
    """
    processed_in_this_run = 0
    
    # [!] V6 变更：检查 MANAGED_API_KEYS (虽然 load_api_keys 已经保证了)
    if not MANAGED_API_KEYS:
        logging.error("[错误] API_KEYS 数量不足。")
        return
    # [!] V6 变更：并发级别不能超过密钥总数
    global CONCURRENCY_LEVEL
    if CONCURRENCY_LEVEL > len(MANAGED_API_KEYS):
        logging.warning(
            f"[警告] 并发级别 ({CONCURRENCY_LEVEL}) 高于 API 密钥数量 ({len(MANAGED_API_KEYS)})。"
        )
        logging.warning(f"[警告] 将并发级别限制为 {len(MANAGED_API_KEYS)}。")
        CONCURRENCY_LEVEL = len(MANAGED_API_KEYS)
    
    # 1. 加载 Excel 并查找待处理行
    wb, ws, last_row = get_excel_data(EXCEL_FILE_PATH, SHEET_NAME)
    if not wb or not ws:
        return
        
    num_data_cols = get_col_index(DATA_END_COL_LETTER)
    # [!] 变更：确保读取列包含 K 列
    last_col_to_read = max(num_data_cols, SCCS_OPINION_COL, K_COL, TARGET_COL, STATUS_COL)

    # 扫描待处理行
    pending_rows = []
    total_rows = 0
    # [!] 变更：使用 values_only=True 加速读取
    for i, row in enumerate(ws.iter_rows(
        min_row=DATA_START_ROW, 
        max_row=last_row, 
        max_col=last_col_to_read, 
        values_only=True
    )):
        total_rows += 1
        status = row[STATUS_COL - 1] # M列 (索引-1)
        a_column_value = row[0]      # A列 (索引-1)
        
        # 只处理M列为空且A列有值的行
        if (not status or str(status).strip() == '') and \
           (a_column_value and str(a_column_value).strip() != ''):
            pending_rows.append({
                "row_number": DATA_START_ROW + i,
                "row_data": row # row_data 是包含所有列的元组
            })

    logging.info('============================================================')
    logging.info('[启动] 扫描完成')
    logging.info(f'总行数: {total_rows} (在 {last_row} 行中)')
    logging.info(f'待处理: {len(pending_rows)} 行')
    logging.info(f'并发级别: {CONCURRENCY_LEVEL}')
    logging.info('============================================================')

    if not pending_rows:
        logging.info('[完成] 没有待处理的行！')
        log_final_stats(progress, total_rows)
        return

    # 确保计时器已启动
    progress.start_timer_if_not_set()

    # 2. 批量处理
    processed_index = 0
    consecutive_failure_count = 0 # [!] 全局连续失败计数器
    all_keys_disabled = False     # [!] V6 变更：标记是否所有key都失效
    
    async with httpx.AsyncClient() as client:
        
        while (processed_index < len(pending_rows)) and \
              (consecutive_failure_count < MAX_CONSECUTIVE_FAILURES) and \
              (not all_keys_disabled):
            
            batch_size = min(CONCURRENCY_LEVEL, len(pending_rows) - processed_index)
            tasks = []
            
            # [!] V6 变更：在此批次中使用的密钥（索引）
            keys_used_in_batch = set()
            
            for i in range(batch_size):
                # [!] V6 变更：从管理器获取下一个活跃密钥
                key_info = get_next_active_key_info()
                
                if key_info is None:
                    # [!] V6 变更：没有可用的密钥了
                    logging.error("[!] 停止运行：所有 API 密钥均已失败，没有可用的密钥。")
                    all_keys_disabled = True
                    break # 中断此批次的任务创建
                
                key_to_use_index = key_info["index"]
                
                # [!] V6 变更：确保在此批次中不会重复使用同一个密钥
                if key_to_use_index in keys_used_in_batch:
                    # 我们已经绕了一圈，又回到了这个密钥
                    # 这意味着我们活跃的密钥少于 CONCURRENCY_LEVEL
                    # 停止创建任务，以较小的批次运行
                    logging.info(
                        f"[并发] 活跃密钥 ({len(keys_used_in_batch)}) "
                        f"少于并发级别 ({CONCURRENCY_LEVEL})，减小批次大小。"
                    )
                    break 
                
                keys_used_in_batch.add(key_to_use_index)
                key_to_use_string = key_info["key"]

                pending_row = pending_rows[processed_index + i]
                row_data = pending_row['row_data']
                
                # 动态模型选择 (基于 H 列)
                sccs_opinion = row_data[SCCS_OPINION_COL - 1]
                model_to_use = MODEL_ADVANCED if \
                    (sccs_opinion and str(sccs_opinion).strip() != '') else MODEL_DEFAULT
                
                # [!] 变更：从 K 列 (索引 K_COL - 1) 获取输入
                k_col_value = row_data[K_COL - 1] 
                context_data_str = format_cell_value(k_col_value)
                
                row_info = {
                    "row_number": pending_row['row_number'],
                    "model_used": model_to_use,
                    "context_data": context_data_str # [!] 传递字符串
                }
                
                # 创建异步任务
                tasks.append(
                    handle_row_processing(
                        client, 
                        row_info, 
                        key_to_use_index, 
                        key_to_use_string
                    )
                )

            if not tasks and all_keys_disabled:
                # 如果没有任务被创建，并且是因为所有 key 都失效了，则跳出主循环
                break
            elif not tasks:
                # 如果因为其他原因（例如 pending_rows 耗尽）导致没有任务
                continue

            current_batch_size = len(tasks)
            logging.info(
                f'[并发] 处理 {current_batch_size} 个请求 '
                f'(Excel 行 {pending_rows[processed_index]["row_number"]} 到 '
                f'{pending_rows[processed_index + current_batch_size - 1]["row_number"]})...'
            )
            
            # 执行并发请求
            results = await asyncio.gather(*tasks)
            
            # 3. 处理结果并写入 Excel
            batch_success_count = 0
            
            last_failed_row = 0
            for result_package in results:
                # [!] V7.3 变更：拆包
                row_result = result_package["row_result"]
                key_index = result_package["key_index"]
                failure_type = result_package["failure_type"] # V7.3: key_failed -> failure_type

                # [!] V7.3 变更：更新密钥状态
                # (K列为空导致的"失败" (failure_type=None) 不会计入密钥失败)
                update_key_status(key_index, failure_type)
                
                row_to_update = row_result['row_number']
                if row_result['status'] == 'success':
                    # L列 (JSON), M列 (Status)
                    ws.cell(row=row_to_update, column=TARGET_COL, value=row_result['json'])
                    
                    # [!] V7 变更：状态信息更详细
                    if row_result.get('json_fix'):
                        status_msg = "Processed (JSON Fix)"
                    elif row_result.get('retry'):
                        status_msg = "Processed (Retry)"
                    else:
                        status_msg = "Processed"
                    
                    ws.cell(row=row_to_update, column=STATUS_COL, value=status_msg)
                    batch_success_count += 1
                    consecutive_failure_count = 0 # [!] 成功，重置全局计数器
                else:
                    # M列 (Status)
                    ws.cell(row=row_to_update, column=STATUS_COL, value=row_result['message'])
                    consecutive_failure_count += 1 # [!] 失败，增加全局计数器
                    last_failed_row = row_to_update
                    logging.warning(
                        f"[!] 全局连续失败 {consecutive_failure_count}/{MAX_CONSECUTIVE_FAILURES} 次 "
                        f"(在第 {row_to_update} 行)。"
                    )
                
                if consecutive_failure_count >= MAX_CONSECUTIVE_FAILURES:
                    logging.error(
                        f"[!] 连续 {MAX_CONSECUTIVE_FAILURES} 次处理失败，停止当前批处理。"
                    )
                    break # 中断此批次的结果循环
            
            # 尝试保存
            try:
                wb.save(EXCEL_FILE_PATH)
                logging.info(
                    f"[保存] 批处理结果已保存到 {EXCEL_FILE_PATH} "
                    f"({batch_success_count}/{len(results)} 成功)"
                )
            except IOError as e:
                logging.error(f"[致命错误] 无法保存 Excel 文件: {e}")
                logging.error("请关闭 Excel 文件后重试！")
                return # 无法保存，终止运行

            processed_in_this_run += batch_success_count
            processed_index += current_batch_size # [!] V6 变更：索引前进
            
            if (processed_index < len(pending_rows)) and \
               (consecutive_failure_count < MAX_CONSECUTIVE_FAILURES) and \
               (not all_keys_disabled):
                
                logging.info(f'[延迟] 等待 {BATCH_DELAY_SEC} 秒...')
                await asyncio.sleep(BATCH_DELAY_SEC) # [!] V6 变更：批次间延迟

    # 4. 运行结束
    if processed_in_this_run > 0:
        progress.increment_processed(processed_in_this_run)

    if processed_index >= len(pending_rows):
        logging.info('[完成] 所有待处理行已处理完毕！')
        log_final_stats(progress, total_rows)
    elif consecutive_failure_count >= MAX_CONSECUTIVE_FAILURES:
        logging.error('============================================================')
        logging.error(f'[!] 停止运行：全局连续 {consecutive_failure_count} 次处理失败。')
        logging.error(f'[!] 请检查 Excel 第 {last_failed_row} 行附近的错误信息、您的网络连接或 API 密钥。')
        logging.error('============================================================')
    elif all_keys_disabled:
        logging.error('============================================================')
        logging.error(
            f'[!] 停止运行：所有 API 密钥均因失败 (403 或 连续 429) 而被禁用。'
        )
        logging.error(f'[!] 请检查您的 API 密钥配额或网络问题。')
        logging.error('============================================================')
    else:
        logging.info(f'[暂停] 运行被中断。')
        logging.info(f'总计已处理 (所有运行): {progress.get_property("total_processed")}')

# =================================================================================
# --- 辅助操作 (Utility Operations) ---
# =================================================================================

def check_progress():
    """检查当前 Excel 文件的处理进度。"""
    wb, ws, last_row = get_excel_data(EXCEL_FILE_PATH, SHEET_NAME)
    if not wb or not ws:
        return

    total_rows = 0
    processed_count = 0
    error_count = 0
    pending_count = 0

    for row_idx, row in enumerate(ws.iter_rows(
        min_row=DATA_START_ROW, 
        max_row=last_row, 
        max_col=STATUS_COL
    )):
        # 只计算 A 列有值的行
        a_val = row[0].value
        if not a_val or str(a_val).strip() == '':
            continue

        total_rows += 1
        status_cell = row[STATUS_COL - 1] # M列
        status = str(status_cell.value or '').strip()
        
        if status in ["Processed", "Processed (Retry)", "Processed (JSON Fix)"]:
            processed_count += 1
        elif status.startswith("Error:"):
            error_count += 1
        elif status == '':
            pending_count += 1
        
    progress_percent = (processed_count / total_rows * 100) if total_rows > 0 else 0
    
    progress = ProgressTracker(CONFIG_FILE_PATH)
    start_time = progress.get_property('start_time')
    
    logging.info('============================================================')
    logging.info('当前处理进度')
    logging.info('============================================================')
    logging.info(f'总行数 (有A列数据): {total_rows}')
    logging.info(f'已处理: {processed_count} 行 ({progress_percent:.2f}%)')
    logging.info(f'错误: {error_count} 行')
    logging.info(f'待处理: {pending_count} 行')
    logging.info(f'开始时间: {start_time or "未开始"}')
    logging.info('============================================================')

def reset_error_rows():
    """重置所有错误行，以便重新处理。"""
    wb, ws, last_row = get_excel_data(EXCEL_FILE_PATH, SHEET_NAME)
    if not wb or not ws:
        return

    reset_count = 0
    for row_idx in range(DATA_START_ROW, last_row + 1):
        status_cell = ws.cell(row=row_idx, column=STATUS_COL)
        status = str(status_cell.value or '').strip()
        
        if status.startswith("Error:"):
            status_cell.value = None # 清空 M 列
            ws.cell(row=row_idx, column=TARGET_COL).value = None # 清空 L 列
            reset_count += 1
    
    try:
        wb.save(EXCEL_FILE_PATH)
        logging.info(f'[重置] 已清除 {reset_count} 个错误行的状态，将在下次运行时重新处理。')
    except IOError as e:
        logging.error(f"[错误] 无法保存 Excel 文件: {e}。请关闭文件后重试。")

def list_error_rows():
    """列出所有出错的行号和错误信息。"""
    wb, ws, last_row = get_excel_data(EXCEL_FILE_PATH, SHEET_NAME)
    if not wb or not ws:
        return

    logging.info('============================================================')
    logging.info('错误行列表')
    logging.info('============================================================')
    
    error_count = 0
    for row_idx in range(DATA_START_ROW, last_row + 1):
        status = str(ws.cell(row=row_idx, column=STATUS_COL).value or '').strip()
        if status.startswith("Error:"):
            logging.info(f'行 {row_idx}: {status}')
            error_count += 1
            
    logging.info('============================================================')
    logging.info(f'总计: {error_count} 个错误行')
    logging.info('============================================================')

def log_final_stats(progress: ProgressTracker, total_rows: int):
    """记录处理完成后的最终统计数据。"""
    start_time_iso = progress.get_property('start_time')
    total_processed = progress.get_property('total_processed') or 0
    
    if start_time_iso:
        start_time = datetime.fromisoformat(start_time_iso)
        end_time = datetime.now()
        duration_sec = (end_time - start_time).total_seconds()
        duration_min = duration_sec / 60
        duration_hr = duration_sec / 3600
        
        avg_speed = (total_processed / duration_min) if duration_min > 0 else 0
        
        logging.info('============================================================')
        logging.info('处理完成统计')
        logging.info('============================================================')
        logging.info(f'总行数: {total_rows} 行')
        logging.info(f'成功处理: {total_processed} 行')
        logging.info(f'总耗时: {duration_hr:.2f} 小时 ({duration_min:.1f} 分钟)')
        logging.info(f'平均速度: {avg_speed:.1f} 行/分钟')
        logging.info('============================================================')
    
    # 清理配置文件
    progress.delete_property('start_time')
    progress.delete_property('total_processed')

async def test_single_row(row_number: int):
    """测试单行逻辑，不写入文件。"""
    logging.info(f'[测试] 开始测试第 {row_number} 行...')
    wb, ws, last_row = get_excel_data(EXCEL_FILE_PATH, SHEET_NAME)
    if not wb or not ws:
        return
    if row_number < DATA_START_ROW or row_number > last_row:
        logging.error(f"[错误] 行号 {row_number} 超出范围 ({DATA_START_ROW} - {last_row})。")
        return

    # [!] 变更：确保读取列包含 K 列和 SCCS (H) 列
    max_col_to_read = max(get_col_index(DATA_END_COL_LETTER), K_COL, SCCS_OPINION_COL)
    
    # 读取指定行数据
    row_data = list(ws.iter_rows(
        min_row=row_number, 
        max_row=row_number, 
        max_col=max_col_to_read, 
        values_only=True
    ))[0]
    
    # [!] 变更：从 K 列 (索引 K_COL - 1) 获取输入
    k_col_value = row_data[K_COL - 1] 
    context_data_str = format_cell_value(k_col_value)

    if not context_data_str:
        logging.error(f"[测试失败] 第 {row_number} 行 K 列为空。")
        return

    logging.info('[原始数据 (来自 K 列)]')
    logging.info(context_data_str)

    # 动态模型选择 (基于 H 列)
    sccs_opinion = row_data[SCCS_OPINION_COL - 1]
    model_to_use = MODEL_ADVANCED if \
        (sccs_opinion and str(sccs_opinion).strip() != '') else MODEL_DEFAULT
    key_to_use = API_KEYS[0]
    
    logging.info(f"[API] 使用模型: {model_to_use}")

    async with httpx.AsyncClient() as client:
        result = await process_row_api_call(
            client, 
            context_data_str, # [!] 传递字符串
            model_to_use, 
            key_to_use
        )
    
    if result['status'] == 'success':
        logging.info('[测试成功] API 返回有效 JSON:')
        logging.info(result['json'])
    elif result['status'] == 'json_error':
        logging.warning('[测试] 初始调用返回无效 JSON，尝试使用 PRO 模型修复...')
        async with httpx.AsyncClient() as client:
            fix_result = await process_row_api_call(
                client,
                context_data_str,
                RETRY_MODEL,
                key_to_use,
                is_retry=True,
                is_json_fix=True
            )
        if fix_result['status'] == 'success':
            logging.info('[测试成功] PRO 模型返回有效 JSON:')
            logging.info(fix_result['json'])
        else:
            logging.error('[测试失败] PRO 模型也无法生成有效 JSON:')
            logging.error(fix_result['message'])
    elif result['status'] == 'quota_error':
        logging.error('[测试失败] API 调用出错 (QUOTA_EXCEEDED):')
        logging.error(result['message'])

    # [!] V8.0 新增
    elif result['status'] == 'forbidden_error':
        logging.error('[测试失败] API 调用出错 (403 FORBIDDEN):')
        logging.error(result['message'])
        
    # [!] V7.4 变更：在测试中也报告 MAX_TOKENS
    elif result['status'] == 'max_tokens_error':
        logging.error('[测试失败] API 调用出错 (MAX_TOKENS):')
        logging.error(result['message'])
    else:
        logging.error('[测试失败] API 调用出错:')
        logging.error(result['message'])

# =================================================================================
# --- 启动入口 (Main Entry Point) ---
# =================================================================================

def main():
    """
    主函数，解析命令行参数并执行相应操作。
    """
    # API 密钥检查已在顶层 load_api_keys() 中自动完成。
    
    # 命令行参数解析
    parser = argparse.ArgumentParser(description="COSING JSON 批量转换器 (Python 版)")
    parser.add_argument(
        'action', 
        nargs='?', 
        default='process', 
        choices=['process', 'check', 'reset', 'list_errors', 'test'],
        help=(
            "要执行的操作: 'process' (处理数据), 'check' (检查进度), "
            "'reset' (重置错误行), 'list_errors' (列出错误行), 'test' (测试单行)。 "
            "默认: 'process'"
        )
    )
    parser.add_argument(
        '--row', 
        type=int, 
        help="当 action 为 'test' 时，指定要测试的行号。"
    )
    args = parser.parse_args()

    # 根据 action 执行不同功能
    if args.action == 'process':
        progress = ProgressTracker(CONFIG_FILE_PATH)
        asyncio.run(process_cosing_jsons_async(progress))
    
    elif args.action == 'check':
        check_progress()
        
    elif args.action == 'reset':
        reset_error_rows()
        
    elif args.action == 'list_errors':
        list_error_rows()
        
    elif args.action == 'test':
        if not args.row:
            logging.error("[错误] 'test' 操作必须使用 '--row' 参数指定行号。")
            logging.error("示例: python cosing_processor.py test --row 5")
        else:
            asyncio.run(test_single_row(args.row))

if __name__ == "__main__":
    main()