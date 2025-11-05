// =================================================================================
// --- 台湾 (TW) 法规 JSON 批量生成 (GetTWJsons) ---
// 功能：使用 Gemini API，根据 JSON Schema 提取台湾法规工作表数据并进行中英文翻译。
// 模式：高效循环执行（接近 6 分钟） + 无状态断点续传 + 延迟 5 分钟定时触发器。
// 依赖： global.GS 中定义的 API_KEY。
// =================================================================================

// =================================================================================
// --- 台湾 (TW) 常量定义 ---
// =================================================================================

const TW_JSON_WRITE_COL_START = 18;   // R 列 (18)
const TW_JSON_BATCH_SIZE = 10;        // 每次 API 调用处理的行数 (依照要求设为 20)
const TW_TRIGGER_INTERVAL_MINUTES = 5; // 触发器运行间隔 (5 分钟)
const TW_JSON_TRIGGER_INIT_KEY = 'twJsonTriggerInitTime'; // 用于记录触发器初始化时间的属性键
const TW_TRIGGER_DELAY_MS = 120000;   // 延迟 2 分钟 (120,000 毫秒) 建立触发器
// 6分钟的硬性限制。设置为 5分30秒 (330,000 毫秒) 提前退出，避免超时报错。
const TW_MAX_RUN_TIME_MS = 330000; 
const TW_API_BATCH_DELAY_MS = 10000;  // 批次写入后的延迟时间 (30秒)

// =================================================================================
// --- 台湾 (TW) 工作表配置 ---
// =================================================================================

/**
 * 台湾法规工作表配置
 * 定义了每个工作表的标题范围、数据起始行、读取的列范围和对应的法规附件类型。
 */
const TW_SHEET_CONFIG = {
    // 1.) 色素成分
    "色素成分": { 
        headerStart: 1,      // 标题从第 1 行开始
        headerCount: 7,      // 标题共 7 行
        dataStart: 8,        // 数据从第 8 行开始
        cols: "F",           // 读取到 F 列
        annex: "ANNEX_IV"    // Json 页签值
    },
    // 2.) 不允许使用的色素成分
    "不允许使用的色素成分": { 
        headerStart: 1,      // 标题从第 1 行开始
        headerCount: 2,      // 标题共 2 行
        dataStart: 3,        // 数据从第 3 行开始
        cols: "B",           // 读取到 B 列
        annex: "ANNEX_II"    // Json 页签值
    },
    // 3.) 禁止使用成分
    "禁止使用成分": { 
        headerStart: 1,      // 标题从第 1 行开始
        headerCount: 2,      // 标题共 2 行
        dataStart: 3,        // 数据从第 3 行开始
        cols: "C",           // 读取到 C 列
        annex: "ANNEX_II"    // Json 页签值
    },
    // 4.) Preservative
    "Preservative": { 
        headerStart: 1,      // 标题从第 1 行开始
        headerCount: 2,      // 标题共 2 行
        dataStart: 3,        // 数据从第 3 行开始
        cols: "H",           // 读取到 H 列
        annex: "ANNEX_V"     // Json 页签值
    },
    // 5.) Restricted
    "Restricted": { 
        headerStart: 1,      // 标题从第 1 行开始
        headerCount: 2,      // 标题共 2 行
        dataStart: 3,        // 数据从第 3 行开始
        cols: "H",           // 读取到 H 列
        annex: "ANNEX_III"   // Json 页签值
    },
    // 6.) Sunblock
    "Sunblock": { 
        headerStart: 1,      // 标题从第 1 行开始
        headerCount: 2,      // 标题共 2 行
        dataStart: 3,        // 数据从第 3 行开始
        cols: "H",           // 读取到 H 列
        annex: "ANNEX_VI"    // Json 页签值
    }
};

/**
 * 台湾法规工作表名称列表 (从配置中自动生成)
 */
const TW_SOURCE_SHEET_NAMES = Object.keys(TW_SHEET_CONFIG);

// =================================================================================
// --- JSON SCHEMA 定义 (保持结构，用于约束 AI 输出) ---
// =================================================================================

/**
 * 化妆品物质法规 (Cosmetics Regulation) 的统一双语 JSON Schema
 * (此结构被台湾和欧盟的程序共用，以确保数据格式统一)
 */
