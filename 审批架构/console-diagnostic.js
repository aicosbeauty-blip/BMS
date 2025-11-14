// ========================================
// 🔍 紧急诊断脚本 v1.2
// 请在主页面的控制台(F12)中运行此脚本
// ========================================

console.clear();
console.log('%c🔍 开始系统诊断...', 'font-size: 18px; color: #f97316; font-weight: bold;');
console.log('');

// 1. 检查版本
console.log('%c1️⃣ 检查代码版本', 'font-size: 14px; font-weight: bold;');
if (typeof selectProcess === 'function') {
    const funcCode = selectProcess.toString();
    if (funcCode.includes('处理节点') && funcCode.includes('员工列表:')) {
        console.log('%c✅ 版本正确: v1.2 (包含详细日志)', 'color: #10b981');
    } else if (funcCode.includes('方式2：通过role名称查找')) {
        console.log('%c⚠️  版本: v1.1 (部分修复)', 'color: #f59e0b');
        console.log('%c请更新到 v1.2 获取更多调试信息', 'color: #f59e0b');
    } else {
        console.log('%c❌ 版本过旧: v1.0 或更早', 'color: #ef4444');
        console.log('%c必须更新 main-logic.js 文件！', 'color: #ef4444; font-weight: bold;');
    }
} else {
    console.log('%c❌ 错误: selectProcess 函数不存在', 'color: #ef4444');
}
console.log('');

// 2. 检查数据加载
console.log('%c2️⃣ 检查数据加载状态', 'font-size: 14px; font-weight: bold;');
const hasRoles = typeof availableRoles !== 'undefined' && availableRoles && availableRoles.length > 0;
const hasProcess = typeof processList !== 'undefined' && processList && processList.length > 0;
const hasNodes = typeof workflowNodes !== 'undefined' && workflowNodes && workflowNodes.length > 0;

console.log(`角色数据: ${hasRoles ? '✅' : '❌'} ${availableRoles?.length || 0} 个角色`);
console.log(`流程数据: ${hasProcess ? '✅' : '❌'} ${processList?.length || 0} 个流程`);
console.log(`工作流节点: ${hasNodes ? '✅' : '❌'} ${workflowNodes?.length || 0} 个节点`);
console.log('');

if (!hasRoles) {
    console.log('%c❌ 角色数据未加载！', 'color: #ef4444; font-size: 14px; font-weight: bold;');
    console.log('可能原因:');
    console.log('  1. 角色.json 文件不存在或路径错误');
    console.log('  2. JSON 格式错误');
    console.log('  3. 网络请求失败(检查 Network 标签)');
    console.log('  4. 跨域问题(需要使用本地服务器)');
    console.log('');
}

if (!hasNodes && hasProcess) {
    console.log('%c⚠️  有流程但没有节点', 'color: #f59e0b; font-size: 14px;');
    console.log('请点击左侧的某个流程');
    console.log('');
}

