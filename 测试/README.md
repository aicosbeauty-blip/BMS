# 员工权限管理系统 - 使用说明

## 📋 项目概述

这是一个全新设计的员工权限管理界面，用于配置员工的审批范围。采用左右分栏对比设计，让权限管理更加直观和高效。

## ✨ 核心特性

### 1. **左右分栏设计**
- **左侧**：显示已授权的部门和公司（绿色主题）
- **右侧**：显示未授权的部门和公司（灰色主题）
- 一目了然地查看授权状态

### 2. **按部门分组展示**
- 根据JSON数据的第二层（部门类型）进行分组
- 每个部门下展示所属的所有公司（第三层CNAMEEN）
- 支持折叠/展开，方便浏览大量数据

### 3. **智能筛选系统**
- **业务板块筛选**：按GROUPID筛选
- **部门类型筛选**：选择特定部门类型
- **关键词搜索**：搜索公司名或部门名
- 实时过滤，无需刷新

### 4. **快速操作**
- **点击公司卡片**：在已授权/未授权之间切换
- **批量授权**：一键授权整个部门
- **批量取消**：一键取消整个部门的授权
- **全部折叠/展开**：便于浏览

### 5. **实时统计**
- 已授权部门数量
- 已授权公司数量
- 未授权部门数量
- 涵盖的业务板块数量

## 📁 文件结构

```
├── employee-permission-modal.html    # 权限管理弹框HTML
├── employee-permission-modal.js      # 权限管理逻辑JS
├── styles.css                        # 样式文件
├── demo.html                         # 演示页面
├── 授权公司.JSON                      # 权限数据文件
└── README.md                         # 说明文档
```

## 📊 JSON数据结构说明

```json
{
  "Y": {                          // 已授权
    "部门类型1": [                // 第二层：部门类型（如"品牌部"）
      {
        "RDEPT": "公司-部门",     // 完整的部门名称
        "CREATEBY": "创建人",
        "CREATEDATE": "创建日期",
        "CNAMEEN": "分公司名称",   // 第三层：分公司
        "GROUPID": "业务板块"      // 业务板块（如"博雅生命"）
      }
    ]
  },
  "N": {                          // 未授权（结构同上）
    "部门类型2": [...]
  }
}
```

### 数据层级说明：
1. **第一层**：Y/N - 表示授权状态
2. **第二层**：部门类型 - 如"品牌部"、"财务部"等
3. **第三层**：CNAMEEN - 分公司名称

## 🚀 快速开始

### 1. 基础集成

在您的HTML中引入必要的文件：

```html
<!-- 引入样式 -->
<link rel="stylesheet" href="styles.css">

<!-- 引入权限弹框HTML -->
<div id="employeePermissionModal"></div>

<!-- 引入脚本 -->
<script src="employee-permission-modal.js"></script>
```

### 2. 初始化模块

```javascript
// 页面加载时初始化，指定JSON文件路径
document.addEventListener('DOMContentLoaded', function() {
    EmployeePermissionModal.init('授权公司.JSON');
});
```

### 3. 打开权限管理面板

```javascript
// 参数：员工姓名、角色名称、员工ID
EmployeePermissionModal.open('张三', '部门经理', 'EMP001');
```

### 4. 监听保存事件

```javascript
document.addEventListener('employeePermissionSaved', function(event) {
    console.log('已保存的权限配置:', event.detail);
    
    // event.detail 包含：
    // - employee: 员工信息
    // - authorized: 已授权的部门列表
    // - permissionData: 完整的权限数据
    
    // 发送到服务器保存
    saveToServer(event.detail);
});
```

## 🎨 UI设计特点

### 1. **颜色系统**
- **橙色**：主题色，用于按钮和强调
- **绿色**：已授权状态
- **灰色**：未授权状态
- **蓝色**：信息提示

### 2. **交互反馈**
- 悬停效果：卡片提升和阴影
- 点击反馈：缩放动画
- 加载状态：旋转图标
- 过渡动画：流畅的切换效果

### 3. **响应式设计**
- 支持桌面、平板、手机
- 自适应宽度调整
- 触摸友好的交互

## 🔧 API接口

### 公开方法

```javascript
// 初始化模块
EmployeePermissionModal.init(jsonUrl)

// 打开权限面板
EmployeePermissionModal.open(employeeName, roleName, employeeId)

// 关闭权限面板
EmployeePermissionModal.close()

// 保存权限配置
EmployeePermissionModal.save()

// 切换公司授权状态
EmployeePermissionModal.toggleCompanyAuthorization(rdept, isAuthorized)

// 授权整个部门
EmployeePermissionModal.moveDeptToAuthorized(deptType)

// 取消整个部门授权
EmployeePermissionModal.moveDeptToUnauthorized(deptType)

// 清空所有授权
EmployeePermissionModal.clearAllAuthorized()

// 授权所有可见项
EmployeePermissionModal.authorizeAllVisible()

// 折叠/展开操作
EmployeePermissionModal.toggleCollapse(side, deptType)
EmployeePermissionModal.expandAll(side)
EmployeePermissionModal.collapseAll(side)

// 获取当前员工信息
EmployeePermissionModal.getCurrentEmployee()

// 获取已授权部门列表
EmployeePermissionModal.getAuthorizedDepartments()
```

## 💡 使用技巧

### 1. **快速授权**
- 点击公司卡片可直接切换授权状态
- 使用部门头部的"授权全部"按钮批量操作

### 2. **高效筛选**
- 先使用业务板块筛选缩小范围
- 再用搜索框精确定位
- 配合折叠功能管理大量数据

### 3. **数据管理**
- 左右对比让授权状态一目了然
- 实时统计显示配置进度
- 保存前可随时调整

### 4. **键盘快捷键**（可扩展）
- ESC：关闭面板
- Ctrl+F：聚焦搜索框
- Ctrl+S：保存配置

## 🔍 常见问题

### Q: 如何加载自定义的JSON文件？
```javascript
EmployeePermissionModal.init('path/to/your/data.json');
```

### Q: 如何自定义样式？
在 `styles.css` 中修改对应的CSS类，或在您的自定义CSS中覆盖。

### Q: 如何处理大量数据？
系统支持筛选和折叠功能，建议：
1. 使用业务板块筛选
2. 配合关键词搜索
3. 折叠不需要的部门

### Q: 如何与后端集成？
监听 `employeePermissionSaved` 事件，将数据发送到服务器：
```javascript
document.addEventListener('employeePermissionSaved', function(event) {
    fetch('/api/save-permissions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(event.detail)
    });
});
```

## 📱 浏览器兼容性

- ✅ Chrome/Edge 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ 移动端浏览器

## 🎯 未来计划

- [ ] 添加拖拽授权功能
- [ ] 支持批量导入/导出
- [ ] 添加操作历史记录
- [ ] 支持权限模板
- [ ] 增加多语言支持

## 📞 技术支持

如有问题或建议，请联系开发团队。

---

**版本**: v2.0  
**最后更新**: 2025-11-06  
**作者**: Claude