const COSMETIC_REGULATION_SCHEMA = {
  "title": "Cosmetic Substances Regulation Schema (Bilingual)",
  "description": "Unified bilingual schema for cosmetic substances across Annex II-VI of EU Cosmetics Regulation",
  "type": "object",
  "properties": {
    "annexType": {
      "type": "string",
      "enum": ["ANNEX_II", "ANNEX_III", "ANNEX_IV", "ANNEX_V", "ANNEX_VI"],
      "description": "Type of annex | 附录类型"
    },
    "country": {
      "type": "string",
      "description": "Country or region of regulation (e.g., 'EU', 'TWN') | 法规所属国家或地区"
    },
    "isProhibited": {
      "type": "boolean",
      "description": "Flag to mark this substance as prohibited (e.g., listed in Annex II) | 标记此物质为禁用（例如在附录II中）",
      "default": false
    },
    "referenceNumber": {
      "type": "string",
      "description": "Reference number of the substance entry | 物质条目参考编号"
    },
    "substanceIdentification": {
      "type": "object",
      "description": "Substance identification information | 物质标识信息",
      "properties": {
        "chemicalName": {
          "type": "object",
          "description": "Chemical name / INN / XAN | 化学名称/国际非专利名",
          "properties": {
            "eng": {
              "type": "string",
              "description": "English chemical name"
            },
            "chs": {
              "type": "string",
              "description": "Chinese chemical name | 中文化学名称"
            }
          },
          "required": ["eng"]
        },
        "commonIngredientsName": {
          "type": "object",
          "description": "INCI name (International Nomenclature of Cosmetic Ingredients) | 国际化妆品成分命名",
          "properties": {
            "eng": {
              "type": "string",
              "description": "INCI name (standard)"
            },
            "chs": {
              "type": "string",
              "description": "Chinese common name | 中文通用名称"
            }
          }
        },
        "casNumber": {
          "type": "string",
          "description": "CAS Registry Number | CAS登记号",
          "pattern": "^[0-9]{1,7}-[0-9]{2}-[0-9]$"
        },
        "ecNumber": {
          "type": "string",
          "description": "EC Number (EINECS/ELINCS) | EC编号"
        },
        "colourIndexNumber": {
          "type": "string",
          "description": "Colour Index Number (only for Annex IV) | 色素索引号（仅附录IV）"
        },
        "color": {
          "type": "object",
          "description": "Physical color description (only for Annex IV) | 颜色描述（仅附录IV）",
          "properties": {
            "eng": {
              "type": "string",
              "description": "Color in English"
            },
            "chs": {
              "type": "string",
              "description": "颜色中文描述"
            }
          }
        },
        "iupacName": {
          "type": "string",
          "description": "Chemical/IUPAC Name (international standard) | IUPAC化学名称（国际标准）"
        }
      },
      "required": ["chemicalName"]
    },
    "usageConditions": {
      "type": "object",
      "description": "Conditions/Restrictions of use | 使用条件/限制",
      "properties": {
        "productTypeBodyParts": {
          "type": "object",
          "description": "Applicable/restricted product types and body parts | 适用/限制的产品类型和身体部位",
          "properties": {
            "eng": {
              "type": "string",
              "description": "Product types and body parts in English"
            },
            "chs": {
              "type": "string",
              "description": "产品类型和身体部位中文描述"
            }
          }
        },
        "maximumConcentration": {
          "type": "string",
          "description": "Maximum concentration in ready for use preparation (e.g., '0.5%', '100ppm') | 即用制剂中的最大浓度"
        },
        "maxConcentration_leaveon": {
          "type": "string",
          "description": "Maximum concentration for leave-on products (e.g., '0.5%') | 驻留类产品中的最大浓度"
        },
        "maxConcentration_rinseoff": {
          "type": "string",
          "description": "Maximum concentration for rinse-off products (e.g., '2%') | 淋洗类产品中的最大浓度"
        },
        "other": {
          "type": "object",
          "description": "Other conditions or restrictions | 其他条件或限制",
          "properties": {
            "eng": {
              "type": "string",
              "description": "Other conditions in English"
            },
            "chs": {
              "type": "string",
              "description": "其他条件中文描述"
            }
          }
        }
      }
    },
    "wordingOfConditionsAndWarnings": {
      "type": "object",
      "description": "Required wording of conditions of use and warnings on product labels | 标签上要求的使用条件和警告措辞",
      "properties": {
        "eng": {
          "type": "string",
          "description": "Warning text in English"
        },
        "chs": {
          "type": "string",
          "description": "警告文字中文版本"
        }
      }
    },
    "regulatoryReferences": {
      "type": "object",
      "description": "Regulatory references | 法规参考",
      "properties": {
        "regulation": {
          "type": "string",
          "description": "Main regulation reference | 主要法规参考"
        },
        "otherDirectivesRegulations": {
          "type": "string",
          "description": "Other related directives or regulations | 其他相关指令或法规"
        },
        "sccsOpinions": {
          "type": "string",
          "description": "SCCS opinions reference | SCCS意见参考编号"
        }
      }
    },
    "identifiedIngredients": {
      "type": "array",
      "description": "List of identified ingredients or substances (monolingual). | 已识别成分或物质列表（单语）。",
      "items": {
        "type": "string"
      }
    },
    "cmrClassification": {
      "type": "string",
      "description": "CMR classification (Carcinogenic, Mutagenic, Reprotoxic) - standard codes | CMR分类（标准代码）",
      "enum": ["CMR1A", "CMR1B", "CMR2"]
    },
    "updateDate": {
      "type": "string",
      "format": "date",
      "description": "Last update date (ISO 8601 format: YYYY-MM-DD) | 最后更新日期"
    }
  },
  "required": ["annexType", "referenceNumber", "substanceIdentification"]
};


