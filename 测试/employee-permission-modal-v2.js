/**
 * 员工权限编辑弹框模块 - V2 紧凑卡片版
 * 支持新的JSON结构：部门 > Y/N > 公司列表
 */
const EmployeePermissionModal = (function() {
    // 私有变量
    let currentEmployee = null;
    let permissionData = {}; // 完整的权限数据
    let filteredDepts = []; // 筛选后的部门列表
    let isInitialized = false;
    let viewMode = 'grid'; // 'grid' 或 'list'
    let currentDeptName = null; // 当前查看的部门

    /**
     * 初始化模块
     * @param {string} jsonUrl - JSON数据文件路径
     */
    async function init(jsonUrl = '授权公司.JSON') {
        if (isInitialized) return;
        
        try {
            // 加载JSON数据
            const response = await fetch(jsonUrl);
            const data = await response.json();
            
            // 移除description字段，只保留部门数据
            delete data.description;
            permissionData = data;
            
            // 绑定事件监听器
            bindEventListeners();
            
            isInitialized = true;
            console.log('✓ 员工权限编辑模块已初始化 (V2)', permissionData);
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

        const detailModal = document.getElementById('deptDetailModal');
        if (detailModal) {
            detailModal.addEventListener('click', function(e) {
                if (e.target === this) {
                    closeDeptDetail();
                }
            });
        }

        // 筛选器事件
        const groupFilter = document.getElementById('sidebarGroupFilter');
        const statusFilter = document.getElementById('sidebarStatusFilter');
        const searchInput = document.getElementById('sidebarSearchInput');

        if (groupFilter) groupFilter.addEventListener('change', applyFilters);
        if (statusFilter) statusFilter.addEventListener('change', applyFilters);
        if (searchInput) searchInput.addEventListener('input', applyFilters);
    }

    /**
     * 打开员工权限编辑面板
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

        Object.keys(permissionData).forEach(deptName => {
            const dept = permissionData[deptName];
            ['Y', 'N'].forEach(status => {
                if (dept[status]) {
                    dept[status].forEach(company => {
                        if (company.GROUPID) groupIds.add(company.GROUPID);
                    });
                }
            });
        });

        // 填充业务板块选项
        const groupSelect = document.getElementById('sidebarGroupFilter');
        groupSelect.innerHTML = '<option value="">全部</option>';
        Array.from(groupIds).sort().forEach(group => {
            const option = document.createElement('option');
            option.value = group;
            option.textContent = group;
            groupSelect.appendChild(option);
        });
    }

    /**
     * 应用筛选条件
     */
    function applyFilters() {
        const groupFilter = document.getElementById('sidebarGroupFilter').value;
        const statusFilter = document.getElementById('sidebarStatusFilter').value;
        const searchTerm = document.getElementById('sidebarSearchInput').value.toLowerCase();

        filteredDepts = Object.keys(permissionData).filter(deptName => {
            const dept = permissionData[deptName];
            
            // 搜索过滤
            if (searchTerm) {
                const matchDept = deptName.toLowerCase().includes(searchTerm);
                const matchCompany = hasMatchingCompany(dept, searchTerm);
                if (!matchDept && !matchCompany) return false;
            }

            // 业务板块过滤
            if (groupFilter && !hasMatchingGroup(dept, groupFilter)) {
                return false;
            }

            // 授权状态过滤
            if (statusFilter) {
                const yCount = (dept.Y || []).length;
                const nCount = (dept.N || []).length;
                
                if (statusFilter === 'authorized' && yCount === 0) return false;
                if (statusFilter === 'unauthorized' && nCount === 0) return false;
                if (statusFilter === 'partial' && (yCount === 0 || nCount === 0)) return false;
            }

            return true;
        }).sort();

        renderDepartmentGrid();
        updateStatistics();
    }

    /**
     * 检查部门是否有匹配的公司
     */
    function hasMatchingCompany(dept, searchTerm) {
        const allCompanies = [...(dept.Y || []), ...(dept.N || [])];
        return allCompanies.some(c => 
            (c.RDEPT || '').toLowerCase().includes(searchTerm) ||
            (c.CNAMEEN || '').toLowerCase().includes(searchTerm)
        );
    }

    /**
     * 检查部门是否有匹配的业务板块
     */
    function hasMatchingGroup(dept, groupId) {
        const allCompanies = [...(dept.Y || []), ...(dept.N || [])];
        return allCompanies.some(c => c.GROUPID === groupId);
    }

    /**
     * 渲染部门网格
     */
    function renderDepartmentGrid() {
        const container = document.getElementById('departmentGrid');
        const emptyState = document.getElementById('emptyState');

        if (filteredDepts.length === 0) {
            container.classList.add('hidden');
            emptyState.classList.remove('hidden');
            return;
        }

        container.classList.remove('hidden');
        emptyState.classList.add('hidden');

        container.innerHTML = filteredDepts.map(deptName => {
            const dept = permissionData[deptName];
            const yCount = (dept.Y || []).length;
            const nCount = (dept.N || []).length;
            const total = yCount + nCount;
            const percentage = total > 0 ? Math.round((yCount / total) * 100) : 0;

            // 获取主要业务板块
            const allCompanies = [...(dept.Y || []), ...(dept.N || [])];
            const groups = [...new Set(allCompanies.map(c => c.GROUPID).filter(g => g))];
            const primaryGroup = groups[0] || '未分类';

            return `
                <div class="dept-card bg-white rounded-xl border-2 ${
                    yCount > 0 && nCount === 0 ? 'border-green-400' :
                    yCount === 0 && nCount > 0 ? 'border-gray-300' :
                    'border-orange-400'
                } hover:shadow-xl transition-all cursor-pointer overflow-hidden"
                     onclick="EmployeePermissionModal.openDeptDetail('${deptName}')">
                    
                    <!-- 部门头部 -->
                    <div class="p-3 border-b border-gray-200 bg-gradient-to-r ${
                        yCount > 0 && nCount === 0 ? 'from-green-50 to-green-100' :
                        yCount === 0 && nCount > 0 ? 'from-gray-50 to-gray-100' :
                        'from-orange-50 to-orange-100'
                    }">
                        <div class="flex items-start gap-2">
                            <div class="w-9 h-9 ${
                                yCount > 0 && nCount === 0 ? 'bg-green-500' :
                                yCount === 0 && nCount > 0 ? 'bg-gray-400' :
                                'bg-orange-500'
                            } rounded-lg flex items-center justify-center flex-shrink-0">
                                <i class="fas fa-sitemap text-white text-sm"></i>
                            </div>
                            <div class="flex-1 min-w-0">
                                <h3 class="font-bold text-gray-900 text-sm leading-tight truncate" title="${deptName}">
                                    ${deptName}
                                </h3>
                                <div class="flex items-center gap-1 mt-1">
                                    <span class="px-1.5 py-0.5 bg-white bg-opacity-70 rounded text-xs font-medium text-gray-600">
                                        <i class="fas fa-layer-group text-xs"></i> ${primaryGroup}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 统计信息 -->
                    <div class="p-3">
                        <!-- 进度条 -->
                        <div class="mb-2">
                            <div class="flex items-center justify-between text-xs mb-1">
                                <span class="text-gray-600 font-medium">授权进度</span>
                                <span class="font-bold ${percentage === 100 ? 'text-green-600' : percentage === 0 ? 'text-gray-500' : 'text-orange-600'}">
                                    ${percentage}%
                                </span>
                            </div>
                            <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
                                <div class="h-full ${
                                    percentage === 100 ? 'bg-green-500' :
                                    percentage === 0 ? 'bg-gray-400' :
                                    'bg-orange-500'
                                } transition-all duration-500" style="width: ${percentage}%"></div>
                            </div>
                        </div>

                        <!-- 数量统计 -->
                        <div class="grid grid-cols-3 gap-2">
                            <div class="text-center p-2 bg-green-50 rounded-lg border border-green-200">
                                <div class="text-xs text-green-600 mb-1">已授权</div>
                                <div class="text-lg font-bold text-green-700">${yCount}</div>
                            </div>
                            <div class="text-center p-2 bg-gray-50 rounded-lg border border-gray-200">
                                <div class="text-xs text-gray-600 mb-1">未授权</div>
                                <div class="text-lg font-bold text-gray-700">${nCount}</div>
                            </div>
                            <div class="text-center p-2 bg-blue-50 rounded-lg border border-blue-200">
                                <div class="text-xs text-blue-600 mb-1">总计</div>
                                <div class="text-lg font-bold text-blue-700">${total}</div>
                            </div>
                        </div>
                    </div>

                    <!-- 快速操作 -->
                    <div class="px-3 pb-3 flex gap-2">
                        ${yCount === total ? `
                            <button onclick="event.stopPropagation(); EmployeePermissionModal.removeAllFromDeptQuick('${deptName}')"
                                    class="flex-1 px-2 py-1.5 text-xs bg-red-50 border border-red-300 text-red-700 rounded hover:bg-red-100 transition font-medium">
                                <i class="fas fa-times-circle mr-1"></i>取消全部
                            </button>
                        ` : nCount === total ? `
                            <button onclick="event.stopPropagation(); EmployeePermissionModal.addAllFromDeptQuick('${deptName}')"
                                    class="flex-1 px-2 py-1.5 text-xs bg-green-50 border border-green-300 text-green-700 rounded hover:bg-green-100 transition font-medium">
                                <i class="fas fa-check-circle mr-1"></i>授权全部
                            </button>
                        ` : `
                            <button onclick="event.stopPropagation(); EmployeePermissionModal.addAllFromDeptQuick('${deptName}')"
                                    class="flex-1 px-2 py-1.5 text-xs bg-green-50 border border-green-300 text-green-700 rounded hover:bg-green-100 transition font-medium">
                                <i class="fas fa-plus mr-1"></i>授权
                            </button>
                            <button onclick="event.stopPropagation(); EmployeePermissionModal.removeAllFromDeptQuick('${deptName}')"
                                    class="flex-1 px-2 py-1.5 text-xs bg-red-50 border border-red-300 text-red-700 rounded hover:bg-red-100 transition font-medium">
                                <i class="fas fa-minus mr-1"></i>取消
                            </button>
                        `}
                    </div>

                    <!-- 点击查看提示 -->
                    <div class="px-3 pb-2 text-center">
                        <span class="text-xs text-gray-400 italic">
                            <i class="fas fa-hand-pointer"></i> 点击查看详情
                        </span>
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * 打开部门详情弹窗
     */
    function openDeptDetail(deptName) {
        currentDeptName = deptName;
        const dept = permissionData[deptName];
        
        document.getElementById('detailDeptName').textContent = deptName;
        
        const yList = dept.Y || [];
        const nList = dept.N || [];
        
        document.getElementById('detailAuthorizedCount').textContent = yList.length;
        document.getElementById('detailUnauthorizedCount').textContent = nList.length;
        document.getElementById('detailTotalCount').textContent = yList.length + nList.length;

        // 渲染已授权列表
        const authorizedContainer = document.getElementById('detailAuthorizedList');
        if (yList.length === 0) {
            authorizedContainer.innerHTML = '<p class="text-gray-400 text-sm text-center py-4">暂无已授权公司</p>';
        } else {
            authorizedContainer.innerHTML = yList.map(company => renderCompanyItem(company, true, deptName)).join('');
        }

        // 渲染未授权列表
        const unauthorizedContainer = document.getElementById('detailUnauthorizedList');
        if (nList.length === 0) {
            unauthorizedContainer.innerHTML = '<p class="text-gray-400 text-sm text-center py-4">暂无未授权公司</p>';
        } else {
            unauthorizedContainer.innerHTML = nList.map(company => renderCompanyItem(company, false, deptName)).join('');
        }

        // 显示弹窗
        document.getElementById('deptDetailModal').classList.remove('hidden');
    }

    /**
     * 关闭部门详情弹窗
     */
    function closeDeptDetail() {
        document.getElementById('deptDetailModal').classList.add('hidden');
        currentDeptName = null;
        // 刷新主界面
        renderDepartmentGrid();
        updateStatistics();
    }

    /**
     * 渲染公司项
     */
    function renderCompanyItem(company, isAuthorized, deptName) {
        const hasCompany = company.CNAMEEN && company.CNAMEEN.trim() !== '';
        const hasGroup = company.GROUPID && company.GROUPID.trim() !== '';

        return `
            <div class="flex items-center gap-3 p-3 bg-gradient-to-r ${
                isAuthorized ? 'from-green-50 to-white border-green-200' : 'from-gray-50 to-white border-gray-200'
            } border rounded-lg hover:shadow-md transition-all">
                <div class="w-10 h-10 ${isAuthorized ? 'bg-green-500' : 'bg-gray-400'} rounded-lg flex items-center justify-center flex-shrink-0">
                    <i class="fas fa-building text-white"></i>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="font-semibold text-gray-900 text-sm truncate">${company.RDEPT}</div>
                    <div class="flex items-center gap-2 mt-1">
                        ${hasCompany ? `
                            <span class="text-xs text-gray-600 flex items-center gap-1">
                                <i class="fas fa-building text-blue-500"></i>${company.CNAMEEN}
                            </span>
                        ` : '<span class="text-xs text-yellow-600"><i class="fas fa-exclamation-triangle"></i> 未设置</span>'}
                        ${hasGroup ? `
                            <span class="text-xs text-gray-500 flex items-center gap-1">
                                <i class="fas fa-layer-group text-purple-500"></i>${company.GROUPID}
                            </span>
                        ` : ''}
                    </div>
                </div>
                <button onclick="EmployeePermissionModal.toggleCompany('${deptName}', '${company.RDEPT}', ${isAuthorized})"
                        class="px-3 py-1.5 text-xs ${
                            isAuthorized 
                                ? 'bg-red-50 border border-red-300 text-red-700 hover:bg-red-100' 
                                : 'bg-green-50 border border-green-300 text-green-700 hover:bg-green-100'
                        } rounded transition font-medium">
                    <i class="fas ${isAuthorized ? 'fa-times' : 'fa-check'} mr-1"></i>
                    ${isAuthorized ? '取消' : '授权'}
                </button>
            </div>
        `;
    }

    /**
     * 切换单个公司的授权状态
     */
    function toggleCompany(deptName, rdept, isAuthorized) {
        const dept = permissionData[deptName];
        const sourceKey = isAuthorized ? 'Y' : 'N';
        const targetKey = isAuthorized ? 'N' : 'Y';

        const sourceIndex = dept[sourceKey].findIndex(c => c.RDEPT === rdept);
        if (sourceIndex !== -1) {
            const company = dept[sourceKey].splice(sourceIndex, 1)[0];
            if (!dept[targetKey]) dept[targetKey] = [];
            dept[targetKey].push(company);
        }

        // 重新打开详情以刷新
        openDeptDetail(deptName);
    }

    /**
     * 批量授权部门内所有公司
     */
    function addAllFromDept() {
        if (!currentDeptName) return;
        const dept = permissionData[currentDeptName];
        
        if (dept.N && dept.N.length > 0) {
            if (!dept.Y) dept.Y = [];
            dept.Y = dept.Y.concat(dept.N);
            dept.N = [];
        }

        openDeptDetail(currentDeptName);
    }

    /**
     * 批量取消部门内所有授权
     */
    function removeAllFromDept() {
        if (!currentDeptName) return;
        const dept = permissionData[currentDeptName];
        
        if (dept.Y && dept.Y.length > 0) {
            if (!dept.N) dept.N = [];
            dept.N = dept.N.concat(dept.Y);
            dept.Y = [];
        }

        openDeptDetail(currentDeptName);
    }

    /**
     * 快速授权（从卡片）
     */
    function addAllFromDeptQuick(deptName) {
        const dept = permissionData[deptName];
        if (dept.N && dept.N.length > 0) {
            if (!dept.Y) dept.Y = [];
            dept.Y = dept.Y.concat(dept.N);
            dept.N = [];
        }
        renderDepartmentGrid();
        updateStatistics();
    }

    /**
     * 快速取消授权（从卡片）
     */
    function removeAllFromDeptQuick(deptName) {
        const dept = permissionData[deptName];
        if (dept.Y && dept.Y.length > 0) {
            if (!dept.N) dept.N = [];
            dept.N = dept.N.concat(dept.Y);
            dept.Y = [];
        }
        renderDepartmentGrid();
        updateStatistics();
    }

    /**
     * 授权所有可见部门
     */
    function authorizeAllVisible() {
        if (!confirm(`确定要授权所有 ${filteredDepts.length} 个部门的所有公司吗？`)) return;

        filteredDepts.forEach(deptName => {
            const dept = permissionData[deptName];
            if (dept.N && dept.N.length > 0) {
                if (!dept.Y) dept.Y = [];
                dept.Y = dept.Y.concat(dept.N);
                dept.N = [];
            }
        });

        renderDepartmentGrid();
        updateStatistics();
    }

    /**
     * 清空所有授权
     */
    function clearAllAuthorized() {
        if (!confirm('确定要清空所有授权吗？')) return;

        Object.keys(permissionData).forEach(deptName => {
            const dept = permissionData[deptName];
            if (dept.Y && dept.Y.length > 0) {
                if (!dept.N) dept.N = [];
                dept.N = dept.N.concat(dept.Y);
                dept.Y = [];
            }
        });

        renderDepartmentGrid();
        updateStatistics();
    }

    /**
     * 设置视图模式
     */
    function setViewMode(mode) {
        viewMode = mode;
        
        const gridBtn = document.getElementById('viewGridBtn');
        const listBtn = document.getElementById('viewListBtn');
        
        if (mode === 'grid') {
            gridBtn.className = 'px-2.5 py-1.5 text-xs bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-all';
            listBtn.className = 'px-2.5 py-1.5 text-xs border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-all';
            document.getElementById('departmentGrid').className = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3';
        } else {
            gridBtn.className = 'px-2.5 py-1.5 text-xs border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-all';
            listBtn.className = 'px-2.5 py-1.5 text-xs bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-all';
            document.getElementById('departmentGrid').className = 'grid grid-cols-1 gap-3';
        }
    }

    /**
     * 更新统计信息
     */
    function updateStatistics() {
        let totalAuthorized = 0;
        let totalUnauthorized = 0;
        const companies = new Set();
        const groups = new Set();

        Object.keys(permissionData).forEach(deptName => {
            const dept = permissionData[deptName];
            
            if (dept.Y) {
                totalAuthorized += dept.Y.length;
                dept.Y.forEach(c => {
                    if (c.CNAMEEN) companies.add(c.CNAMEEN);
                    if (c.GROUPID) groups.add(c.GROUPID);
                });
            }
            
            if (dept.N) {
                totalUnauthorized += dept.N.length;
                dept.N.forEach(c => {
                    if (c.CNAMEEN) companies.add(c.CNAMEEN);
                    if (c.GROUPID) groups.add(c.GROUPID);
                });
            }
        });

        document.getElementById('totalDeptCount').textContent = Object.keys(permissionData).length;
        document.getElementById('totalAuthorizedCount').textContent = totalAuthorized;
        document.getElementById('totalUnauthorizedCount').textContent = totalUnauthorized;
        document.getElementById('companyCount').textContent = companies.size;
        document.getElementById('groupCount').textContent = groups.size;
    }

    /**
     * 保存员工权限
     */
    function save() {
        const authorizedList = [];
        
        Object.keys(permissionData).forEach(deptName => {
            const dept = permissionData[deptName];
            if (dept.Y) {
                dept.Y.forEach(company => {
                    authorizedList.push({
                        deptType: deptName,
                        ...company
                    });
                });
            }
        });

        console.log('保存员工权限:', {
            employee: currentEmployee,
            authorized: authorizedList,
            permissionData: permissionData
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

    // 公开的API
    return {
        init,
        open,
        close,
        save,
        openDeptDetail,
        closeDeptDetail,
        toggleCompany,
        addAllFromDept,
        removeAllFromDept,
        addAllFromDeptQuick,
        removeAllFromDeptQuick,
        authorizeAllVisible,
        clearAllAuthorized,
        setViewMode,
        getCurrentEmployee: () => currentEmployee,
        getAuthorizedDepartments: () => {
            const list = [];
            Object.keys(permissionData).forEach(deptName => {
                const dept = permissionData[deptName];
                if (dept.Y) {
                    dept.Y.forEach(company => {
                        list.push({ deptType: deptName, ...company });
                    });
                }
            });
            return list;
        }
    };
})();

// 页面加载时初始化模块
document.addEventListener('DOMContentLoaded', function() {
    EmployeePermissionModal.init('授权公司.JSON');
});
