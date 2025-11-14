# 流程.json 文件格式说明

## 正确的JSON格式示例

```json
{
  "data": [
    {
      "id": "process1",
      "name": "报销审批流程",
      "amountLimit": 10000,
      "createBy": "ADMIN",
      "updateTime": "2025-01-01 10:30:00",
      "nodes": [
        {
          "id": "node1",
          "role": "部门经理",
          "roleId": "ROLE001",
          "roleName": "部门经理",
          "employees": []
        },
        {
          "id": "node2",
          "role": "财务经理",
          "roleId": "ROLE002",
          "roleName": "财务经理",
          "employees": []
        },
        {
          "id": "node3",
          "role": "总经理",
          "roleId": "ROLE003",
          "roleName": "总经理",
          "employees": []
        }
      ]
    },
    {
      "id": "process2",
      "name": "请假审批流程",
      "amountLimit": null,
      "createBy": "ADMIN",
      "updateTime": "2025-01-02 14:20:00",
      "nodes": [
        {
          "id": "node1",
          "role": "直属主管",
          "employees": []
        },
        {
          "id": "node2",
          "role": "人事经理",
          "employees": []
        }
      ]
    }
  ]
}
```

## 字段说明

### 流程对象 (Process)
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 流程唯一标识 |
| name | string | 是 | 流程名称 |
| amountLimit | number/null | 否 | 金额限制（null表示无限制） |
| createBy | string | 否 | 创建人 |
| updateTime | string | 否 | 更新时间 |
| nodes | array | 是 | 审批节点数组 |

### 节点对象 (Node)
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 节点唯一标识 |
| role | string | 是 | 角色名称（必须与角色.json中的RLNAME匹配） |
| roleId | string | 否 | 角色ID（如果提供，必须与角色.json中的SERIALCOLUMN匹配） |
| roleName | string | 否 | 角色名称（兼容字段） |
| employees | array | 否 | 员工数组（通常为空，系统会自动从角色数据加载） |

## 重要说明

### 1. 员工数据自动加载
节点的 `employees` 字段通常设为空数组 `[]`，系统会自动：
- 根据 `roleId` 查找对应的角色
- 如果没有 `roleId`，则根据 `role` 名称查找角色
- 从角色数据中加载该角色下的所有员工
- 自动填充到节点的 `employees` 数组中

### 2. 角色匹配规则
系统按以下优先级匹配角色：
1. **roleId 匹配**：如果节点有 `roleId`，优先使用 `roleId` 在角色.json中查找
2. **role 名称匹配**：如果没有 `roleId` 或找不到，使用 `role` 字段的值匹配角色名称
3. **roleName 匹配**：兼容旧格式，使用 `roleName` 字段匹配

### 3. 最小化配置示例
如果你的角色.json文件中有正确的角色数据，流程配置可以非常简洁：

```json
{
  "data": [
    {
      "id": "process1",
      "name": "报销审批流程",
      "amountLimit": 10000,
      "nodes": [
        {
          "id": "node1",
          "role": "部门经理"
        },
        {
          "id": "node2",
          "role": "财务经理"
        }
      ]
    }
  ]
}
```

只要 `role` 字段的值与角色.json中某个角色的 `RLNAME` 字段匹配，系统就会自动加载该角色的所有员工。

## 与角色.json的关联

### 角色.json格式示例
```json
{
  "data": [
    {
      "SERIALCOLUMN": "ROLE001",
      "RLNAME": "部门经理",
      "data1": [
        {
          "SERIALCOLUMN": "EMP001",
          "RLUSER": "user001",
          "RUSERNAME": "张三",
          "RDDESC": "销售部经理"
        },
        {
          "SERIALCOLUMN": "EMP002",
          "RLUSER": "user002",
          "RUSERNAME": "李四",
          "RDDESC": "技术部经理"
        }
      ]
    },
    {
      "SERIALCOLUMN": "ROLE002",
      "RLNAME": "财务经理",
      "data1": [
        {
          "SERIALCOLUMN": "EMP003",
          "RLUSER": "user003",
          "RUSERNAME": "王五",
          "RDDESC": "财务经理"
        }
      ]
    }
  ]
}
```

### 关联关系
```
流程.json中的节点
  └─ role: "部门经理"
       │
       └─ 匹配 ─→ 角色.json中的角色
                    └─ RLNAME: "部门经理"
                         └─ data1: [所有该角色的员工]
                              │
                              └─ 自动加载到节点的 employees 数组
```

## 故障排查

### 问题：节点没有显示员工
**可能原因：**
1. ✗ 角色.json文件未加载或加载失败
2. ✗ 节点的 `role` 字段值与角色.json中的 `RLNAME` 不匹配
3. ✗ 角色的 `data1` 数组为空（该角色下没有员工）
4. ✗ 数据加载顺序错误（流程在角色数据加载前就被选中）

**解决方法：**
1. ✓ 检查浏览器控制台，确认角色数据已成功加载
2. ✓ 确保节点的 `role` 字段值与角色名称完全一致（区分大小写）
3. ✓ 检查对应角色的 `data1` 数组是否有员工数据
4. ✓ 确保按正确顺序加载：角色.json → 流程.json → 选择流程

### 调试提示
打开浏览器控制台(F12)，查看日志输出：
```
✓ 成功加载 5 个可用角色
✓ 成功加载 3 个审批流程
✓ 为节点 "部门经理" 加载了 2 名员工
✓ 为节点 "财务经理" 加载了 1 名员工
```

如果看到警告：
```
⚠ 未找到角色 "部门经理" 的员工信息
```
说明角色名称不匹配或角色数据缺失。

## 完整示例

### 流程.json（完整示例）
```json
{
  "data": [
    {
      "id": "expense_approval",
      "name": "报销审批流程",
      "amountLimit": 10000,
      "createBy": "ADMIN",
      "updateTime": "2025-01-01 10:30:00",
      "nodes": [
        {
          "id": "node_dept_manager",
          "role": "部门经理",
          "roleId": "ROLE_DEPT_MGR"
        },
        {
          "id": "node_finance_manager",
          "role": "财务经理",
          "roleId": "ROLE_FIN_MGR"
        },
        {
          "id": "node_general_manager",
          "role": "总经理",
          "roleId": "ROLE_GM"
        }
      ]
    },
    {
      "id": "leave_approval",
      "name": "请假审批流程",
      "amountLimit": null,
      "createBy": "HR_ADMIN",
      "updateTime": "2025-01-02 14:20:00",
      "nodes": [
        {
          "id": "node_direct_supervisor",
          "role": "直属主管"
        },
        {
          "id": "node_hr_manager",
          "role": "人事经理"
        }
      ]
    },
    {
      "id": "purchase_approval",
      "name": "采购审批流程",
      "amountLimit": 50000,
      "createBy": "ADMIN",
      "updateTime": "2025-01-03 09:15:00",
      "nodes": [
        {
          "id": "node_purchase_manager",
          "role": "采购经理"
        },
        {
          "id": "node_finance_manager_2",
          "role": "财务经理"
        },
        {
          "id": "node_general_manager_2",
          "role": "总经理"
        }
      ]
    }
  ]
}
```

这个配置会自动从角色.json中加载每个节点对应角色的所有员工，无需手动配置员工信息。