// =================================================================================
// --- 触发器管理函数 (TW) ---
// =================================================================================

/**
 * 检查 'GetTWJsons' 触发器是否已存在。
 * @returns {boolean} - 触发器是否活跃。
 */
function isTWProcessingTriggerActive() {
    const triggers = ScriptApp.getProjectTriggers();
    return triggers.some(trigger => trigger.getHandlerFunction() === 'GetTWJsons');
}

/**
 * 停止 'GetTWJsons' 批量处理的定时触发器。
 * @param {boolean} log - 是否打印日志。
 */
function stopTWJsonProcessingTrigger(log = true) {
    const triggers = ScriptApp.getProjectTriggers();
    let count = 0;
    triggers.forEach(trigger => {
        if (trigger.getHandlerFunction() === 'GetTWJsons') {
            ScriptApp.deleteTrigger(trigger);
            count++;
        }
    });
    
    if (log) {
        if (count > 0) {
            Logger.log(`[删除触发器] 已删除 ${count} 个旧的 'GetTWJsons' 触发器。`);
        } else {
            Logger.log(`[删除触发器] 未找到活动的 'GetTWJsons' 触发器。`);
        }
    }
}

/**
 * 重置 GetTWJsons 函数的工作表处理进度。
 */
function resetTWJsonProgress() {
    const properties = PropertiesService.getScriptProperties();
    properties.deleteProperty(TW_JSON_TRIGGER_INIT_KEY); // 清除初始化时间戳

    Logger.log(`[进度重置] 台湾 (TW) JSON 生成任务的进度已清除。`);
}

// =================================================================================
// --- 核心处理函数 (TW) ---
// =================================================================================

/**
 * 启动台湾 (TW) JSON 批量处理的主函数。
 * 首次运行时，会记录时间，并在 2 分钟后建立一个每 5 分钟运行一次的循环触发器。
 * 随后，每次触发器调用此函数时，都会执行数据处理循环，最大运行时间约为 5 分 30 秒。
 */
