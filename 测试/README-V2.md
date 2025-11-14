# 员工权限管理系统 V2.0 - 紧凑卡片版

## 🎉 全新设计

专为新JSON架构优化的权限管理界面，采用紧凑的部门卡片布局，让授权管理更加直观高效！

## ✨ 核心特性

### 1. **紧凑部门卡片**
- 每个部门一张卡片
- 清晰显示已授权/未授权数量
- 进度条可视化授权比例
- 支持网格和列表两种视图

### 2. **点击查看详情**
- 点击任意部门卡片
- 弹出详情窗口
- 查看该部门下所有公司
- 精确管理每个公司的授权状态

### 3. **快速批量操作**
- 卡片上的快捷按钮
- 一键授权整个部门
- 一键取消整个部门授权
- 支持筛选后批量操作

### 4. **智能筛选系统**
- 按业务板块筛选
- 按授权状态筛选（全部/仅已授权/仅未授权/部分授权）
- 关键词搜索
- 实时过滤更新

### 5. **实时统计面板**
- 总部门数
- 已授权公司数
- 未授权公司数
- 覆盖公司数
- 业务板块数

## 📊 新JSON数据结构

### 结构说明

```json
{
  "部门类型1": {
    "Y": [/* 已授权的公司列表 */],
    "N": [/* 未授权的公司列表 */]
  },
  "部门类型2": {
    "Y": [...],
    "N": [...]
  }
}
```

### 层级定义

1. **第一层（部门类型）**
   - 键：部门名称，如"品牌部"、"财务部"、"技术部"等
   - 值：包含Y和N两个数组的对象

2. **第二层（授权状态）**
   - `Y`：已授权的公司列表
   - `N`：未授权的公司列表

3. **第三层（公司数据）**
   - `RDEPT`：完整的部门名称（公司-部门）
   - `CNAMEEN`：分公司名称
   - `GROUPID`：业务板块
   - `CREATEBY`：创建人
   - `CREATEDATE`：创建日期

### 示例数据

```json
{
  "品牌部": {
    "Y": [
      {
        "RDEPT": "北京博雅和瑞-品牌部",
        "CREATEBY": "DANCHEN",
        "CREATEDATE": "2025-09-05",
        "CNAMEEN": "北京博雅和瑞",
        "GROUPID": "集团板块"
      },
      {
        "RDEPT": "博雅干细胞-品牌部",
        "CREATEBY": "DANCHEN",
        "CREATEDATE": "2025-09-05",
        "CNAMEEN": "博雅干细胞",
        "GROUPID": "博雅生命"
      }
    ],
    "N": []
  },
  "财务部": {
    "Y": [],
    "N": [
      {
        "RDEPT": "博雅干细胞-财务部",
        "CNAMEEN": "博雅干细胞",
        "GROUPID": "博雅生命"
      }
    ]
  }
}
```

## 📁 文件清单

```
├── employee-permission-modal-v2.html    # 权限管理弹框HTML（V2）
├── employee-permission-modal-v2.js      # 权限管理逻辑JS（V2）
├── styles-v2.css                        # 样式文件（V2）
├── demo-v2.html                         # 演示页面（V2）
├── 授权公司.JSON                         # 新结构的权限数据
└── README-V2.md                         # 本文档
```

## 🚀 快速开始

### 1. 引入文件

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>权限管理</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <link rel="stylesheet" href="styles-v2.css">
</head>
<body>
    <!-- 权限弹框容器 -->
    <div id="permissionModalContainer"></div>
    
    <!-- 引入脚本 -->
    <script src="employee-permission-modal-v2.js"></script>
    
    <script>
        // 加载权限弹框HTML
        fetch('employee-permission-modal-v2.html')
            .then(response => response.text())
            .then(html => {
                document.getElementById('permissionModalContainer').innerHTML = html;
            });
    </script>
</body>
</html>
```

### 2. 初始化模块

```javascript
// 页面加载时自动初始化
document.addEventListener('DOMContentLoaded', function() {
    EmployeePermissionModal.init('授权公司.JSON');
});
```

### 3. 打开权限面板

```javascript
// 参数：员工姓名、角色名称、员工ID
EmployeePermissionModal.open('张三', '部门经理', 'EMP001');
```

### 4. 监听保存事件

```javascript
document.addEventListener('employeePermissionSaved', function(event) {
    console.log('保存的权限:', event.detail);
    // event.detail 包含：
    // - employee: 员工信息
    // - authorized: 已授权列表
    // - permissionData: 完整的权限数据
});
```

## 🎨 UI设计特点

### 部门卡片设计

每个部门卡片包含：

1. **头部区域**
   - 部门图标
   - 部门名称
   - 业务板块标签
   - 状态颜色（绿色=全授权，橙色=部分授权，灰色=未授权）

2. **统计区域**
   - 授权进度条（百分比可视化）
   - 已授权数量（绿色）
   - 未授权数量（灰色）
   - 总计数量（蓝色）

3. **操作区域**
   - 快速授权按钮
   - 快速取消按钮
   - 点击查看提示

### 颜色系统

- **绿色**：已授权、完全授权
- **橙色**：部分授权、主题色
- **灰色**：未授权
- **蓝色**：信息提示、统计
- **红色**：取消操作

### 响应式设计

- **XL屏幕（≥1280px）**：4列网格
- **LG屏幕（≥1024px）**：3列网格
- **MD屏幕（≥768px）**：2列网格
- **SM屏幕（<768px）**：1列网格

## 🔧 API接口

### 公开方法

```javascript
// 初始化
EmployeePermissionModal.init(jsonUrl)