// 3. 详细检查每个节点
if (hasNodes) {
    console.log('%c3️⃣ 详细检查每个节点', 'font-size: 14px; font-weight: bold;');
    console.log('');
    
    let hasAnyEmployees = false;
    let hasProblem = false;
    
    workflowNodes.forEach((node, index) => {
        const empCount = node.employees ? node.employees.length : 0;
        const hasEmps = empCount > 0;
        hasAnyEmployees = hasAnyEmployees || hasEmps;
        
        console.log(`%c节点 ${index + 1}: ${node.role || node.roleName}`, 
                   'font-weight: bold; font-size: 13px;');
        console.log(`  角色ID: ${node.roleId || '无'}`);
        console.log(`  员工数: ${empCount} ${hasEmps ? '✅' : '❌'}`);
        
        if (hasEmps) {
            console.log(`  员工列表: ${node.employees.map(e => e.name).join(', ')}`);
        } else {
            hasProblem = true;
            console.log(`  %c⚠️  没有员工数据`, 'color: #ef4444;');
            
            // 测试角色匹配
            if (hasRoles) {
                const roleName = node.role || node.roleName;
                const matchedRole = availableRoles.find(r => r.name === roleName);
                
                if (matchedRole) {
                    console.log(`  %c✓ 找到匹配角色: ${matchedRole.name}`, 'color: #10b981;');
                    console.log(`    角色有 ${matchedRole.employeeCount} 名员工`);
                    
                    if (matchedRole.employeeCount === 0) {
                        console.log(`    %c❌ 问题: 角色.json 中该角色的 data1 为空`, 'color: #ef4444;');
                    } else if (!matchedRole.employees || matchedRole.employees.length === 0) {
                        console.log(`    %c❌ 问题: 角色的 employees 数组为空`, 'color: #ef4444;');
                    } else {
                        console.log(`    %c❌ 问题: 角色有员工但未加载到节点`, 'color: #ef4444;');
                        console.log(`    这可能是代码逻辑问题，需要查看selectProcess函数`);
                    }
                } else {
                    console.log(`  %c❌ 找不到匹配的角色: "${roleName}"`, 'color: #ef4444;');
                    console.log(`  可用角色列表: ${availableRoles.map(r => r.name).join(', ')}`);
                    
                    // 检查是否有相似的
                    const similar = availableRoles.filter(r => 
                        r.name.includes(roleName) || roleName.includes(r.name) ||
                        r.name.toLowerCase() === roleName.toLowerCase()
                    );
                    if (similar.length > 0) {
                        console.log(`  💡 可能的匹配: ${similar.map(r => r.name).join(', ')}`);
                    }
                }
            }
        }
        console.log('');
    });
    
    // 总结
    if (!hasAnyEmployees) {
        console.log('%c❌ 所有节点都没有员工数据！', 'color: #ef4444; font-size: 16px; font-weight: bold;');
        console.log('');
    } else if (hasProblem) {
        console.log('%c⚠️  部分节点缺少员工数据', 'color: #f59e0b; font-size: 16px; font-weight: bold;');
        console.log('');
    } else {
        console.log('%c✅ 所有节点都有员工数据', 'color: #10b981; font-size: 16px; font-weight: bold;');
        console.log('');
    }
}

// 4. 角色数据详情
if (hasRoles) {
    console.log('%c4️⃣ 角色数据详情', 'font-size: 14px; font-weight: bold;');
    console.log('');
    availableRoles.forEach(role => {
        const empCount = role.employees ? role.employees.length : 0;
        console.log(`角色: ${role.name} (ID: ${role.id})`);
        console.log(`  员工数: ${empCount}`);
        if (empCount > 0) {
            const names = role.employees.slice(0, 5).map(e => e.RUSERNAME).join(', ');
            console.log(`  员工示例: ${names}${empCount > 5 ? ` ...等${empCount}人` : ''}`);
        } else {
            console.log(`  %c⚠️  该角色没有员工数据`, 'color: #f59e0b;');
        }
        console.log('');
    });
}

// 5. 建议操作
console.log('%c💡 建议操作', 'font-size: 14px; font-weight: bold;');
console.log('');

if (!hasRoles) {
    console.log('1. 检查 角色.json 文件是否存在');
    console.log('2. 查看 Network 标签，确认文件是否成功加载');
    console.log('3. 确保使用本地服务器运行(不要用 file:// 协议)');
} else if (!hasNodes) {
    console.log('1. 点击左侧的流程列表中的某个流程');
    console.log('2. 如果点击后还是没有，刷新页面重试');
} else {
    // 检查版本
    if (typeof selectProcess === 'function') {
        const funcCode = selectProcess.toString();
        if (!funcCode.includes('员工列表:')) {
            console.log('1. ⭐ 强烈建议: 更新到 main-logic.js v1.2 版本');
            console.log('2. 更新后强制刷新浏览器 (Ctrl+F5)');
        } else {
            console.log('1. 版本已是最新，检查角色名称是否完全匹配');
            console.log('2. 确认角色.json 中的 data1 数组有数据');
            console.log('3. 尝试重新选择流程或刷新页面');
        }
    }
}

console.log('');
console.log('%c========== 诊断完成 ==========', 'font-size: 18px; color: #f97316; font-weight: bold;');
console.log('');
console.log('如需查看原始数据，运行: console.log({availableRoles, workflowNodes})');
console.log('');