async function GetTWJsons() {
    let ui;
    try {
        ui = SpreadsheetApp.getUi();
    } catch (e) {
        Logger.log("无法获取 UI 上下文。");
    }

    const properties = PropertiesService.getScriptProperties();
    const startTime = new Date().getTime(); // 记录本次启动时间
    
    // =================================================
    // 触发器初始化和延迟建立
    // =================================================
    if (!isTWProcessingTriggerActive()) {
        const initTimeStr = properties.getProperty(TW_JSON_TRIGGER_INIT_KEY);
        
        if (!initTimeStr) {
            // 首次运行或上次完成/超时，设置初始化时间戳，等待 2 分钟。
            properties.setProperty(TW_JSON_TRIGGER_INIT_KEY, startTime.toString());
            Logger.log(`[触发器初始化 TW] 首次运行。已设置初始化时间戳，将在 ${TW_TRIGGER_DELAY_MS / 1000} 秒后建立触发器。`);
            
        } else {
            // 检查是否已达到 2 分钟的延迟时间
            const initTime = parseInt(initTimeStr);
            const timeElapsed = startTime - initTime;
            
            if (timeElapsed >= TW_TRIGGER_DELAY_MS) {
                // 延迟时间已到，建立触发器
                stopTWJsonProcessingTrigger(false); // 确保没有重复的触发器
                
                ScriptApp.newTrigger('GetTWJsons')
                    .timeBased()
                    .everyMinutes(TW_TRIGGER_INTERVAL_MINUTES)
                    .create();
                
                properties.deleteProperty(TW_JSON_TRIGGER_INIT_KEY); // 清除初始化时间戳
                Logger.log(`[建立触发器 TW] 已等待 ${TW_TRIGGER_DELAY_MS / 1000} 秒。建立了 'GetTWJsons' 每 ${TW_TRIGGER_INTERVAL_MINUTES} 分钟循环执行的触发器。`);
                
            } else {
                // 未到延迟时间，继续处理数据，等待下次运行建立触发器
                Logger.log(`[等待触发器 TW] 未到 ${TW_TRIGGER_DELAY_MS / 1000} 秒延迟。已运行 ${timeElapsed / 1000} 秒。`);
            }
        }
    }
    // =================================================
    
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    
    if (TW_SOURCE_SHEET_NAMES.length === 0) {
         Logger.log("错误：TW_SOURCE_SHEET_NAMES (来自 TW_SHEET_CONFIG) 为空。无法开始任务。");
         return;
    }
    
    Logger.log("=========================================================");
    Logger.log(`台湾 (TW) JSON 生成任务启动。最大运行时间: ${TW_MAX_RUN_TIME_MS / 1000} 秒。`);
    Logger.log("=========================================================");

    let processedBatchInThisExecution = false;

    // 外层无限循环，保证在时间限制内持续查找和处理批次
    while (true) {
        let foundNewBatch = false;

        // 1. 检查时间限制
        if (new Date().getTime() - startTime > TW_MAX_RUN_TIME_MS) {
            Logger.log(`[EXIT TW] 执行时间已达 ${TW_MAX_RUN_TIME_MS / 1000} 秒限制。停止当前运行，等待下次触发。`);
            return;
        }

        // 2. 遍历所有工作表查找未处理的行
        for (const currentSheetName of TW_SOURCE_SHEET_NAMES) {
            // 获取特定于此工作表的配置
            const config = TW_SHEET_CONFIG[currentSheetName];
            if (!config) {
                Logger.log(`[警告 TW] 找不到 ${currentSheetName} 的配置，跳过。`);
                continue;
            }

            const sheet = ss.getSheetByName(currentSheetName);
            if (!sheet || sheet.getLastRow() < config.dataStart) continue;
            
            // 每次进入新的工作表都检查时间
            if (new Date().getTime() - startTime > TW_MAX_RUN_TIME_MS) break;

            const numColsToRead = columnToNumber(config.cols);

            // 读取表头 (根据配置)
            const headerRowsData = sheet.getRange(config.headerStart, 1, config.headerCount, numColsToRead).getValues();
            const headers = getCombinedHeadersTW(headerRowsData, numColsToRead); // 使用新的标题合并函数

            const lastRow = sheet.getLastRow();
            const dataRowCount = lastRow - config.dataStart + 1;
            if (dataRowCount <= 0) continue;
            
            // 读取 A 列和 R 列的数据，确定处理范围
            // [A列 (1), R列 (TW_JSON_WRITE_COL_START)]
            const checkRange = sheet.getRange(config.dataStart, 1, dataRowCount, TW_JSON_WRITE_COL_START).getValues();
            
            const rowsToProcess = [];
            const processingRowIndices = [];
            let batchFoundIndex = -1; // 记录找到批次的起始索引

            // 查找第一个未处理的行 (A列有值且 R列为空)
            for (let r = 0; r < dataRowCount; r++) {
                const aColValue = String(checkRange[r][0]).trim(); // A 列的值
                const rColValue = String(checkRange[r][TW_JSON_WRITE_COL_START - 1]).trim(); // R 列的值

                // 检查：A列有值 AND R列为空
                if (aColValue !== '' && rColValue === '') {
                    batchFoundIndex = r;
                    break;
                }
            }
            
            if (batchFoundIndex !== -1) {
                // 找到了批次，现在收集这个批次的数据
                foundNewBatch = true;
                processedBatchInThisExecution = true;
                
                const rowIndex = config.dataStart + batchFoundIndex; // 实际行号 (基于 1)
                
                // 读取 TW_JSON_BATCH_SIZE 数量的行
                let batchData = sheet.getRange(rowIndex, 1, TW_JSON_BATCH_SIZE, numColsToRead).getValues();
                
                let i = 0;
                while (i < batchData.length) {
                    const row = batchData[i];
                    // 确保 A 列有值才处理 (处理到空行即停止批次收集)
                    if (String(row[0]).trim() !== '') {
                        rowsToProcess.push(row);
                        processingRowIndices.push(rowIndex + i);
                        i++;
                    } else {
                        break; 
                    }
                }

                Logger.log(`\n工作表 "${currentSheetName}" 找到 ${rowsToProcess.length} 行未处理数据，开始 API 调用...`);

                // 3. 处理批次 (API 调用)
                const apiCalls = rowsToProcess.map(rowData => 
                    convertRowToTWJson(headers, rowData, config.annex, false) // 传入 annexType
                );

                let jsonOutput;
                try {
                    jsonOutput = await Promise.all(apiCalls);
                } catch (e) {
                    Logger.log(`致命错误：API 调用批次处理中断：${e.toString()}`);
                    return; 
                }

                // 4. 写入到 R 列
                const startRow = processingRowIndices[0];
                const numRowsToProcess = jsonOutput.length;
                const finalOutput = jsonOutput.map(jsonString => [jsonString]); 

                try {
                    sheet.getRange(startRow, TW_JSON_WRITE_COL_START, numRowsToProcess, 1).setValues(finalOutput);
                    
                    const endRow = startRow + numRowsToProcess - 1;
                    Logger.log(`[写入成功 TW] 成功写入 ${numRowsToProcess} 行数据到 "${currentSheetName}" (行 ${startRow} 到 ${endRow})。`);
                    
                    // 写入后延时
                    Utilities.sleep(TW_API_BATCH_DELAY_MS);

                } catch (e) {
                    Logger.log(`处理 JSON 时出错: 写入表格失败: ${e.toString()}`);
                    return;
                }
                
                // 批次处理完毕，跳出当前工作表的循环，重新开始 WHILE(TRUE) 循环，以便检查时间并查找下一个批次
                break; 
            }
            
            // 如果未找到批次，继续下一个工作表
        } 
        
        // 5. WHILE(TRUE) 退出条件检查
        if (!foundNewBatch) {
            // 扫描了所有工作表，但这一轮中没有找到任何新的未处理批次
            Logger.log(`[完成扫描 TW] 扫描了所有工作表 (${TW_SOURCE_SHEET_NAMES.length} 张)，未找到新的未处理批次。`);
            
            if (processedBatchInThisExecution) {
                // 如果本次执行中至少处理过一个批次，但这一轮扫描没找到，说明处理完了。
                Logger.log("[COMPLETE TW] 台湾 (TW) JSON 任务已完成。自动停止触发器。");
                stopTWJsonProcessingTrigger();
                return;
            } else {
                // 如果本次执行中从未处理过批次（脚本一启动就发现没数据了）
                Logger.log("[COMPLETE TW] 脚本启动时发现所有数据已处理。自动停止触发器。");
                stopTWJsonProcessingTrigger();
                return;
            }
        }
        
        // 如果找到了新批次 (foundNewBatch=true)，则 while(true) 循环继续，再次从第一个工作表开始查找
    }
}


