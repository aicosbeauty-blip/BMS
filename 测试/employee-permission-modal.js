/**
 * 员工权限编辑弹框模块 - 改进版
 * 支持从JSON文件加载数据，左右分栏显示已授权/未授权
 */
const EmployeePermissionModal = (function() {
    // 私有变量
    let currentEmployee = null;
    let permissionData = { Y: {}, N: {} }; // 完整的权限数据
    let filteredAuthorized = []; // 筛选后的已授权数据
    let filteredUnauthorized = []; // 筛选后的未授权数据
    let isInitialized = false;
    let viewMode = 'split'; // 'split' 或 'all'
    let collapsedStates = {
        authorized: {},
        unauthorized: {}
    };

    /**
     * 初始化模块
     * @param {string} jsonUrl - JSON数据文件路径
     */
    async function init(jsonUrl = '授权公司.JSON') {
        if (isInitialized) return;
        
        try {
            // 加载JSON数据
            const response = await fetch(jsonUrl);
            permissionData = await response.json();
            
            // 绑定事件监听器
            bindEventListeners();
            
            isInitialized = true;
            console.log('✓ 员工权限编辑模块已初始化', permissionData);
        } catch (error) {
            console.error('❌ 加载权限数据失败:', error);
            alert('加载权限数据失败，请检查JSON文件路径');
        }
    }

    /**
     * 绑定事件监听器
     */
    function bindEventListeners() {
        // 点击遮罩层关闭
        const overlay = document.getElementById('permissionSidebar');
        if (overlay) {
            overlay.addEventListener('click', function(e) {
                if (e.target === this) {
                    close();
                }
            });
        }

        // 筛选器事件
        const groupFilter = document.getElementById('sidebarGroupFilter');
        const deptFilter = document.getElementById('sidebarDeptFilter');
        const searchInput = document.getElementById('sidebarSearchInput');

        if (groupFilter) groupFilter.addEventListener('change', applyFilters);
        if (deptFilter) deptFilter.addEventListener('change', applyFilters);
        if (searchInput) searchInput.addEventListener('input', applyFilters);
    }

    /**
     * 打开员工权限编辑面板
     * @param {string} employeeName - 员工姓名
     * @param {string} roleName - 角色名称
     * @param {string} employeeId - 员工ID
     */
    function open(employeeName, roleName, employeeId) {
        currentEmployee = {
            id: employeeId,
            name: employeeName,
            role: roleName
        };
        
        // 更新侧边栏标题
        document.getElementById('sidebarEmployeeName').textContent = employeeName;
        document.getElementById('sidebarEmployeeRole').textContent = `${roleName} - 配置审批范围`;
        
        // 显示侧边栏
        const overlay = document.getElementById('permissionSidebar');
        const panel = overlay.querySelector('.sidebar-panel');
        
        overlay.classList.remove('hidden');
        setTimeout(() => {
            overlay.style.opacity = '1';
            panel.classList.remove('closed');
        }, 10);
        
        // 初始化数据
        initializeFilters();
        applyFilters();
        updateStatistics();
    }

    /**
     * 关闭权限编辑面板
     */
    function close() {
        const overlay = document.getElementById('permissionSidebar');
        const panel = overlay.querySelector('.sidebar-panel');
        
        overlay.style.opacity = '0';
        panel.classList.add('closed');
        
        setTimeout(() => {
            overlay.classList.add('hidden');
        }, 300);
    }

    /**
     * 初始化筛选器选项
     */
    function initializeFilters() {
        // 收集所有业务板块
        const groupIds = new Set();
        const deptTypes = new Set();

        Object.values(permissionData.Y || {}).forEach(depts => {
            Object.keys(depts).forEach(dept => deptTypes.add(dept));
            depts.forEach(d => {
                if (d.GROUPID) groupIds.add(d.GROUPID);
            });
        });

        Object.values(permissionData.N || {}).forEach(depts => {
            Object.keys(depts).forEach(dept => deptTypes.add(dept));
            depts.forEach(d => {
                if (d.GROUPID) groupIds.add(d.GROUPID);
            });
        });

        // 填充业务板块选项
        const groupSelect = document.getElementById('sidebarGroupFilter');
        groupSelect.innerHTML = '<option value="">全部板块</option>';
        Array.from(groupIds).sort().forEach(group => {
            const option = document.createElement('option');
            option.value = group;
            option.textContent = group;
            groupSelect.appendChild(option);
        });

        // 填充部门类型选项
        const deptSelect = document.getElementById('sidebarDeptFilter');
        deptSelect.innerHTML = '<option value="">全部部门</option>';
        Array.from(deptTypes).sort().forEach(dept => {
            const option = document.createElement('option');
            option.value = dept;
            option.textContent = dept;
            deptSelect.appendChild(option);
        });
    }

    /**
     * 应用筛选条件
     */
    function applyFilters() {
        const groupFilter = document.getElementById('sidebarGroupFilter').value;
        const deptFilter = document.getElementById('sidebarDeptFilter').value;
        const searchTerm = document.getElementById('sidebarSearchInput').value.toLowerCase();

        // 筛选已授权数据
        filteredAuthorized = filterData(permissionData.Y || {}, groupFilter, deptFilter, searchTerm);
        
        // 筛选未授权数据
        filteredUnauthorized = filterData(permissionData.N || {}, groupFilter, deptFilter, searchTerm);

        // 渲染内容
        renderContent();
        updateStatistics();
    }

    /**
     * 筛选数据
     */
    function filterData(data, groupFilter, deptFilter, searchTerm) {
        const filtered = {};

        Object.keys(data).forEach(deptType => {
            if (deptFilter && deptType !== deptFilter) return;

            const companies = data[deptType];
            const filteredCompanies = companies.filter(company => {
                if (groupFilter && company.GROUPID !== groupFilter) return false;
                if (searchTerm) {
                    const matchRdept = (company.RDEPT || '').toLowerCase().includes(searchTerm);
                    const matchCompany = (company.CNAMEEN || '').toLowerCase().includes(searchTerm);
                    if (!matchRdept && !matchCompany) return false;
                }
                return true;
            });

            if (filteredCompanies.length > 0) {
                filtered[deptType] = filteredCompanies;
            }
        });

        return filtered;
    }

    /**
     * 渲染内容
     */
    function renderContent() {
        renderSide('authorized', filteredAuthorized);
        renderSide('unauthorized', filteredUnauthorized);
        
        // 更新计数
        document.getElementById('leftCount').textContent = countItems(filteredAuthorized);
        document.getElementById('rightCount').textContent = countItems(filteredUnauthorized);
    }

    /**
     * 渲染单侧内容
     */
    function renderSide(side, data) {
        const containerId = side === 'authorized' ? 'authorizedContent' : 'unauthorizedContent';
        const container = document.getElementById(containerId);
        const isAuthorized = side === 'authorized';

        if (Object.keys(data).length === 0) {
            container.innerHTML = `
                <div class="text-center py-12 text-gray-400">
                    <i class="fas fa-inbox text-5xl mb-4"></i>
                    <p class="text-lg">暂无数据</p>
                </div>
            `;
            return;
        }

        container.innerHTML = Object.keys(data).map(deptType => {
            const companies = data[deptType];
            const isCollapsed = collapsedStates[side][deptType] || false;
            
            return `
                <div class="dept-group mb-4 bg-white rounded-lg border-2 ${isAuthorized ? 'border-green-200' : 'border-gray-200'} overflow-hidden shadow-sm hover:shadow-md transition-all">
                    
                    <!-- 部门类型头部 -->
                    <div class="dept-header bg-gradient-to-r ${isAuthorized ? 'from-green-50 to-green-100' : 'from-gray-50 to-gray-100'} p-4 cursor-pointer border-b ${isAuthorized ? 'border-green-200' : 'border-gray-200'}"
                         onclick="EmployeePermissionModal.toggleCollapse('${side}', '${deptType}')">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center gap-3">
                                <i class="fas ${isCollapsed ? 'fa-chevron-right' : 'fa-chevron-down'} ${isAuthorized ? 'text-green-600' : 'text-gray-600'} transition-transform"></i>
                                <div class="flex items-center gap-2">
                                    <div class="w-10 h-10 ${isAuthorized ? 'bg-green-500' : 'bg-gray-500'} rounded-lg flex items-center justify-center">
                                        <i class="fas fa-sitemap text-white"></i>
                                    </div>
                                    <div>
                                        <h4 class="font-bold ${isAuthorized ? 'text-green-900' : 'text-gray-900'} text-lg">${deptType}</h4>
                                        <p class="text-xs ${isAuthorized ? 'text-green-600' : 'text-gray-500'}">${companies.length} 个公司</p>
                                    </div>
                                </div>
                            </div>
                            <div class="flex items-center gap-2">
                                ${isAuthorized ? `
                                    <button onclick="event.stopPropagation(); EmployeePermissionModal.moveDeptToUnauthorized('${deptType}')" 
                                            class="px-3 py-1.5 text-xs bg-red-50 border border-red-300 text-red-700 rounded-lg hover:bg-red-100 transition">
                                        <i class="fas fa-times-circle mr-1"></i>取消授权
                                    </button>
                                ` : `
                                    <button onclick="event.stopPropagation(); EmployeePermissionModal.moveDeptToAuthorized('${deptType}')" 
                                            class="px-3 py-1.5 text-xs bg-green-50 border border-green-300 text-green-700 rounded-lg hover:bg-green-100 transition">
                                        <i class="fas fa-check-circle mr-1"></i>授权全部
                                    </button>
                                `}
                            </div>
                        </div>
                    </div>

                    <!-- 公司列表 -->
                    <div class="company-list p-3 space-y-2 ${isCollapsed ? 'hidden' : ''}">
                        ${companies.map(company => renderCompanyCard(company, isAuthorized)).join('')}
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * 渲染公司卡片
     */
    function renderCompanyCard(company, isAuthorized) {
        const hasGroup = company.GROUPID && company.GROUPID.trim() !== '';
        const hasCompany = company.CNAMEEN && company.CNAMEEN.trim() !== '';
        
        return `
            <div class="company-card group bg-gradient-to-br ${isAuthorized ? 'from-green-50 to-white border-green-200 hover:border-green-400' : 'from-gray-50 to-white border-gray-200 hover:border-gray-400'} border-2 rounded-lg p-3 cursor-pointer transition-all hover:shadow-lg"
                 onclick="EmployeePermissionModal.toggleCompanyAuthorization('${company.RDEPT}', ${isAuthorized})">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-3 flex-1">
                        <div class="w-8 h-8 ${isAuthorized ? 'bg-green-500' : 'bg-gray-400'} rounded-lg flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                            <i class="fas fa-building text-white text-sm"></i>
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="font-semibold ${isAuthorized ? 'text-green-900' : 'text-gray-900'} truncate">
                                ${company.RDEPT}
                            </div>
                            <div class="flex items-center gap-2 mt-1 text-xs ${isAuthorized ? 'text-green-600' : 'text-gray-500'}">
                                ${hasCompany ? `
                                    <span class="flex items-center gap-1">
                                        <i class="fas fa-building"></i>${company.CNAMEEN}
                                    </span>
                                ` : '<span class="text-yellow-600"><i class="fas fa-exclamation-triangle"></i>未设置公司</span>'}
                                ${hasGroup ? `
                                    <span class="flex items-center gap-1">
                                        <i class="fas fa-layer-group"></i>${company.GROUPID}
                                    </span>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                    <div class="flex items-center gap-2">
                        ${isAuthorized ? `
                            <span class="px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-medium">
                                <i class="fas fa-check mr-1"></i>已授权
                            </span>
                        ` : `
                            <span class="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs font-medium group-hover:bg-green-100 group-hover:text-green-700 transition-colors">
                                <i class="fas fa-plus mr-1"></i>点击授权
                            </span>
                        `}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * 切换折叠状态
     */
    function toggleCollapse(side, deptType) {
        collapsedStates[side][deptType] = !collapsedStates[side][deptType];
        renderContent();
    }

    /**
     * 展开/折叠所有
     */
    function expandAll(side) {
        collapsedStates[side] = {};
        renderContent();
    }

    function collapseAll(side) {
        const data = side === 'authorized' ? filteredAuthorized : filteredUnauthorized;
        Object.keys(data).forEach(deptType => {
            collapsedStates[side][deptType] = true;
        });
        renderContent();
    }

    /**
     * 切换公司授权状态
     */
    function toggleCompanyAuthorization(rdept, currentlyAuthorized) {
        // 从当前状态移除
        const sourceKey = currentlyAuthorized ? 'Y' : 'N';
        const targetKey = currentlyAuthorized ? 'N' : 'Y';
        
        let movedCompany = null;
        let sourceDeptType = null;

        // 查找并移除
        Object.keys(permissionData[sourceKey]).forEach(deptType => {
            const companies = permissionData[sourceKey][deptType];
            const index = companies.findIndex(c => c.RDEPT === rdept);
            if (index !== -1) {
                movedCompany = companies.splice(index, 1)[0];
                sourceDeptType = deptType;
                if (companies.length === 0) {
                    delete permissionData[sourceKey][deptType];
                }
            }
        });

        // 添加到目标
        if (movedCompany && sourceDeptType) {
            if (!permissionData[targetKey][sourceDeptType]) {
                permissionData[targetKey][sourceDeptType] = [];
            }
            permissionData[targetKey][sourceDeptType].push(movedCompany);
        }

        // 重新应用筛选和渲染
        applyFilters();
        updateStatistics();
    }

    /**
     * 移动整个部门到已授权
     */
    function moveDeptToAuthorized(deptType) {
        if (permissionData.N[deptType]) {
            if (!permissionData.Y[deptType]) {
                permissionData.Y[deptType] = [];
            }
            permissionData.Y[deptType] = permissionData.Y[deptType].concat(permissionData.N[deptType]);
            delete permissionData.N[deptType];
            applyFilters();
            updateStatistics();
        }
    }

    /**
     * 移动整个部门到未授权
     */
    function moveDeptToUnauthorized(deptType) {
        if (permissionData.Y[deptType]) {
            if (!permissionData.N[deptType]) {
                permissionData.N[deptType] = [];
            }
            permissionData.N[deptType] = permissionData.N[deptType].concat(permissionData.Y[deptType]);
            delete permissionData.Y[deptType];
            applyFilters();
            updateStatistics();
        }
    }

    /**
     * 清空所有授权
     */
    function clearAllAuthorized() {
        if (!confirm('确定要清空所有授权吗？')) return;
        
        Object.keys(permissionData.Y).forEach(deptType => {
            if (!permissionData.N[deptType]) {
                permissionData.N[deptType] = [];
            }
            permissionData.N[deptType] = permissionData.N[deptType].concat(permissionData.Y[deptType]);
        });
        permissionData.Y = {};
        
        applyFilters();
        updateStatistics();
    }

    /**
     * 授权所有可见项
     */
    function authorizeAllVisible() {
        if (!confirm('确定要授权所有可见的未授权项吗？')) return;

        Object.keys(filteredUnauthorized).forEach(deptType => {
            if (!permissionData.Y[deptType]) {
                permissionData.Y[deptType] = [];
            }
            permissionData.Y[deptType] = permissionData.Y[deptType].concat(filteredUnauthorized[deptType]);
            
            // 从N中移除
            if (permissionData.N[deptType]) {
                filteredUnauthorized[deptType].forEach(company => {
                    const index = permissionData.N[deptType].findIndex(c => c.RDEPT === company.RDEPT);
                    if (index !== -1) {
                        permissionData.N[deptType].splice(index, 1);
                    }
                });
                if (permissionData.N[deptType].length === 0) {
                    delete permissionData.N[deptType];
                }
            }
        });

        applyFilters();
        updateStatistics();
    }

    /**
     * 设置视图模式
     */
    function setViewMode(mode) {
        viewMode = mode;
        
        const splitBtn = document.getElementById('viewSplitBtn');
        const allBtn = document.getElementById('viewAllBtn');
        
        if (mode === 'split') {
            splitBtn.className = 'px-3 py-2 text-sm bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-all';
            allBtn.className = 'px-3 py-2 text-sm border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-all';
        } else {
            splitBtn.className = 'px-3 py-2 text-sm border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-all';
            allBtn.className = 'px-3 py-2 text-sm bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-all';
        }
        
        // TODO: 实现全部显示视图
        alert('全部显示视图功能待实现');
    }

    /**
     * 计数
     */
    function countItems(data) {
        return Object.values(data).reduce((sum, arr) => sum + arr.length, 0);
    }

    /**
     * 更新统计信息
     */
    function updateStatistics() {
        // 统计已授权
        const authorizedDepts = Object.keys(permissionData.Y || {});
        const authorizedCompanies = new Set();
        const authorizedCount = Object.values(permissionData.Y || {}).reduce((sum, arr) => {
            arr.forEach(c => {
                if (c.CNAMEEN) authorizedCompanies.add(c.CNAMEEN);
            });
            return sum + arr.length;
        }, 0);

        // 统计未授权
        const unauthorizedCount = Object.values(permissionData.N || {}).reduce((sum, arr) => sum + arr.length, 0);

        // 统计业务板块
        const allGroups = new Set();
        [...Object.values(permissionData.Y || {}), ...Object.values(permissionData.N || {})].forEach(arr => {
            arr.forEach(c => {
                if (c.GROUPID) allGroups.add(c.GROUPID);
            });
        });

        document.getElementById('authorizedDeptCount').textContent = authorizedCount;
        document.getElementById('authorizedCompanyCount').textContent = authorizedCompanies.size;
        document.getElementById('unauthorizedDeptCount').textContent = unauthorizedCount;
        document.getElementById('totalGroupCount').textContent = allGroups.size;
    }

    /**
     * 保存员工权限
     */
    function save() {
        const authorizedList = [];
        Object.keys(permissionData.Y || {}).forEach(deptType => {
            permissionData.Y[deptType].forEach(company => {
                authorizedList.push({
                    deptType: deptType,
                    ...company
                });
            });
        });

        console.log('保存员工权限:', {
            employee: currentEmployee,
            authorized: authorizedList,
            totalCount: authorizedList.length
        });

        // 触发自定义事件
        const event = new CustomEvent('employeePermissionSaved', {
            detail: {
                employee: currentEmployee,
                authorized: authorizedList,
                permissionData: permissionData
            }
        });
        document.dispatchEvent(event);

        alert(`已为 ${currentEmployee.name} 配置 ${authorizedList.length} 个部门的审批权限`);
        close();
    }

    /**
     * 获取当前员工信息
     */
    function getCurrentEmployee() {
        return currentEmployee;
    }

    /**
     * 获取已授权的部门列表
     */
    function getAuthorizedDepartments() {
        const list = [];
        Object.keys(permissionData.Y || {}).forEach(deptType => {
            permissionData.Y[deptType].forEach(company => {
                list.push({
                    deptType: deptType,
                    ...company
                });
            });
        });
        return list;
    }

    // 公开的API
    return {
        init,
        open,
        close,
        save,
        toggleCompanyAuthorization,
        moveDeptToAuthorized,
        moveDeptToUnauthorized,
        clearAllAuthorized,
        authorizeAllVisible,
        toggleCollapse,
        expandAll,
        collapseAll,
        setViewMode,
        getCurrentEmployee,
        getAuthorizedDepartments
    };
})();

// 页面加载时初始化模块
document.addEventListener('DOMContentLoaded', function() {
    EmployeePermissionModal.init('授权公司.JSON');
});
