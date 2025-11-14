/**
 * 员工权限编辑弹框模块
 * 独立处理员工权限配置的所有逻辑
 */
const EmployeePermissionModal = (function() {
    // 私有变量
    let currentEmployee = null;
    let departmentData = { data: [] };
    let filteredData = [];
    let isInitialized = false;

    /**
     * 初始化模块
     * @param {Object} deptData - 部门数据对象
     */
    function init(deptData) {
        if (isInitialized) return;
        
        departmentData = deptData;
        filteredData = [...departmentData.data];
        
        // 绑定事件监听器
        bindEventListeners();
        
        isInitialized = true;
        console.log('✓ 员工权限编辑模块已初始化');
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
        const companyFilter = document.getElementById('sidebarCompanyFilter');
        const searchInput = document.getElementById('sidebarSearchInput');

        if (groupFilter) groupFilter.addEventListener('change', applyFilters);
        if (companyFilter) companyFilter.addEventListener('change', applyFilters);
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
        renderContent();
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
     * 初始化筛选器
     */
    function initializeFilters() {
        // 填充公司选项
        const companies = [...new Set(departmentData.data.map(d => d.CNAMEEN))].sort();
        const companySelect = document.getElementById('sidebarCompanyFilter');
        companySelect.innerHTML = '<option value="">全部公司</option>';
        
        companies.forEach(company => {
            const option = document.createElement('option');
            option.value = company;
            option.textContent = company;
            companySelect.appendChild(option);
        });
        
        // 初始化过滤数据
        filteredData = [...departmentData.data];
    }

    /**
     * 应用筛选条件
     */
    function applyFilters() {
        const groupFilter = document.getElementById('sidebarGroupFilter').value;
        const companyFilter = document.getElementById('sidebarCompanyFilter').value;
        const searchTerm = document.getElementById('sidebarSearchInput').value.toLowerCase();
        
        filteredData = departmentData.data.filter(dept => {
            if (groupFilter && dept.GROUPID !== groupFilter) return false;
            if (companyFilter && dept.CNAMEEN !== companyFilter) return false;
            if (searchTerm && !dept.RDEPT.toLowerCase().includes(searchTerm)) return false;
            return true;
        });
        
        renderContent();
        updateStatistics();
    }

    /**
     * 渲染侧边栏内容
     */
    function renderContent() {
        const container = document.getElementById('sidebarContent');
        
        // 按公司分组
        const groupedByCompany = {};
        filteredData.forEach(dept => {
            const company = dept.CNAMEEN;
            if (!groupedByCompany[company]) {
                groupedByCompany[company] = {
                    company: company,
                    fullName: dept.CDESC3,
                    groupId: dept.GROUPID,
                    departments: []
                };
            }
            groupedByCompany[company].departments.push(dept);
        });
        
        // 生成HTML
        container.innerHTML = Object.values(groupedByCompany).map(companyData => {
            const selectedCount = companyData.departments.filter(d => d.FLAG === 'Y').length;
            const totalCount = companyData.departments.length;
            
            return `
                <div class="company-card bg-white rounded-lg border border-gray-200 mb-4 overflow-hidden">
                    <!-- 公司头部 -->
                    <div class="bg-gray-50 p-4 border-b border-gray-200">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                                    <i class="fas fa-building text-orange-600"></i>
                                </div>
                                <div>
                                    <h4 class="font-bold text-gray-900">${companyData.company}</h4>
                                    <p class="text-xs text-gray-500">${companyData.fullName}</p>
                                </div>
                            </div>
                            <div class="flex items-center gap-2">
                                <button onclick="EmployeePermissionModal.toggleCompanyDepts('${companyData.company}', true)" 
                                        class="px-2 py-1 text-xs border border-green-300 text-green-700 rounded hover:bg-green-50 transition">
                                    全选
                                </button>
                                <button onclick="EmployeePermissionModal.toggleCompanyDepts('${companyData.company}', false)" 
                                        class="px-2 py-1 text-xs border border-red-300 text-red-700 rounded hover:bg-red-50 transition">
                                    全不选
                                </button>
                                <span class="ml-2 text-sm font-semibold text-gray-700">${selectedCount}/${totalCount}</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 部门列表 -->
                    <div class="p-3 space-y-1">
                        ${companyData.departments.map(dept => `
                            <label class="dept-checkbox flex items-center gap-3 p-2 rounded cursor-pointer hover:bg-orange-50 transition">
                                <input 
                                    type="checkbox" 
                                    ${dept.FLAG === 'Y' ? 'checked' : ''} 
                                    onchange="EmployeePermissionModal.toggleDepartment('${dept.RDEPT}', '${companyData.company}')"
                                    class="w-4 h-4 text-orange-600 rounded focus:ring-orange-500 cursor-pointer"
                                />
                                <span class="flex-1 text-sm ${dept.FLAG === 'Y' ? 'text-gray-900 font-medium' : 'text-gray-600'}">
                                    ${dept.RDEPT}
                                </span>
                                ${dept.FLAG === 'Y' ? '<i class="fas fa-check-circle text-orange-500 text-xs"></i>' : ''}
                            </label>
                        `).join('')}
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * 切换部门选择状态
     * @param {string} deptName - 部门名称
     * @param {string} company - 公司名称
     */
    function toggleDepartment(deptName, company) {
        const dept = departmentData.data.find(d => d.RDEPT === deptName && d.CNAMEEN === company);
        if (dept) {
            dept.FLAG = dept.FLAG === 'Y' ? 'N' : 'Y';
            renderContent();
            updateStatistics();
        }
    }

    /**
     * 切换公司所有部门
     * @param {string} company - 公司名称
     * @param {boolean} selectAll - true为全选，false为全不选
     */
    function toggleCompanyDepts(company, selectAll) {
        departmentData.data.forEach(dept => {
            if (dept.CNAMEEN === company && filteredData.includes(dept)) {
                dept.FLAG = selectAll ? 'Y' : 'N';
            }
        });
        renderContent();
        updateStatistics();
    }

    /**
     * 全选可见部门
     */
    function selectAllVisible() {
        filteredData.forEach(dept => {
            dept.FLAG = 'Y';
        });
        renderContent();
        updateStatistics();
    }

    /**
     * 取消全选
     */
    function deselectAllVisible() {
        filteredData.forEach(dept => {
            dept.FLAG = 'N';
        });
        renderContent();
        updateStatistics();
    }

    /**
     * 更新统计信息
     */
    function updateStatistics() {
        const authorizedDepts = departmentData.data.filter(d => d.FLAG === 'Y');
        const companies = [...new Set(authorizedDepts.map(d => d.CNAMEEN))];
        
        document.getElementById('authorizedCount').textContent = authorizedDepts.length;
        document.getElementById('totalDeptCount').textContent = departmentData.data.length;
        document.getElementById('companyCount').textContent = companies.length;
    }

    /**
     * 保存员工权限
     */
    function save() {
        const authorizedDepts = departmentData.data.filter(d => d.FLAG === 'Y');
        
        console.log('保存员工权限:', {
            employee: currentEmployee,
            departments: authorizedDepts
        });
        
        // 触发自定义事件，让主应用可以监听
        const event = new CustomEvent('employeePermissionSaved', {
            detail: {
                employee: currentEmployee,
                departments: authorizedDepts
            }
        });
        document.dispatchEvent(event);
        
        alert(`已为 ${currentEmployee.name} 配置 ${authorizedDepts.length} 个部门的审批权限`);
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
        return departmentData.data.filter(d => d.FLAG === 'Y');
    }

    // 公开的API
    return {
        init,
        open,
        close,
        save,
        toggleDepartment,
        toggleCompanyDepts,
        selectAllVisible,
        deselectAllVisible,
        getCurrentEmployee,
        getAuthorizedDepartments
    };
})();