// =================================================================================
// --- 测试函数 (TW) ---
// =================================================================================

/**
 * 测试函数：处理每个 TW sheet 的第一条记录
 * 并打印生成的 JSON 结构，但不写入表格。
 */
async function testCreateTWJson() {
    let ui;
    try {
        ui = SpreadsheetApp.getUi();
    } catch (e) {
        Logger.log("无法获取 UI 上下文。");
    }

    const ss = SpreadsheetApp.getActiveSpreadsheet();
    Logger.log("========== [TEST] GetTWJsons PROMPT (Gemini API Schema Mode) ==========");
    Logger.log("--- 开始测试每个台湾 (TW) 工作表的第一行数据 JSON 生成 ---");

    let successCount = 0;

    if (TW_SOURCE_SHEET_NAMES.length === 0) {
        Logger.log("错误：TW_SOURCE_SHEET_NAMES 为空。请检查 TW_SHEET_CONFIG 配置。");
        if (ui) ui.alert("错误：TW_SOURCE_SHEET_NAMES 为空。");
        return;
    }
    
    for (const sheetName of TW_SOURCE_SHEET_NAMES) {
        const config = TW_SHEET_CONFIG[sheetName];
        if (!config) {
             Logger.log(`警告：找不到工作表 "${sheetName}" 的配置，跳过。`);
             continue;
        }

        const sheet = ss.getSheetByName(sheetName);
        if (!sheet) {
            Logger.log(`警告：找不到工作表 "${sheetName}"，跳过。`);
            continue;
        }

        Logger.log(`\n>>> 正在处理工作表: ${sheetName}`);

        try {
            const numColsToRead = columnToNumber(config.cols);

            // 1. 读取标题行 (根据配置)
            const headerRowsData = sheet.getRange(config.headerStart, 1, config.headerCount, numColsToRead).getValues();
            const headers = getCombinedHeadersTW(headerRowsData, numColsToRead);

            Logger.log(`   [DEBUG] 原始表头 (行 ${config.headerStart} 到 ${config.headerStart + config.headerCount - 1}): ${JSON.stringify(headerRowsData)}`);
            Logger.log(`   [DEBUG] 清理/合并后的表头: ${JSON.stringify(headers)}`);


            // 2. 读取第一行数据 (根据配置)
            const rowData = sheet.getRange(config.dataStart, 1, 1, numColsToRead).getValues()[0];
            
            // 3. 转换成 JSON 字符串 (启用调试日志)
            const jsonString = await convertRowToTWJson(headers, rowData, config.annex, true);
            
            Logger.log(`   [SUCCESS] 生成的 JSON (第 ${config.dataStart} 行):`);
            // 尝试美化打印 JSON
            try {
                const parsedJson = JSON.parse(jsonString);
                Logger.log(JSON.stringify(parsedJson, null, 2));
            } catch (e) {
                Logger.log(jsonString); // 如果无法解析，则打印原始字符串
            }
            
            successCount++;

            // 测试运行时也增加延迟
            Utilities.sleep(TW_API_BATCH_DELAY_MS);

        } catch (e) {
            Logger.log(`   [ERROR] 处理工作表 ${sheetName} 失败: ${e.toString()}`);
            // 遇到错误立即停止，方便调试
            return;
        }
    }

    Logger.log("--- 结束测试 (TW) ---");
    const finalMessage = `台湾 (TW) JSON 测试生成完毕。共处理了 ${successCount} 个工作表的第一行数据。请在 Apps Script 编辑器中通过 "查看" > "日志" 来检查 JSON 输出内容。`;
    Logger.log(finalMessage);
    if (ui) ui.alert(finalMessage);
}


