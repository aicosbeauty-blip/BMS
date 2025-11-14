/**
 * 调试辅助脚本
 * 在浏览器控制台运行这些命令来诊断问题
 */

// ========== 调试命令集 ==========

// 1. 检查角色数据是否加载
console.log('=== 检查角色数据 ===');
console.log('角色总数:', availableRoles ? availableRoles.length : 0);
if (availableRoles && availableRoles.length > 0) {
    console.log('前3个角色:', availableRoles.slice(0, 3).map(r => ({
        id: r.id,
        name: r.name,
        employeeCount: r.employeeCount
    })));
    
    // 显示每个角色的员工信息
    availableRoles.forEach(role => {
        console.log(`角色 "${role.name}" (ID: ${role.id}):`, 
                   role.employees ? role.employees.length + ' 名员工' : '无员工数据');
        if (role.employees && role.employees.length > 0) {
            console.log('  员工列表:', role.employees.map(e => e.RUSERNAME || e.name).join(', '));
        }
    });
}

// 2. 检查流程数据
console.log('\n=== 检查流程数据 ===');
console.log('流程总数:', processList ? processList.length : 0);
if (processList && processList.length > 0) {
    processList.forEach(process => {
        console.log(`流程: "${process.name}" (ID: ${process.id})`);
        console.log('  节点数:', process.nodes ? process.nodes.length : 0);
        if (process.nodes) {
            process.nodes.forEach((node, idx) => {
                console.log(`  节点 ${idx + 1}:`, {
                    id: node.id,
                    role: node.role,
                    roleId: node.roleId,
                    roleName: node.roleName,
                    员工数: node.employees ? node.employees.length : 0
                });
            });
        }
    });
}

// 3. 检查当前显示的工作流节点
console.log('\n=== 检查当前工作流 ===');
console.log('当前流程ID:', selectedProcessId);
console.log('工作流节点数:', workflowNodes ? workflowNodes.length : 0);
if (workflowNodes && workflowNodes.length > 0) {
    workflowNodes.forEach((node, idx) => {
        console.log(`节点 ${idx + 1}:`, {
            id: node.id,
            role: node.role,
            roleId: node.roleId,
            员工数: node.employees ? node.employees.length : 0,
            员工列表: node.employees ? node.employees.map(e => e.name).join(', ') : '无'
        });
    });
}

// 4. 测试角色匹配
console.log('\n=== 测试角色匹配 ===');
if (workflowNodes && workflowNodes.length > 0 && availableRoles && availableRoles.length > 0) {
    workflowNodes.forEach(node => {
        const roleName = node.role || node.roleName;
        const matchedRole = availableRoles.find(r => r.name === roleName);
        console.log(`节点角色 "${roleName}":`, matchedRole ? 
            `✓ 找到匹配 (ID: ${matchedRole.id}, ${matchedRole.employeeCount} 名员工)` : 
            '✗ 未找到匹配角色');
    });
}

// 5. 检查部门数据
console.log('\n=== 检查部门数据 ===');
console.log('部门总数:', departmentData && departmentData.data ? departmentData.data.length : 0);

console.log('\n=== 诊断完成 ===');
console.log('如果看到警告或错误，请仔细检查上述信息');
