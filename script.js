let expenses = [];
let editingId = null;
let currentFilter = 'all';
let currentView = 'list';

const categoryColors = {
    Food: '#3b82f6',
    Transport: '#8b5cf6',
    Utilities: '#10b981',
    Entertainment: '#f59e0b',
    Healthcare: '#ef4444',
    Shopping: '#ec4899',
    Other: '#6366f1'
};

let categoryChart = null;
let dailyChart = null;

document.addEventListener('DOMContentLoaded', () => {
    loadExpenses();
    document.getElementById('date').valueAsDate = new Date();
    updateUI();
});

function loadExpenses() {
    const saved = localStorage.getItem('expenses');
    if (saved) expenses = JSON.parse(saved);
}

function saveExpenses() {
    localStorage.setItem('expenses', JSON.stringify(expenses));
}

function handleSubmit() {
    const amount = document.getElementById('amount').value;
    const category = document.getElementById('category').value;
    const date = document.getElementById('date').value;
    const description = document.getElementById('description').value;

    if (!amount || !description) { 
        alert('Please fill in all fields'); 
        return; 
    }

    if (editingId) {
        const index = expenses.findIndex(e => e.id === editingId);
        expenses[index] = { id: editingId, amount, category, date, description };
        editingId = null;
        document.getElementById('formTitle').textContent = 'Add New Expense';
        document.getElementById('cancelBtn').classList.add('hidden');
    } else {
        expenses.push({ id: Date.now(), amount, category, date, description });
    }

    saveExpenses();
    clearForm();
    updateUI();
}

function clearForm() {
    document.getElementById('amount').value = '';
    document.getElementById('category').value = 'Food';
    document.getElementById('date').valueAsDate = new Date();
    document.getElementById('description').value = '';
}

function editExpense(id) {
    const exp = expenses.find(e => e.id === id);
    if (exp) {
        document.getElementById('amount').value = exp.amount;
        document.getElementById('category').value = exp.category;
        document.getElementById('date').value = exp.date;
        document.getElementById('description').value = exp.description;
        editingId = id;
        document.getElementById('formTitle').textContent = 'Edit Expense';
        document.getElementById('cancelBtn').classList.remove('hidden');
    }
}

function cancelEdit() {
    editingId = null;
    clearForm();
    document.getElementById('formTitle').textContent = 'Add New Expense';
    document.getElementById('cancelBtn').classList.add('hidden');
}

function deleteExpense(id) {
    if (confirm('Are you sure you want to delete this expense?')) {
        expenses = expenses.filter(e => e.id !== id);
        saveExpenses();
        updateUI();
    }
}

function setFilter(filter, event) {
    currentFilter = filter;
    document.querySelectorAll('.filters .filter-group:first-child .filter-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    updateUI();
}

function setView(view, event) {
    currentView = view;
    document.querySelectorAll('.filters .filter-group:last-child .filter-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    if (view === 'list') {
        document.getElementById('listView').classList.remove('hidden');
        document.getElementById('chartsView').classList.add('hidden');
    } else {
        document.getElementById('listView').classList.add('hidden');
        document.getElementById('chartsView').classList.remove('hidden');
        updateCharts();
    }
}

function getFilteredExpenses() {
    const now = new Date();
    return expenses.filter(exp => {
        const expDate = new Date(exp.date);
        if (currentFilter === 'week') {
            const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
            return expDate >= weekAgo;
        } else if (currentFilter === 'month') {
            return expDate.getMonth() === now.getMonth() && expDate.getFullYear() === now.getFullYear();
        }
        return true;
    }).sort((a, b) => new Date(b.date) - new Date(a.date));
}

function updateUI() {
    updateSummary();
    updateTable();
    if (currentView === 'charts') updateCharts();
}

function updateSummary() {
    const filtered = getFilteredExpenses();
    const total = filtered.reduce((sum, exp) => sum + parseFloat(exp.amount), 0);
    const categories = new Set(filtered.map(e => e.category));
    document.getElementById('totalExpenses').textContent = '$' + total.toFixed(2);
    document.getElementById('totalRecords').textContent = filtered.length;
    document.getElementById('totalCategories').textContent = categories.size;
}

function updateTable() {
    const tbody = document.getElementById('expenseTableBody');
    const filtered = getFilteredExpenses();
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No expenses recorded yet. Add your first expense above!</td></tr>';
        return;
    }
    tbody.innerHTML = filtered.map(exp => `
        <tr>
            <td>${exp.date}</td>
            <td><span class="category-badge" style="background-color: ${categoryColors[exp.category]}">${exp.category}</span></td>
            <td>${exp.description}</td>
            <td>$${parseFloat(exp.amount).toFixed(2)}</td>
            <td>
                <button class="action-btn edit-btn" onclick="editExpense(${exp.id})">✏️</button>
                <button class="action-btn delete-btn" onclick="deleteExpense(${exp.id})">🗑️</button>
            </td>
        </tr>
    `).join('');
}

function updateCharts() {
    const filtered = getFilteredExpenses();

    // Expenses by Category
    const categoryMap = {};
    filtered.forEach(exp => {
        categoryMap[exp.category] = (categoryMap[exp.category] || 0) + parseFloat(exp.amount);
    });

    const catLabels = Object.keys(categoryMap);
    const catData = Object.values(categoryMap);
    const catColors = catLabels.map(label => categoryColors[label]);

    if (categoryChart) categoryChart.destroy();
    const ctxCat = document.getElementById('categoryChart').getContext('2d');
    categoryChart = new Chart(ctxCat, {
        type: 'pie',
        data: { labels: catLabels, datasets: [{ data: catData, backgroundColor: catColors }] },
        options: { plugins: { legend: { position: 'bottom' } } }
    });

    // Daily Expenses Last 10 Days
    const dailyMap = {};
    for (let i = 9; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        const key = d.toISOString().split('T')[0];
        dailyMap[key] = 0;
    }
    filtered.forEach(exp => {
        if (dailyMap[exp.date] !== undefined) dailyMap[exp.date] += parseFloat(exp.amount);
    });

    const dailyLabels = Object.keys(dailyMap);
    const dailyData = Object.values(dailyMap);

    if (dailyChart) dailyChart.destroy();
    const ctxDaily = document.getElementById('dailyChart').getContext('2d');
    dailyChart = new Chart(ctxDaily, {
        type: 'bar',
        data: {
            labels: dailyLabels,
            datasets: [{
                label: 'Daily Expense',
                data: dailyData,
                backgroundColor: '#2196f3'
            }]
        },
        options: { plugins: { legend: { display: false } }, responsive: true }
    });
}