// =================================================================================
// --- [新] 单行测试函数 (TW) ---
// =================================================================================

/**
 * [新] 测试函数运行器：处理指定工作表的指定行号
 * * [!] 使用方法:
 * 1. 更改下面的 `TEST_SHEET_NAME` 为您要测试的工作表名称 (例如 "色素成分" 或 "Restricted")。
 * 2. 更改下面的 `TEST_ROW_NUMBER` 为您要测试的行号 (例如 8, 9, 10...)。
 * 3. 从 Apps Script 编辑器运行此函数 (runTestSingleTWJson)。
 * 4. 在日志中查看结果。
 */
async function runTestSingleTWJson() {
    // --- [!] 在这里配置您要测试的单行 ---
    const TEST_SHEET_NAME = "Restricted"; 
    const TEST_ROW_NUMBER = 3;     // [!] 必须是数据起始行或之后 (例如 "色素成分" 是从第 8 行开始)
    // ------------------------------------

    Logger.log(`========== [TEST] testSingleTWJson (单行测试) ==========`);
    Logger.log(`>>> 准备处理工作表: "${TEST_SHEET_NAME}", 行号: ${TEST_ROW_NUMBER}`);
    
    try {
        const jsonString = await testSingleTWJson_Logic(TEST_SHEET_NAME, TEST_ROW_NUMBER);
        
        Logger.log(`   [SUCCESS] 成功生成 JSON (工作表: "${TEST_SHEET_NAME}", 行: ${TEST_ROW_NUMBER}):`);
        try {
            const parsedJson = JSON.parse(jsonString);
            Logger.log(JSON.stringify(parsedJson, null, 2));
        } catch (e) {
            Logger.log(jsonString); // 无法解析则打印原始字符串
        }

    } catch (e) {
        Logger.log(`   [ERROR] 处理失败 (工作表: "${TEST_SHEET_NAME}", 行: ${TEST_ROW_NUMBER}): ${e.toString()}`);
        Logger.log(e.stack); // 打印堆栈跟踪
    }
    Logger.log("========== [TEST] 单行测试结束 ==========");
}

/**
 * [新] 测试函数核心逻辑：处理单行
 * @param {string} sheetName 要测试的工作表名称
 * @param {number} rowNumber 要测试的具体行号
 * @returns {Promise<string>} JSON 字符串
 */
async function testSingleTWJson_Logic(sheetName, rowNumber) {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    
    const config = TW_SHEET_CONFIG[sheetName];
    if (!config) {
        throw new Error(`找不到工作表 "${sheetName}" 的配置。`);
    }

    const sheet = ss.getSheetByName(sheetName);
    if (!sheet) {
        throw new Error(`找不到工作表 "${sheetName}"。`);
    }
    
    if (rowNumber < config.dataStart) {
        throw new Error(`行号 ${rowNumber} 无效。此工作表的数据从第 ${config.dataStart} 行开始。`);
    }

    const numColsToRead = columnToNumber(config.cols);

    // 1. 读取标题行 (根据配置)
    const headerRowsData = sheet.getRange(config.headerStart, 1, config.headerCount, numColsToRead).getValues();
    const headers = getCombinedHeadersTW(headerRowsData, numColsToRead);

    // 2. 读取指定行数据
    const rowData = sheet.getRange(rowNumber, 1, 1, numColsToRead).getValues()[0];
    
    // 3. 转换成 JSON 字符串 (启用调试日志)
    return await convertRowToTWJson(headers, rowData, config.annex, true);
}


