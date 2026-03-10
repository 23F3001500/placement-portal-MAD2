const { createApp, nextTick } = Vue;
const { createRouter, createWebHashHistory } = VueRouter;

axios.interceptors.request.use(config => {
    const token = localStorage.getItem('token');
    if (token && token.length > 10) config.headers.Authorization = `Bearer ${token}`;
    if (config.method === 'get') config.url += (config.url.includes('?') ? '&' : '?') + 't=' + new Date().getTime();
    return config;
});

axios.interceptors.response.use(response => response, error => {
    if (error.response && (error.response.status === 401 || error.response.status === 422)) {
        alert("Session invalid or expired. You have been safely logged out.");
        localStorage.clear(); window.location.href = '/'; 
    } else if (error.response && error.response.status === 403) {
        alert(error.response.data.message || "Access denied.");
        if(error.response.data.message.includes('blacklisted')) { localStorage.clear(); window.location.href = '/'; }
    }
    return Promise.reject(error);
});

const Login = {
    template: '#login-template',
    data() { return { username: '', password: '' } },
    methods: {
        async login() {
            try {
                const res = await axios.post('/api/login', { username: this.username, password: this.password });
                localStorage.setItem('token', res.data.token);
                localStorage.setItem('role', res.data.role);
                this.$root.userRole = res.data.role;
                this.$root.isAuthenticated = true;
                if (res.data.role === 'admin') { this.$root.fetchPendingCounts(); this.$router.push('/admin'); }
                else if (res.data.role === 'company') this.$router.push('/company');
                else this.$router.push('/student');
            } catch (e) { alert(e.response?.data?.message || 'Invalid Credentials'); }
        }
    }
};

const Register = {
    template: '#register-template',
    data() { return { role: 'student', username: '', password: '', email: '', fullname: '', cgpa: '', branch: '', graduation_year: '', company_name: '', hr_contact: '', website: '' } },
    methods: {
        async register() {
            try {
                await axios.post('/api/register', this.$data);
                alert('Registration Successful! Please log in.');
                this.$router.push('/login');
            } catch (e) { alert(e.response?.data?.message || 'Server error while registering.'); }
        }
    }
};

const AdminDash = {
    template: '#admin-dash-template',
    data() { return { stats: { students: 0, companies: 0, drives: 0 }, chartInstance: null } },
    async mounted() {
        try {
            const res = await axios.get('/api/admin/stats');
            this.stats = res.data;
            this.renderChart();
        } catch(e) {}
    },
    methods: {
        renderChart() {
            nextTick(() => {
                const ctx = document.getElementById('adminChart');
                if (ctx) {
                    if (this.chartInstance) this.chartInstance.destroy();
                    this.chartInstance = new Chart(ctx, {
                        type: 'doughnut',
                        data: {
                            labels: ['Students', 'Companies', 'Drives'],
                            datasets: [{
                                data: [this.stats.students, this.stats.companies, this.stats.drives],
                                backgroundColor: ['#0284c7', '#6366f1', '#059669'],
                                borderWidth: 0,
                                hoverOffset: 10
                            }]
                        },
                        options: { responsive: true, maintainAspectRatio: false, cutout: '70%', plugins: { legend: { position: 'right', labels: { font: { family: 'Nunito', size: 13 } } } } }
                    });
                }
            });
        }
    }
};

const AdminApprovals = {
    template: '#admin-approvals-template',
    data() { return { companies: [], pendingDrives: [] } },
    computed: { pendingCompanies() { return this.companies.filter(c => c.approval_status === 'Pending'); } },
    async mounted() { this.loadApprovals(); },
    methods: {
        async loadApprovals() {
            try {
                const c = await axios.get('/api/admin/companies');
                this.companies = c.data; this.$root.pendingCompanyCount = this.pendingCompanies.length;
                const d = await axios.get('/api/admin/pending_drives');
                this.pendingDrives = d.data;
            } catch(e) {}
        },
        async actionCompany(company_id, action) { await axios.post(`/api/admin/${action}_company/${company_id}`); this.loadApprovals(); },
        async actionDrive(drive_id, action) { await axios.post(`/api/admin/drive/${drive_id}/${action}`); this.loadApprovals(); }
    }
};

const AdminUsers = {
    template: '#admin-users-template',
    data() { return { users: [], searchQuery: '', selectedUser: null } },
    computed: {
        filteredUsers() {
            const q = this.searchQuery.toLowerCase();
            return this.users.filter(u => u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q));
        }
    },
    async mounted() { this.loadUsers(); },
    methods: {
        async loadUsers() { const res = await axios.get('/api/admin/users'); this.users = res.data; },
        async toggleBlacklist(user_id) { await axios.post(`/api/admin/user/${user_id}/toggle_blacklist`); this.loadUsers(); },
        viewUser(user) { this.selectedUser = user; }
    }
};

const AdminDrives = {
    template: '#admin-drives-template',
    data() { return { drives: [], searchQuery: '', selectedDrive: null } },
    computed: {
        filteredDrives() {
            const q = this.searchQuery.toLowerCase();
            return this.drives.filter(d => d.job_title.toLowerCase().includes(q) || d.company.toLowerCase().includes(q));
        }
    },
    async mounted() { this.loadDrives(); },
    methods: {
        async loadDrives() {
            try {
                const res = await axios.get('/api/admin/all_drives');
                this.drives = res.data;
            } catch(e) {}
        },
        async closeDrive(drive_id) {
            try {
                await axios.post(`/api/admin/drive/${drive_id}/close`);
                this.loadDrives();
            } catch(e) { alert('Error closing drive'); }
        },
        viewDrive(drive) { this.selectedDrive = drive; }
    }
};

