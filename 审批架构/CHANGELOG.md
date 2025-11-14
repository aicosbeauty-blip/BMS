# 更新日志 (CHANGELOG)

## 版本 1.1 - 2025-11-05

### 🐛 Bug修复

#### 修复从JSON加载流程时员工信息不显示的问题

**问题描述：**
- 从JSON文件加载流程时，流程节点下的员工信息没有显示
- 手工拖拽添加新流程节点时可以正常显示员工信息

**根本原因：**
原代码在 `selectProcess()` 函数中只通过 `roleId` 查找角色，但JSON文件中的流程节点可能：
1. 没有 `roleId` 字段，只有 `role` 名称
2. `roleId` 与角色数据不匹配
3. 使用了 `roleName` 而不是 `role` 字段

**修复方案：**
增强了角色匹配逻辑，现在支持三种匹配方式（按优先级）：

1. **通过 roleId 匹配**（最精确）
   ```javascript
   if (node.roleId) {
       role = availableRoles.find(r => r.id === node.roleId);
   }
   ```

2. **通过 role 名称匹配**（常用方式）
   ```javascript
   if (!role && node.role) {
       role = availableRoles.find(r => r.name === node.role);
       if (role) {
           node.roleId = role.id; // 自动补充roleId
       }
   }
   ```

3. **通过 roleName 匹配**（兼容旧格式）
   ```javascript
   if (!role && node.roleName) {
       role = availableRoles.find(r => r.name === node.roleName);
       if (role) {
           node.roleId = role.id;
           node.role = node.roleName;
       }
   }
   ```

**修复后的效果：**
- ✅ 支持只使用角色名称的简化配置
- ✅ 自动从角色数据加载员工信息
- ✅ 兼容多种JSON格式
- ✅ 提供详细的控制台日志便于调试
- ✅ 保留已有的员工数据（如果节点已配置）

**控制台输出示例：**
```
✓ 成功加载 15 个可用角色
✓ 成功加载 3 个审批流程
✓ 为节点 "部门经理" 加载了 5 名员工
✓ 为节点 "财务经理" 加载了 3 名员工
✓ 为节点 "总经理" 加载了 1 名员工
```

如果出现问题会显示警告：
```
⚠ 未找到角色 "某角色名" 的员工信息
```

### 📝 相关文件更新

- **main-logic.js** - 修复了 `selectProcess()` 函数的角色匹配逻辑

### 📚 新增文档

- **流程JSON格式说明.md** - 详细说明了流程.json的正确格式和使用方法

### 🎯 使用建议

#### 最简配置方式
如果你的 `角色.json` 文件已经包含了完整的角色和员工信息，那么 `流程.json` 可以非常简洁：

```json
{
  "data": [
    {
      "id": "process1",
      "name": "报销审批流程",
      "amountLimit": 10000,
      "nodes": [
        {"id": "node1", "role": "部门经理"},
        {"id": "node2", "role": "财务经理"},
        {"id": "node3", "role": "总经理"}
      ]
    }
  ]
}
```

系统会自动：
1. 根据 `role` 字段查找对应的角色
2. 加载该角色下的所有员工
3. 显示在流程节点中

#### 精确配置方式
如果需要更精确的控制，可以同时提供 `roleId`：

```json
{
  "id": "node1",
  "role": "部门经理",
  "roleId": "ROLE001"
}
```

这样可以确保即使角色名称相同，也能准确匹配到正确的角色。

### 🔍 故障排查指南

如果员工信息仍然不显示，请检查：

1. **打开浏览器控制台** (按F12)
2. **查看是否有错误信息**
3. **确认角色数据已加载**：应该看到 "✓ 成功加载 X 个可用角色"
4. **确认角色名称匹配**：流程节点的 `role` 值必须与角色.json中的 `RLNAME` 完全一致
5. **确认角色有员工**：在角色.json中检查对应角色的 `data1` 数组是否有数据

### 💡 技术细节

修复涉及的代码变更：

**修改前：**
```javascript
workflowNodes.forEach(node => {
    if (node.roleId) {
        const role = availableRoles.find(r => r.id === node.roleId);
        if (role && role.employees) {
            // 加载员工
        }
    }
});
```

**修改后：**
```javascript
workflowNodes.forEach(node => {
    // 如果节点已经有员工数据，跳过
    if (node.employees && node.employees.length > 0) {
        return;
    }
    
    // 初始化员工数组
    node.employees = [];
    
    // 多种方式匹配角色
    let role = null;
    if (node.roleId) {
        role = availableRoles.find(r => r.id === node.roleId);
    }
    if (!role && node.role) {
        role = availableRoles.find(r => r.name === node.role);
        if (role) node.roleId = role.id;
    }
    if (!role && node.roleName) {
        role = availableRoles.find(r => r.name === node.roleName);
        if (role) {
            node.roleId = role.id;
            node.role = node.roleName;
        }
    }
    
    // 加载员工信息
    if (role && role.employees && role.employees.length > 0) {
        node.employees = role.employees.map(emp => ({...}));
        console.log(`✓ 为节点 "${node.role}" 加载了 ${node.employees.length} 名员工`);
    } else {
        console.warn(`⚠ 未找到角色 "${node.role}" 的员工信息`);
    }
});
```

### 📦 更新的文件列表

1. ✅ main-logic.js (已更新)
2. ✅ 流程JSON格式说明.md (新增)
3. ✅ CHANGELOG.md (本文件)

---

## 版本 1.0 - 2025-11-05

### ✨ 初始版本

- 将原始的大型HTML文件拆分为5个模块化文件
- 实现员工权限编辑功能的独立模块
- 支持拖拽配置审批流程
- 支持从JSON文件加载数据
- 提供完整的文档说明

### 📁 文件结构

```
project/
├── index.html (4.3KB)
├── styles.css (1.7KB)
├── main-logic.js (21KB)
├── employee-permission-modal.html (5.4KB)
├── employee-permission-modal.js (12KB)
├── README.md
└── ARCHITECTURE.md
```

### 🎯 核心功能

- ✅ 审批流程可视化编辑
- ✅ 拖拽添加审批节点
- ✅ 员工权限配置
- ✅ 部门架构管理
- ✅ 流程导入导出
- ✅ 模块化架构设计