// =================================================================================
// --- 辅助函数 (TW) ---
// =================================================================================

/**
 * 将单行数据根据表头转换为符合 Schema 的 JSON 字符串，并通过 Gemini API 验证和生成 (TW 版本)。
 * @param {Array<string>} headers - 整合后的表头键名。
 * @param {Array<any>} rowData - 单行数据。
 * @param {string} annexType - 目标 annexType (例如 "ANNEX_II")。
 * @param {boolean} isTestMode - 是否为测试模式 (true 时打印详细 API Payload)。
 * @returns {Promise<string>} - JSON 字符串。
 */
async function convertRowToTWJson(headers, rowData, annexType, isTestMode) {
    const contextData = {};
    
    // 1. 预处理数据为扁平的 K-V 对象
    headers.forEach((headerKey, index) => {
        if (headerKey === '') return;

        let value = rowData[index];
        
        // --- 值预处理与类型检查 ---
        if (typeof value === 'object' && value instanceof Date) {
            // 将日期格式化为 YYYY-MM-DD
            value = Utilities.formatDate(value, Session.getScriptTimeZone(), "yyyy-MM-DD");
        } else if (value === null || typeof value === 'undefined') {
            value = '';
        } else {
            value = String(value).trim();
        }
        
        contextData[headerKey] = value;
    });

    // 2. 添加台湾 (TW) 特定提示，便于 AI 填充 required 字段
    contextData['_target_annex_type'] = annexType;
    contextData['_target_country'] = "台湾"; // 固定为台湾


    // 3. 调用 Gemini API 进行结构化生成
    return callGeminiForTWJson(contextData, isTestMode);
}


/**
 * 调用 Gemini API (gemini-2.5-flash-preview-09-2025) 强制返回符合 Schema 的 JSON (TW 版本)。
 * @param {object} contextData - 包含行数据的 K-V 对象。
 * @param {boolean} isTestMode - 是否为测试模式 (true 时打印详细 API Payload)。
 * @returns {Promise<string>} - 原始 JSON 字符串。
 */
async function callGeminiForTWJson(contextData, isTestMode) {
    const apiKey = (typeof API_KEY !== 'undefined') ? API_KEY : "";
    const model = "gemini-2.5-flash-lite"; // 修正：使用 gemini-2.5-flash-lite
    const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;

    const contextJsonString = JSON.stringify(contextData);

    // [!] 关键修改：更新 systemPrompt 以适配台湾 (TW) 法规和繁体中文
    const systemPrompt = `您是一个台湾化妆品法规数据提取和翻译助手。
* 您的任务是根据用户提供的上下文数据，严格按照 JSON Schema 提取信息。
* Schema 中的 'eng' 字段（例如在 'chemicalName' 或 'wordingOfConditionsAndWarnings' 中）用于存放英文或原始数据。
* Schema 中的 'chs' 字段用于**繁体中文**字段。
* 如果上下文数据是英文，请将其填入 'eng' 字段，并**尽力将其翻译为繁体中文**后填入 'chs' 字段。
* 如果上下文数据是中文（简体或繁体），请**同时填入 'eng' 和 'chs' 字段**（确保 'chs' 字段为繁体中文）。
* **特殊规则 (单语数组)**：对于 'identifiedIngredients' 字段（它是一个字符串数组），如果 Schema 描述它是“单语”的，则**不需要**为它创建 'eng'/'chs' 对，只需按原样提取数据（如果数据是用逗号或换行符分隔的，则应拆分为数组）。
* **特殊规则 (默认值)**：'country' 字段应根据上下文中的 '_target_country' (例如 "台湾") 来填充。
* 'annexType' 字段应根据上下文中的 '_target_annex_type' (例如 "ANNEX_II") 来填充。
* 严格遵守 Schema 规定的数据类型和枚举值。`;
    
    const userQuery = `请根据以下上下文数据，提取符合 Schema 的 JSON：\n\n${contextJsonString}`;

    const payload = {
        contents: [{
            role: "user",
            parts: [{ text: userQuery }]
        }],
        systemInstruction: {
            parts: [{ text: systemPrompt }]
        },
        generationConfig: {
            responseMimeType: "application/json",
            responseSchema: COSMETIC_REGULATION_SCHEMA // 使用重命名后的 Schema
        }
    };

    if (isTestMode) {
        Logger.log(`[DEBUG TW] 正在调用的 API Key (前 4 位/后 4 位): ${apiKey.substring(0, 4)}...${apiKey.substring(apiKey.length - 4)}`);
        Logger.log(`[DEBUG TW] 正在调用的模型: ${model}`);
        Logger.log(`[DEBUG TW] 正在调用的完整 URL: ${apiUrl.split('key=')[0]}key=...REDACTED...`);
        Logger.log(`[DEBUG TW] 完整的 API Payload (格式化): \n${JSON.stringify(payload, null, 2)}`);
    }

    const maxRetries = 3;
    const initialDelay = 10000; // 10 seconds
    
    return fetchWithBackoff(apiUrl, payload, maxRetries, initialDelay);
}