// 打开/关闭
EmployeePermissionModal.open(employeeName, roleName, employeeId)
EmployeePermissionModal.close()

// 部门详情
EmployeePermissionModal.openDeptDetail(deptName)
EmployeePermissionModal.closeDeptDetail()

// 单个操作
EmployeePermissionModal.toggleCompany(deptName, rdept, isAuthorized)

// 批量操作
EmployeePermissionModal.addAllFromDept()          // 详情窗口中授权全部
EmployeePermissionModal.removeAllFromDept()       // 详情窗口中取消全部
EmployeePermissionModal.addAllFromDeptQuick(deptName)     // 快速授权
EmployeePermissionModal.removeAllFromDeptQuick(deptName)  // 快速取消
EmployeePermissionModal.authorizeAllVisible()     // 授权所有可见
EmployeePermissionModal.clearAllAuthorized()      // 清空所有授权

// 视图模式
EmployeePermissionModal.setViewMode('grid' | 'list')

// 数据获取
EmployeePermissionModal.getCurrentEmployee()
EmployeePermissionModal.getAuthorizedDepartments()

// 保存
EmployeePermissionModal.save()
```

## 💡 使用技巧

### 1. 快速浏览

- 使用网格视图快速浏览所有部门
- 通过进度条和颜色快速识别授权状态
- 使用筛选器快速定位目标部门

### 2. 批量操作

- 对于需要全部授权的部门，直接点击"授权全部"按钮
- 使用"授权状态"筛选器找出所有未授权部门，然后批量授权
- 先筛选后操作，提高效率

### 3. 精细管理

- 点击部门卡片进入详情
- 在详情中逐一管理每个公司
- 可以看到完整的公司信息（CNAMEEN、GROUPID等）

### 4. 数据验证

- 黄色警告标识未设置公司名的条目
- 顶部统计实时更新
- 保存前可随时调整

## 🔍 常见问题

### Q: 如何处理大量部门？

**A**: 使用筛选功能：
1. 先按业务板块筛选
2. 再使用授权状态筛选
3. 配合搜索框精确定位
4. 支持网格和列表两种视图

### Q: 如何批量授权？

**A**: 三种方式：
1. 卡片快捷按钮（单个部门）
2. 顶部"全部授权"按钮（所有可见）
3. 详情窗口内的批量按钮

### Q: 数据如何保存？

**A**: 监听事件并发送到服务器：
```javascript
document.addEventListener('employeePermissionSaved', function(event) {
    fetch('/api/save-permissions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(event.detail)
    });
});
```

### Q: 如何自定义样式？

**A**: 修改 `styles-v2.css` 或在自定义CSS中覆盖：
```css
.dept-card {
    /* 自定义卡片样式 */
}
```

## 📊 与V1.0的区别

| 特性 | V1.0 | V2.0 |
|-----|------|------|
| JSON结构 | FLAG字段标识 | Y/N分组 |
| 布局方式 | 左右分栏对比 | 卡片网格 |
| 主要展示 | 公司列表 | 部门卡片 |
| 数量显示 | 分栏统计 | 卡片内统计 |
| 详情查看 | 内联展开 | 弹窗查看 |
| 适用场景 | 少量数据 | 大量数据 |
| 信息密度 | 较低 | 较高 |
| 操作效率 | 中等 | 高 |

## 🎯 适用场景

### V2.0 更适合：

- ✅ 部门数量较多（20+）
- ✅ 需要快速浏览全局
- ✅ 频繁的批量操作
- ✅ 移动端访问
- ✅ 强调授权进度

### V1.0 更适合：

- ✅ 需要详细对比已授权/未授权
- ✅ 部门数量较少（<20）
- ✅ 需要同时查看多个部门
- ✅ 强调授权状态差异

## 🌟 最佳实践

1. **首次配置**
   - 使用业务板块筛选器逐个板块配置
   - 利用批量操作快速授权整个部门
   - 最后使用搜索精确调整

2. **定期维护**
   - 使用"部分授权"筛选找出需要检查的部门
   - 点击进入详情逐一确认
   - 及时清理不需要的授权

3. **权限审计**
   - 导出授权数据定期备份
   - 使用统计数据了解授权范围
   - 对比不同员工的授权差异

## 📞 技术支持

如有问题或建议，请联系开发团队。

---

**版本**: V2.0  
**发布日期**: 2025-11-06  
**作者**: Claude  
**兼容**: Chrome 90+, Firefox 88+, Safari 14+
