# 文件拆分架构图

## 📊 文件依赖关系

```
┌─────────────────────────────────────────────────────────────┐
│                       index.html                             │
│                     (主HTML文件 4.3KB)                       │
│                      入口页面                                 │
└────────────┬────────────────────────┬────────────────────────┘
             │                        │
             │ 引用                    │ 引用
             ▼                        ▼
    ┌────────────────┐        ┌──────────────────┐
    │  styles.css    │        │  main-logic.js   │
    │  (1.7KB)       │        │  (21KB)          │
    │  全局样式       │        │  主应用逻辑       │
    └────────────────┘        └────────┬─────────┘
                                       │
                                       │ 初始化并使用
                                       ▼
                    ┌──────────────────────────────────────┐
                    │ employee-permission-modal.js         │
                    │ (12KB)                               │
                    │ 员工权限编辑逻辑模块                   │
                    │                                      │
                    │ 公开API:                             │
                    │ • init()                             │
                    │ • open()                             │
                    │ • close()                            │
                    │ • save()                             │
                    │ • toggleDepartment()                 │
                    │ • toggleCompanyDepts()               │
                    │ • selectAllVisible()                 │
                    │ • deselectAllVisible()               │
                    └──────────────┬───────────────────────┘
                                   │
                                   │ 动态加载HTML模板
                                   ▼
                    ┌──────────────────────────────────────┐
                    │ employee-permission-modal.html       │
                    │ (5.4KB)                              │
                    │ 员工权限编辑弹框HTML模板               │
                    └──────────────────────────────────────┘
```

## 🔄 数据流向

```
外部JSON文件
    │
    │ fetch请求
    ▼
┌─────────────────┐
│ main-logic.js   │
│                 │
│ • 角色.json     │ ──────┐
│ • 审批架构.json │        │
│ • 流程.json     │        │ 传递数据
└─────────────────┘        │
                           ▼
        ┌──────────────────────────────────┐
        │ employee-permission-modal.js     │
        │                                  │
        │ EmployeePermissionModal.init()   │
        └──────────────────────────────────┘
                           │
                           │ 触发事件
                           ▼
                  employeePermissionSaved
                           │
                           │ 监听
                           ▼
        ┌──────────────────────────────────┐
        │ main-logic.js                    │
        │ 处理保存后的逻辑                   │
        └──────────────────────────────────┘
```

## 🎯 模块职责划分

### 1. index.html (入口文件)
```
职责: 页面结构定义
├── 头部导航
├── 左侧流程列表
├── 中间编辑画布
├── 右侧角色面板
└── 弹框容器
```

### 2. styles.css (样式管理)
```
职责: 全局样式定义
├── 基础样式
├── 动画效果
├── 组件样式
└── 响应式布局
```

### 3. main-logic.js (主控制器)
```
职责: 核心业务逻辑
├── 数据加载
├── 页面渲染
│   ├── 流程列表
│   ├── 角色列表
│   └── 工作流画布
├── 拖拽处理
├── 节点管理
│   ├── 添加节点
│   ├── 删除节点
│   └── 插入节点
├── 员工管理
└── 流程保存/导出
```

### 4. employee-permission-modal.js (独立模块)
```
职责: 员工权限编辑
├── 模块初始化
├── 弹框控制
│   ├── 打开
│   └── 关闭
├── 数据筛选
│   ├── 业务板块
│   ├── 公司
│   └── 搜索
├── 内容渲染
│   └── 按公司分组
├── 权限管理
│   ├── 切换部门
│   ├── 批量操作
│   └── 保存权限
└── 统计更新
```

### 5. employee-permission-modal.html (UI模板)
```
职责: 弹框界面结构
├── 头部信息
│   ├── 员工信息
│   └── 统计卡片
├── 筛选工具栏
│   ├── 业务板块下拉
│   ├── 公司下拉
│   ├── 搜索框
│   └── 批量按钮
├── 内容区域
│   └── 公司部门列表
└── 底部操作
    ├── 取消按钮
    └── 保存按钮
```

## 📦 文件大小对比

### 拆分前
```
┌────────────────────────────┐
│  原始HTML文件               │
│  ~45KB                     │
│  ~1100行代码               │
└────────────────────────────┘
```

### 拆分后
```
┌─────────────────┐
│ index.html      │  4.3KB  (结构)
└─────────────────┘

┌─────────────────┐
│ styles.css      │  1.7KB  (样式)
└─────────────────┘

┌─────────────────┐
│ main-logic.js   │  21KB   (主逻辑)
└─────────────────┘

┌──────────────────────────────────┐
│ employee-permission-modal.js     │  12KB   (弹框逻辑)
└──────────────────────────────────┘

┌──────────────────────────────────┐
│ employee-permission-modal.html   │  5.4KB  (弹框模板)
└──────────────────────────────────┘

总计: 44.4KB (5个文件)
```

## ⚡ 性能优势

### 1. 按需加载
```
页面初始加载:
  ✓ index.html     (4.3KB)
  ✓ styles.css     (1.7KB)
  ✓ main-logic.js  (21KB)
  ✓ employee-permission-modal.js (12KB)
  ────────────────────────────────
  首次加载: 39KB

弹框首次使用时:
  ✓ employee-permission-modal.html (5.4KB)
  ────────────────────────────────
  动态加载: 5.4KB
```

### 2. 缓存策略
```
浏览器缓存:
  • CSS文件 → 长期缓存 (样式变化少)
  • JS模块 → 按需更新 (逻辑独立)
  • HTML模板 → 按需加载 (一次加载)
```

### 3. 开发效率
```
模块化开发:
  • 样式修改 → 只编辑 CSS
  • 主逻辑修改 → 只编辑 main-logic.js
  • 弹框修改 → 只编辑 modal 相关文件
  • 互不影响，减少冲突
```

## 🔗 通信机制

### JavaScript模块间通信
```javascript
// 主应用调用弹框模块
EmployeePermissionModal.open(name, role, id);

// 弹框模块触发事件给主应用
document.dispatchEvent(
  new CustomEvent('employeePermissionSaved', {
    detail: { employee, departments }
  })
);

// 主应用监听事件
document.addEventListener('employeePermissionSaved', handler);
```

### HTML动态加载
```javascript
// main-logic.js 中的代码
const response = await fetch('employee-permission-modal.html');
modalContainer.innerHTML = await response.text();
```

## 🎨 样式组织

### CSS模块化
```css
/* 基础样式 */
body { ... }

/* 动画效果 */
.sidebar-overlay { ... }
.sidebar-panel { ... }

/* 组件样式 */
.employee-tag { ... }
.company-card { ... }
.dept-checkbox { ... }

/* 功能样式 */
.drop-indicator { ... }
.role-card.dragging { ... }
```

## 📱 响应式设计
```
所有样式都在 styles.css 中统一管理
可以方便地添加媒体查询实现响应式布局

@media (max-width: 768px) {
  /* 移动端样式 */
}
```

## 🚀 扩展建议

### 1. 添加新功能模块
```
按照相同模式创建新模块:
  • 新模块.html  (界面模板)
  • 新模块.js    (逻辑代码)
  • 在 main-logic.js 中集成
```

### 2. 优化建议
```
生产环境:
  • 合并压缩 JS 文件
  • 压缩 CSS 文件
  • 启用 Gzip 压缩
  • 使用 CDN 加速
```

### 3. 代码分割
```
如果 main-logic.js 继续增大:
  • 可以进一步拆分为:
    - data-loader.js     (数据加载)
    - workflow-render.js (工作流渲染)
    - drag-handler.js    (拖拽处理)
```