/**
 * 带有指数退避（Exponential Backoff）的 API 请求辅助函数。
 * (此函数为通用函数，保持不变)
 * @param {string} apiUrl - API 端点 URL。
 * @param {object} payload - 请求负载。
 * @param {number} maxRetries - 最大重试次数。
 * @param {number} initialDelay - 初始延时（毫秒）。
 * @returns {Promise<string>} - 成功时的 JSON 字符串。
 */
async function fetchWithBackoff(apiUrl, payload, maxRetries, initialDelay) {
    let lastError = null;
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const options = {
                method: 'post',
                contentType: 'application/json',
                payload: JSON.stringify(payload),
                muteHttpExceptions: true
            };

            const response = UrlFetchApp.fetch(apiUrl, options);
            const responseCode = response.getResponseCode();
            const contentText = response.getContentText();

            // 成功
            if (responseCode === 200) {
                const result = JSON.parse(contentText);
                const textPart = result.candidates?.[0]?.content?.parts?.[0]?.text;
                
                if (textPart) {
                    return textPart;
                } else {
                    lastError = new Error("API 响应成功，但缺少文本内容。");
                }
            } 
            
            // 429 速率限制 或 400/403/500 等其他错误
            if (responseCode === 429 || responseCode >= 400) {
                 lastError = new Error(`API 请求失败，状态码: ${responseCode}. 详情: ${contentText}`);
                 Logger.log(`[API] 收到响应: ${responseCode}. 内容: ${contentText}`);

                 // 如果是 429 或 500 (服务器错误)，则尝试重试
                 // 如果是 400 (无效参数) 或 403 (权限)，则不再重试
                 if (responseCode !== 429 && responseCode !== 500) {
                     break; 
                 }
            } else {
                 lastError = new Error(`API 收到未知状态码: ${responseCode}`);
            }

        } catch (e) {
            lastError = new Error(`fetch 捕获到意外错误: ${e.toString()}`);
        }

        // 准备下一次重试
        if (attempt < maxRetries) {
            const delay = initialDelay * Math.pow(2, attempt - 1);
            Logger.log(`[API] 尝试 ${attempt}/${maxRetries} 失败。等待 ${delay} 毫秒后重试...`);
            Utilities.sleep(delay);
        }
    }

    // 达到最大重试次数或遇到不可恢复的错误，抛出错误
    throw lastError;
}


/**
 * [新] 整合多行表头 (台湾版)。
 * 将多行标题合并为单行键名，用于 '色素成分' (7行) 等工作表。
 * @param {Array<Array<any>>} headerRowsData - 包含 N 行标题数据的二维数组。
 * @param {number} numCols - 要读取的列数。
 * @returns {Array<string>} - 整合后的表头数组。
 */
function getCombinedHeadersTW(headerRowsData, numCols) {
    const headers = [];
    const numHeaderRows = headerRowsData.length;

    for (let j = 0; j < numCols; j++) { // 遍历每一列
        let columnHeaders = [];
        for (let i = 0; i < numHeaderRows; i++) { // 遍历该列的每一行
            const cellValue = (headerRowsData[i] && headerRowsData[i][j]) ? String(headerRowsData[i][j]).trim() : '';
            if (cellValue !== '') {
                columnHeaders.push(cellValue);
            }
        }
        
        // 将该列的所有非空标题单元格用空格连接
        let combinedHeader = columnHeaders.join(' ').trim().toLowerCase();
        
        if (combinedHeader === '') {
            headers.push(''); 
        } else {
            // 清理掉多余空格，并替换 '/' 和 ',' 为 '_'
            headers.push(combinedHeader.replace(/[\s\/,]+/g, '_').replace(/_+/g, '_')); 
        }
    }
    return headers;
}

/**
 * 将列字母（如 'A', 'B', 'AA'）转换为数字（1, 2, 27）。
 * (此函数为通用函数，保持不变)
 * @param {string} column - 列的字母表示。
 * @returns {number} - 列的数字表示。
 */
function columnToNumber(column) {
  let sum = 0;
  for (let i = 0; i < column.length; i++) {
    sum *= 26;
    sum += column.charCodeAt(i) - 'A'.charCodeAt(0) + 1;
  }
  return sum;
}