const AdminApplications = {
    template: '#admin-applications-template',
    data() { return { applications: [] } },
    async mounted() {
        try {
            const res = await axios.get('/api/admin/applications');
            this.applications = res.data;
        } catch(e) {}
    }
};

const StudentDash = {
    template: '#student-dash-template',
    data() { return { drives: [], searchQuery: '', selectedDriveDetails: null } },
    computed: {
        filteredDrives() {
            const q = this.searchQuery.toLowerCase();
            return this.drives.filter(d => d.job_title.toLowerCase().includes(q) || d.company.toLowerCase().includes(q));
        }
    },
    async mounted() { const res = await axios.get('/api/student/drives'); this.drives = res.data; },
    methods: {
        async apply(drive_id) {
            try { await axios.post(`/api/student/apply/${drive_id}`); alert('Applied successfully!'); } 
            catch (e) { alert(e.response?.data?.message || 'Error applying'); }
        },
        viewDriveDetails(drive) { this.selectedDriveDetails = drive; }
    }
};

const StudentApplications = {
    template: '#student-applications-template',
    data() { return { applications: [] } },
    async mounted() { const res = await axios.get('/api/student/applications'); this.applications = res.data; },
    methods: {
        async exportCSV() {
            try { const res = await axios.post('/api/student/export_applications'); alert(res.data.message); } 
            catch(e) { alert('Error triggering CSV export.'); }
        }
    }
};

const StudentProfile = {
    template: '#student-profile-template',
    data() { return { profile: { fullname: '', cgpa: 0, branch: '', graduation_year: '', resume_link: '' } } },
    async mounted() { const res = await axios.get('/api/student/profile'); this.profile = res.data; },
    methods: {
        async updateProfile() {
            try { await axios.put('/api/student/profile', this.profile); alert('Profile updated successfully!'); } 
            catch(e) { alert('Error updating profile.'); }
        }
    }
};

const CompanyDash = {
    template: '#company-dash-template',
    data() { return { drives: [], selectedDrive: null, applicants: [], selectedStudent: null, selectedOffer: null } },
    async mounted() { const res = await axios.get('/api/company/drives'); this.drives = res.data; },
    methods: {
        async viewApplicants(drive_id) { this.selectedDrive = drive_id; const res = await axios.get(`/api/company/drive/${drive_id}/applicants`); this.applicants = res.data; },
        async updateStatus(application_id, status) { await axios.post(`/api/company/application/${application_id}/status`, { status }); this.viewApplicants(this.selectedDrive); },
        viewStudent(student) { this.selectedStudent = student; },
        
        generateOffer(app, jobTitle, companyName) {
            this.selectedOffer = {
                application_id: app.application_id,
                student_name: app.student_name,
                job_title: jobTitle,
                company_name: companyName
            };
        },
        async sendOfferEmail(application_id) {
            try {
                const res = await axios.post(`/api/company/application/${application_id}/send_offer`);
                alert(res.data.message);
                this.selectedOffer = null;
            } catch(e) { alert('Error sending offer letter.'); }
        }
    }
};

const CompanyCreateDrive = {
    template: '#company-create-drive-template',
    data() { return { form: { job_title: '', job_description: '', eligibility_cgpa: '', eligibility_branch: '', eligibility_year: '', application_deadline: '' }, errorMsg: null, isPending: false } },
    methods: {
        async submitDrive() {
            try {
                this.errorMsg = null; this.isPending = false;
                await axios.post('/api/company/drives', this.form);
                alert('Drive created! Pending Admin approval.'); this.$router.push('/company');
            } catch (e) { 
                this.errorMsg = e.response?.data?.message || 'Error creating drive.';
                if (this.errorMsg.toLowerCase().includes('not approved')) { this.isPending = true; this.errorMsg = null; }
            }
        }
    }
};

const routes = [
    { path: '/', redirect: '/login' },
    { path: '/login', component: Login },
    { path: '/register', component: Register },
    { path: '/admin', component: AdminDash },
    { path: '/admin/approvals', component: AdminApprovals },
    { path: '/admin/users', component: AdminUsers },
    { path: '/admin/drives', component: AdminDrives },
    { path: '/admin/applications', component: AdminApplications },
    { path: '/student', component: StudentDash },
    { path: '/student/applications', component: StudentApplications },
    { path: '/student/profile', component: StudentProfile },
    { path: '/company', component: CompanyDash },
    { path: '/company/create', component: CompanyCreateDrive },
];

const router = createRouter({ history: createWebHashHistory(), routes });

const app = createApp({
    data() { return { isAuthenticated: !!localStorage.getItem('token'), userRole: localStorage.getItem('role'), pendingCompanyCount: 0 } },
    mounted() { if (this.isAuthenticated && this.userRole === 'admin') this.fetchPendingCounts(); },
    methods: {
        async fetchPendingCounts() {
            if (this.userRole === 'admin') {
                try { const res = await axios.get('/api/admin/companies'); this.pendingCompanyCount = res.data.filter(c => c.approval_status === 'Pending').length; } catch(e) {}
            }
        },
        logout() { localStorage.clear(); this.isAuthenticated = false; this.userRole = null; this.pendingCompanyCount = 0; this.$router.push('/login'); }
    }
});
app.config.compilerOptions.delimiters = ['[[', ']]'];
app.use(router);
app.mount('#app');