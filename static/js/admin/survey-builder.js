/**
 * Survey Builder - Admin JavaScript
 * Handles: Years, Question Titles, Questions, Form Builder, Excel Import
 */
import { api } from '/static/js/admin/api.js';
import { toast, confirmDelete, escape } from '/static/js/admin/ui.js';

// ============================================================
// STATE
// ============================================================
const state = {
  activeTab: 'years',
  years: [],
  questionTitles: [],
  uniQuestions: [],
  ministryQuestions: [],
  currentYearId: null,
  currentOrgType: 'university',
  availableQuestions: [],
  formQuestions: [], // questions on canvas
  selectedQuestionId: null,
  importData: null,
  importStep: 1,
};

// ============================================================
// DOM ELEMENTS
// ============================================================
const tabs = document.querySelectorAll('.builder-tab');
const panels = document.querySelectorAll('.tab-panel');

// Years
const yearsTable = document.getElementById('years-table');
const yearsPagination = document.getElementById('years-pagination');
const yearsSearch = document.getElementById('years-search');
const yearsStatusFilter = document.getElementById('years-status-filter');

// Question Titles
const titlesTable = document.getElementById('titles-table');
const titlesPagination = document.getElementById('titles-pagination');
const titlesSearch = document.getElementById('titles-search');

// University Questions
const uniQTable = document.getElementById('uni-q-table');
const uniQPagination = document.getElementById('uni-q-pagination');
const uniQSearch = document.getElementById('uni-q-search');
const uniQYearFilter = document.getElementById('uni-q-year-filter');
const uniQTitleFilter = document.getElementById('uni-q-title-filter');

// Ministry Questions
const minQTable = document.getElementById('min-q-table');
const minQPagination = document.getElementById('min-q-pagination');
const minQSearch = document.getElementById('min-q-search');
const minQYearFilter = document.getElementById('min-q-year-filter');
const minQTitleFilter = document.getElementById('min-q-title-filter');

// Builder
const builderOrgType = document.getElementById('builder-org-type');
const builderYear = document.getElementById('builder-year');
const loadBuilderBtn = document.getElementById('load-builder');
const builderContent = document.getElementById('builder-content');
const availableQuestions = document.getElementById('available-questions');
const availableQSearch = document.getElementById('available-q-search');
const availableTitleFilter = document.getElementById('available-title-filter');
const formCanvas = document.getElementById('form-canvas');
const questionSequence = document.getElementById('question-sequence');
const dropHint = document.getElementById('drop-hint');
const canvasTitle = document.getElementById('canvas-title');
const formProperties = document.getElementById('form-properties');
const previewFormBtn = document.getElementById('preview-form');
const saveFormBtn = document.getElementById('save-form');

// Import
const importExcelBtn = document.getElementById('import-excel-btn');
const excelImportDialog = document.getElementById('excel-import-dialog');
const excelDropZone = document.getElementById('excel-drop-zone');
const excelFileInput = document.getElementById('excel-file-input');
const excelFileBtn = document.getElementById('excel-file-btn');

// Dialogs
const yearFormDialog = document.getElementById('year-form-dialog');
const yearForm = document.getElementById('year-form');
const titleFormDialog = document.getElementById('title-form-dialog');
const titleForm = document.getElementById('title-form');
const questionFormDialog = document.getElementById('question-form-dialog');
const questionForm = document.getElementById('question-form');

// ============================================================
// INITIALIZATION
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initDialogs();
  initDragDrop();
  initExcelImport();
  initEventListeners();
  loadAllData();
});

function initTabs() {
  tabs.forEach(tab => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });
}

function switchTab(tabName) {
  state.activeTab = tabName;
  
  tabs.forEach(t => t.classList.toggle('is-active', t.dataset.tab === tabName));
  panels.forEach(p => p.classList.toggle('is-active', p.dataset.tabPanel === tabName));
  
  // Load data for tab if not loaded
  if (tabName === 'years' && state.years.length === 0) loadYears();
  if (tabName === 'question-titles' && state.questionTitles.length === 0) loadQuestionTitles();
  if (tabName === 'university-questions' && state.uniQuestions.length === 0) loadUniQuestions();
  if (tabName === 'ministry-questions' && state.ministryQuestions.length === 0) loadMinistryQuestions();
  if (tabName === 'builder') initBuilder();
}

// ============================================================
// DATA LOADING
// ============================================================
async function loadAllData() {
  await Promise.all([
    loadYears(),
    loadQuestionTitles(),

  ]);
}

async function loadYears(page = 1) {
  try {
    const params = new URLSearchParams({ page, limit: 25 });
    const search = yearsSearch?.value?.trim();
    if (search) params.append('search', search);
    const status = yearsStatusFilter?.value;
    if (status !== '') params.append('status', status);
    
    const data = await api(`/survey/years?${params}`);
    state.years = data;
    renderYearsTable(data);
    renderPagination(yearsPagination, page, data.length, loadYears);
    updateYearFilters();
    updateBuilderYearSelect();
  } catch (e) {
    console.error('Failed to load years:', e);
    toast('Failed to load years');
  }
}

async function loadQuestionTitles(page = 1) {
  try {
    const params = new URLSearchParams({ page, limit: 25 });
    const search = titlesSearch?.value?.trim();
    if (search) params.append('search', search);
    
    const data = await api(`/survey/question-titles?${params}`);
    state.questionTitles = data;
    renderTitlesTable(data);
    renderPagination(titlesPagination, page, data.length, loadQuestionTitles);
    updateTitleFilters();
  } catch (e) {
    console.error('Failed to load question titles:', e);
    toast('Failed to load question titles');
  }
}

async function loadUniQuestions(page = 1) {
  try {
    const params = new URLSearchParams({ page, limit: 25 });
    const search = uniQSearch?.value?.trim();
    if (search) params.append('search', search);
    const yearId = uniQYearFilter?.value;
    if (yearId) params.append('year_id', yearId);
    const titleId = uniQTitleFilter?.value;
    if (titleId) params.append('title_id', titleId);
    
    const data = await api(`/survey/questions/university?${params}`);
    state.uniQuestions = data;
    renderUniQuestionsTable(data);
    renderPagination(uniQPagination, page, data.length, loadUniQuestions);
  } catch (e) {
    console.error('Failed to load university questions:', e);
    toast('Failed to load university questions');
  }
}

async function loadMinistryQuestions(page = 1) {
  try {
    const params = new URLSearchParams({ page, limit: 25 });
    const search = minQSearch?.value?.trim();
    if (search) params.append('search', search);
    const yearId = minQYearFilter?.value;
    if (yearId) params.append('year_id', yearId);
    const titleId = minQTitleFilter?.value;
    if (titleId) params.append('title_id', titleId);
    
    const data = await api(`/survey/questions/ministry?${params}`);
    state.ministryQuestions = data;
    renderMinistryQuestionsTable(data);
    renderPagination(minQPagination, page, data.length, loadMinistryQuestions);
  } catch (e) {
    console.error('Failed to load ministry questions:', e);
    toast('Failed to load ministry questions');
  }
}

async function loadActiveYearsForBuilder() {
  try {
    const data = await api('/survey/years?limit=100');
    state.years = data;
    updateYearFilters();
    updateBuilderYearSelect();
  } catch (e) {
    console.error('Failed to load active years:', e);
  }
}

// ============================================================
// RENDER TABLES
// ============================================================
function renderPagination(container, page, count, loadPage) {
  if (!container) return;
  container.innerHTML = `<button type="button" class="btn" data-prev ${page === 1 ? 'disabled' : ''}>ယခင်</button><span>စာမျက်နှာ ${page}</span><button type="button" class="btn" data-next ${count < 25 ? 'disabled' : ''}>နောက်သို့</button>`;
  container.querySelector('[data-prev]').onclick = () => loadPage(page - 1);
  container.querySelector('[data-next]').onclick = () => loadPage(page + 1);
}

function renderYearsTable(years) {
  const tbody = yearsTable?.querySelector('tbody');
  if (!tbody) return;
  
  tbody.innerHTML = years.map(y => `
    <tr>
      <td>${y.yID}</td>
      <td><strong>${escape(y.label)}</strong><br><small>${y.year_from}/${y.year_to}</small></td>
      <td><span class="badge ${y.status === 1 ? 'published' : 'draft'}">${y.status === 1 ? 'Published' : 'Draft'}</span></td>
      <td class="numeric">${y.uni_question_count ?? "—"}</td>
      <td class="numeric">${y.min_question_count ?? "—"}</td>
      <td>
        <div class="actions">
          <button class="icon-button" data-edit-year="${y.yID}" title="Edit"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>
          <button class="icon-button danger" data-delete-year="${y.yID}" title="Delete"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></button>
        </div>
      </td>
    </tr>
  `).join('') || '<tr><td colspan="6" class="builder-empty">ကိုက်ညီသော မှတ်တမ်း မရှိပါ။ အသစ်ထည့်ပါ သို့မဟုတ် ရှာဖွေမှုကို ပြောင်းလဲပါ။</td></tr>';
}

function renderTitlesTable(titles) {
  const tbody = titlesTable?.querySelector('tbody');
  if (!tbody) return;
  
  tbody.innerHTML = titles.map(t => `
    <tr>
      <td>${t.qTID}</td>
      <td class="title">${escape(t.qTDetail)}</td>
      <td>${escape(t.description || '')}</td>
      <td class="numeric">${t.uni_count ?? "—"}</td>
      <td class="numeric">${t.min_count ?? "—"}</td>
      <td>
        <div class="actions">
          <button class="icon-button" data-edit-title="${t.qTID}" title="Edit"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>
          <button class="icon-button danger" data-delete-title="${t.qTID}" title="Delete"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></button>
        </div>
      </td>
    </tr>
  `).join('') || '<tr><td colspan="6" class="builder-empty">ကိုက်ညီသော မှတ်တမ်း မရှိပါ။ အသစ်ထည့်ပါ သို့မဟုတ် ရှာဖွေမှုကို ပြောင်းလဲပါ။</td></tr>';
}

function renderUniQuestionsTable(questions) {
  const tbody = uniQTable?.querySelector('tbody');
  if (!tbody) return;
  
  tbody.innerHTML = questions.map(q => `
    <tr>
      <td>${q.uQId}</td>
      <td class="title">${escape(q.uQDetail)}</td>
      <td>${escape(q.qTDetail || '—')}</td>
      <td>${q.year_label || q.yID}</td>
      <td class="numeric">${q.survey_count ?? "—"}</td>
      <td>
        <div class="actions">
          <button class="icon-button" data-edit-uni-q="${q.uQId}" title="Edit"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>
          <button class="icon-button danger" data-delete-uni-q="${q.uQId}" title="Delete"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></button>
        </div>
      </td>
    </tr>
  `).join('') || '<tr><td colspan="6" class="builder-empty">ကိုက်ညီသော မှတ်တမ်း မရှိပါ။ အသစ်ထည့်ပါ သို့မဟုတ် ရှာဖွေမှုကို ပြောင်းလဲပါ။</td></tr>';
}

function renderMinistryQuestionsTable(questions) {
  const tbody = minQTable?.querySelector('tbody');
  if (!tbody) return;
  
  tbody.innerHTML = questions.map(q => `
    <tr>
      <td>${q.mQId}</td>
      <td class="title">${escape(q.mQDetail)}</td>
      <td>${escape(q.qTDetail || '—')}</td>
      <td>${q.year_label || q.yID}</td>
      <td class="numeric">${q.survey_count ?? "—"}</td>
      <td>
        <div class="actions">
          <button class="icon-button" data-edit-min-q="${q.mQId}" title="Edit"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>
          <button class="icon-button danger" data-delete-min-q="${q.mQId}" title="Delete"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></button>
        </div>
      </td>
    </tr>
  `).join('') || '<tr><td colspan="6" class="builder-empty">ကိုက်ညီသော မှတ်တမ်း မရှိပါ။ အသစ်ထည့်ပါ သို့မဟုတ် ရှာဖွေမှုကို ပြောင်းလဲပါ။</td></tr>';
}

// ============================================================
// FILTER UPDATES
// ============================================================
function updateYearFilters() {
  const yearOptions = state.years.map(y => `<option value="${y.yID}">${escape(y.label)}</option>`).join('');
  [uniQYearFilter, minQYearFilter].forEach(sel => {
    if (sel) sel.innerHTML = `<option value="">All Years</option>${yearOptions}`;
  });
  updateBuilderYearSelect();
}

function updateTitleFilters() {
  const titleOptions = state.questionTitles.map(t => `<option value="${t.qTID}">${escape(t.qTDetail)}</option>`).join('');
  [uniQTitleFilter, minQTitleFilter, availableTitleFilter].forEach(sel => {
    if (sel) sel.innerHTML = `<option value="">All Titles</option>${titleOptions}`;
  });
}

function updateBuilderYearSelect() {
  if (!builderYear) return;
  const orgType = builderOrgType?.value || 'university';
  const options = state.years.map(y => `<option value="${y.yID}">${escape(y.label)}</option>`).join('');
  builderYear.innerHTML = `<option value="">Select Year</option>${options}`;
  builderYear.disabled = false;
  loadBuilderBtn.disabled = false;
}

// ============================================================
// BUILDER INITIALIZATION
// ============================================================
function initBuilder() {
  builderOrgType.value = state.currentOrgType;
  builderYear.value = state.currentYearId || '';
  builderContent.hidden = true;
  questionSequence.innerHTML = '';
  formProperties.innerHTML = '<p class="empty-state">Select Year + Org Type and click "Open Builder"</p>';
}

async function loadBuilder() {
  const orgType = builderOrgType.value;
  const yearId = parseInt(builderYear.value);
  
  if (!yearId) {
    toast('Please select a year');
    return;
  }
  
  state.currentOrgType = orgType;
  state.currentYearId = yearId;
  
  try {
    const data = await api(`/survey/builder/${orgType}/${yearId}`);
    
    state.availableQuestions = (data.available_questions || []).map(q => ({
      question_id: q.uQId ?? q.mQId,
      question_type: orgType === 'university' ? 'uniquestion' : 'ministryquestion',
      question_detail: q.uQDetail ?? q.mQDetail,
      question_title: q.qTDetail,
      question_title_id: q.qTID,
    }));
    state.formQuestions = data.questions || [];
    state.questionTitles = data.available_titles || [];
    
    builderContent.hidden = false;
    canvasTitle.textContent = data.form.title;
    renderAvailableQuestions();
    renderFormCanvas();
    updateTitleFilters();
    toast('Builder loaded');
  } catch (e) {
    console.error('Failed to load builder:', e);
    toast('Failed to load builder');
  }
}

function renderAvailableQuestions() {
  if (!availableQuestions) return;
  
  const search = availableQSearch?.value?.toLowerCase() || '';
  const titleFilter = availableTitleFilter?.value;
  
  let questions = state.availableQuestions;
  
  if (search) {
    questions = questions.filter(q => 
      (q.question_detail || '').toLowerCase().includes(search) ||
      (q.question_title || '').toLowerCase().includes(search)
    );
  }
  
  if (titleFilter) {
    questions = questions.filter(q => q.question_title_id == titleFilter);
  }
  
  // Group by title
  const grouped = {};
  questions.forEach(q => {
    const titleKey = q.question_title || 'ungrouped';
    if (!grouped[titleKey]) grouped[titleKey] = [];
    grouped[titleKey].push(q);
  });
  
  availableQuestions.innerHTML = Object.entries(grouped).map(([title, qs]) => `
    <div class="question-group">
      <h4 class="group-title">${escape(title)}</h4>
      ${qs.map(q => `
        <div class="question-item" role="button" tabindex="0" draggable="true" data-qid="${q.question_id}" data-qtype="${q.question_type}">
          <div class="question-item-header">
            <span class="question-item-drag" aria-label="Drag"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 9h16M4 15h16"/></svg></span>
            <div class="question-item-content">
              <div class="question-item-detail">${escape(q.question_detail)}</div>
              <div class="question-item-meta">
                <span class="question-item-badge">${q.question_type === 'uniquestion' ? 'Uni' : 'Min'}</span>
                ${q.question_title ? `<span class="question-item-badge">${escape(q.question_title)}</span>` : ''}
              </div>
            </div>
          </div>
        </div>
      `).join('')}
    </div>
  `).join('');
  
  // Add drag listeners
  availableQuestions.querySelectorAll('.question-item[draggable="true"]').forEach(item => {
    item.addEventListener('click', () => addQuestionToCanvas(item.dataset.qid, item.dataset.qtype));
    item.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        addQuestionToCanvas(item.dataset.qid, item.dataset.qtype);
      }
    });
    item.addEventListener('dragstart', handleDragStart);
    item.addEventListener('dragend', handleDragEnd);
  });
}

function renderFormCanvas() {
  if (!questionSequence) return;
  
  if (state.formQuestions.length === 0) {
    questionSequence.innerHTML = '';
    dropHint.hidden = false;
    return;
  }
  
  dropHint.hidden = true;
  questionSequence.innerHTML = state.formQuestions.map((q, index) => `
    <li class="canvas-question" draggable="true" data-qid="${q.question_id}" data-qtype="${q.question_type}" data-index="${index}">
      <span class="question-order">${index + 1}</span>
      <div class="question-content">
        <div class="question-detail">${escape(q.question_detail)}</div>
        <div class="question-meta">
          <span class="question-item-badge">${q.question_type === 'uniquestion' ? 'Uni' : 'Min'}</span>
          ${q.question_title ? `<span class="question-item-badge">${escape(q.question_title)}</span>` : ''}
          <span class="question-item-badge">${q.is_required ? 'Required' : 'Optional'}</span>
        </div>
      </div>
      <div class="question-actions">
        <button class="icon-button" data-edit-canvas-q="${q.id}" title="Properties"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg></button>
        <button class="icon-button danger" data-remove-canvas-q="${q.id}" title="Remove"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
      </div>
    </li>
  `).join('');
  
  // Add drag listeners for canvas
  questionSequence.querySelectorAll('.canvas-question[draggable="true"]').forEach(item => {
    item.addEventListener('dragstart', handleCanvasDragStart);
    item.addEventListener('dragend', handleCanvasDragEnd);
    item.addEventListener('dragover', handleCanvasDragOver);
    item.addEventListener('dragleave', handleCanvasDragLeave);
    item.addEventListener('drop', handleCanvasDrop);
    item.addEventListener('click', (e) => {
      if (!e.target.closest('.question-actions')) {
        selectCanvasQuestion(item.dataset.qid, item.dataset.qtype);
      }
    });
  });
  
  // Dropzone events
  formCanvas.addEventListener('dragover', (e) => e.preventDefault());
  formCanvas.addEventListener('drop', handleCanvasZoneDrop);
}

function selectCanvasQuestion(qid, qtype) {
  // Remove previous selection
  questionSequence.querySelectorAll('.canvas-question').forEach(el => el.classList.remove('selected'));
  
  // Add selection
  const el = questionSequence.querySelector(`[data-qid="${qid}"]`);
  if (el) el.classList.add('selected');
  
  // Show properties
  const q = state.formQuestions.find(fq => fq.question_id == qid && fq.question_type === qtype);
  if (q) showQuestionProperties(q);
}

function showQuestionProperties(q) {
  if (!formProperties) return;
  
  formProperties.innerHTML = `
    <div class="props-panel" data-props-for="${q.id}">
      <h4>Question Properties</h4>
      <div class="prop-field">
        <label>Display Order</label>
        <input type="number" class="prop-order" value="${state.formQuestions.indexOf(q)}" min="0" readonly>
      </div>
      <div class="prop-field">
        <label>Question Detail</label>
        <textarea class="prop-detail" readonly>${escape(q.question_detail)}</textarea>
      </div>
      <div class="prop-field">
        <label>Question Title (Group)</label>
        <select class="prop-title">
          <option value="">— Ungrouped —</option>
          ${state.questionTitles.map(t => `<option value="${t.qTID}" ${q.question_title_id === t.qTID ? 'selected' : ''}>${escape(t.qTDetail)}</option>`).join('')}
        </select>
      </div>
      <div class="prop-field">
        <label>Required</label>
        <label class="checkbox-label"><input type="checkbox" class="prop-required" ${q.is_required ? 'checked' : ''}> Required</label>
      </div>
      <div class="prop-actions">
        <button type="button" class="btn btn-danger btn-sm prop-remove" data-remove="${q.id}">Remove from Form</button>
      </div>
    </div>
  `;
  
  // Update listeners
  formProperties.querySelector('.prop-title')?.addEventListener('change', (e) => updateQuestionTitle(q.id, e.target.value));
  formProperties.querySelector('.prop-required')?.addEventListener('change', (e) => updateQuestionRequired(q.id, e.target.checked));
  formProperties.querySelector('.prop-remove')?.addEventListener('click', () => removeQuestionFromCanvas(q.id));
}

// ============================================================
// DRAG AND DROP
// ============================================================
function initDragDrop() {
  // Available questions drag
  availableQuestions?.addEventListener('dragover', (e) => e.preventDefault());
  availableQuestions?.addEventListener('drop', (e) => e.preventDefault());
  
  // Form canvas zone
  formCanvas?.addEventListener('dragover', (e) => {
    e.preventDefault();
    formCanvas.classList.add('drag-active');
  });
  formCanvas?.addEventListener('dragleave', () => {
    formCanvas.classList.remove('drag-active');
  });
}

function handleDragStart(e) {
  e.dataTransfer.setData('text/plain', JSON.stringify({
    qid: e.currentTarget.dataset.qid,
    qtype: e.currentTarget.dataset.qtype,
    source: 'available'
  }));
  e.currentTarget.classList.add('dragging');
}

function handleDragEnd(e) {
  e.currentTarget.classList.remove('dragging');
}

function handleCanvasDragStart(e) {
  e.dataTransfer.setData('text/plain', JSON.stringify({
    qid: e.currentTarget.dataset.qid,
    qtype: e.currentTarget.dataset.qtype,
    index: e.currentTarget.dataset.index,
    source: 'canvas'
  }));
  e.currentTarget.classList.add('dragging');
}

function handleCanvasDragEnd(e) {
  e.currentTarget.classList.remove('dragging');
  questionSequence.querySelectorAll('.canvas-question').forEach(el => el.classList.remove('drag-over'));
}

function handleCanvasDragOver(e) {
  e.preventDefault();
  e.currentTarget.classList.add('drag-over');
}

function handleCanvasDragLeave(e) {
  e.currentTarget.classList.remove('drag-over');
}

function handleCanvasDrop(e) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  
  try {
    const data = JSON.parse(e.dataTransfer.getData('text/plain'));
    if (data.source === 'available') {
      addQuestionToCanvas(data.qid, data.qtype);
    } else if (data.source === 'canvas') {
      reorderCanvasQuestions(data.index, getDropIndex(e.currentTarget));
    }
  } catch (err) {
    console.error('Drop error:', err);
  }
}

function handleCanvasZoneDrop(e) {
  e.preventDefault();
  formCanvas.classList.remove('drag-active');
  
  try {
    const data = JSON.parse(e.dataTransfer.getData('text/plain'));
    if (data.source === 'available') {
      addQuestionToCanvas(data.qid, data.qtype);
    }
  } catch (err) {
    console.error('Zone drop error:', err);
  }
}

function getDropIndex(target) {
  const items = Array.from(questionSequence.querySelectorAll('.canvas-question'));
  const index = items.indexOf(target);
  return index >= 0 ? index : items.length;
}

function addQuestionToCanvas(qid, qtype) {
  const q = state.availableQuestions.find(aq => aq.question_id == qid && aq.question_type === qtype);
  if (!q) return;
  
  // Check if already in canvas
  const exists = state.formQuestions.some(fq => fq.question_id == qid && fq.question_type === qtype);
  if (exists) {
    toast('Question already in form');
    return;
  }
  
  const newQuestion = {
    id: `canvas-${Date.now()}`,
    question_id: q.question_id,
    question_type: q.question_type,
    display_order: state.formQuestions.length,
    is_required: true,
    question_detail: q.question_detail,
    question_title: q.question_title,
    question_title_id: q.question_title_id,
  };
  
  state.formQuestions.push(newQuestion);
  renderFormCanvas();
  toast('Question added to form');
}

function removeQuestionFromCanvas(canvasId) {
  state.formQuestions = state.formQuestions.filter(q => q.id !== canvasId);
  // Reorder
  state.formQuestions.forEach((q, i) => q.display_order = i);
  renderFormCanvas();
  formProperties.innerHTML = '<p class="empty-state">Click a question to edit properties</p>';
  toast('Question removed');
}

function reorderCanvasQuestions(fromIndex, toIndex) {
  if (fromIndex === toIndex) return;
  
  const [removed] = state.formQuestions.splice(fromIndex, 1);
  state.formQuestions.splice(toIndex, 0, removed);
  
  // Reorder all
  state.formQuestions.forEach((q, i) => q.display_order = i);
  
  renderFormCanvas();
}

function updateQuestionTitle(canvasId, titleId) {
  const q = state.formQuestions.find(fq => fq.id === canvasId);
  if (q) {
    q.question_title_id = titleId ? parseInt(titleId) : null;
    const title = state.questionTitles.find(t => t.qTID === q.question_title_id);
    q.question_title = title?.qTDetail || null;
    renderFormCanvas();
  }
}

function updateQuestionRequired(canvasId, required) {
  const q = state.formQuestions.find(fq => fq.id === canvasId);
  if (q) {
    q.is_required = required;
    renderFormCanvas();
  }
}

// ============================================================
// EXCEL IMPORT
// ============================================================
function initExcelImport() {
  importExcelBtn?.addEventListener('click', () => {
    excelImportDialog?.showModal();
    state.importStep = 1;
    showImportStep(1);
  });
  
  excelFileBtn?.addEventListener('click', () => excelFileInput?.click());
  
  excelFileInput?.addEventListener('change', (e) => {
    if (e.target.files[0]) handleExcelFile(e.target.files[0]);
  });
  
  excelDropZone?.addEventListener('dragover', (e) => {
    e.preventDefault();
    excelDropZone.classList.add('is-dragging');
  });
  
  excelDropZone?.addEventListener('dragleave', () => {
    excelDropZone.classList.remove('is-dragging');
  });
  
  excelDropZone?.addEventListener('drop', (e) => {
    e.preventDefault();
    excelDropZone.classList.remove('is-dragging');
    if (e.dataTransfer.files[0]) handleExcelFile(e.dataTransfer.files[0]);
  });
  
  document.getElementById('import-back')?.addEventListener('click', () => {
    state.importStep = Math.max(1, state.importStep - 1);
    showImportStep(state.importStep);
  });
  
  document.getElementById('import-confirm')?.addEventListener('click', confirmImport);
}

function showImportStep(step) {
  document.querySelectorAll('#excel-import-dialog .import-step').forEach(s => s.classList.add('hidden'));
  document.getElementById(`import-step-${step}`)?.classList.remove('hidden');
}

async function handleExcelFile(file) {
  const formData = new FormData();
  formData.append('file', file);
  
  try {
    const preview = await api('/survey/import/preview', {
      method: 'POST',
      body: formData,
      headers: {} // Let browser set multipart boundary
    });
    
    state.importData = preview;
    renderImportPreview(preview);
    state.importStep = 2;
    showImportStep(2);
  } catch (e) {
    console.error('Excel preview failed:', e);
    toast('Failed to parse Excel file');
  }
}

function renderImportPreview(preview) {
  // Detected columns
  const columnsList = document.getElementById('detected-columns');
  if (columnsList) {
    columnsList.innerHTML = preview.headers.map(h => `<li>${escape(h)}</li>`).join('');
  }
  
  // Field mappings
  const fieldMappings = document.getElementById('field-mappings');
  const dbFields = preview.detected_org_type === 'university' 
    ? ['qTDetail', 'uQDetail', 'qTID', 'yID']
    : ['qTDetail', 'mQDetail', 'qTID', 'yID'];
  
  if (fieldMappings) {
    fieldMappings.innerHTML = dbFields.map(field => {
      const suggested = preview.suggested_mapping[field] || '';
      const options = ['', ...preview.headers].map(h => 
        `<option value="${escape(h)}" ${h === suggested ? 'selected' : ''}>${escape(h) || '— Not mapped —'}</option>`
      ).join('');
      return `
        <div class="field-mapping-row">
          <label>${field}</label>
          <select name="${field}">${options}</select>
        </div>
      `;
    }).join('');
  }
  
  // Preview table
  const previewTable = document.getElementById('import-preview-table');
  if (previewTable && preview.rows.length > 0) {
    const headers = preview.headers;
    const rows = preview.rows.slice(0, 10);
    previewTable.innerHTML = `
      <table class="data-table" style="min-width:auto;">
        <thead><tr>${headers.map(h => `<th>${escape(h)}</th>`).join('')}</tr></thead>
        <tbody>${rows.map(r => `<tr>${r.map(c => `<td>${escape(String(c || ''))}</td>`).join('')}</tr>`).join('')}</tbody>
      </table>
    `;
  }
  
  // Set org type and year
  if (preview.detected_org_type) {
    builderOrgType.value = preview.detected_org_type;
    updateBuilderYearSelect();
  }
  if (preview.detected_year_id) {
    builderYear.value = preview.detected_year_id;
  }
}

async function confirmImport() {
  if (!state.importData) return;
  
  const mappings = {};
  document.querySelectorAll('#field-mappings select').forEach(sel => {
    if (sel.value) mappings[sel.name] = sel.value;
  });
  
  const createTitles = document.getElementById('import-create-titles')?.checked;
  const createQuestions = document.getElementById('import-create-questions')?.checked;
  const updateExisting = document.getElementById('import-update-existing')?.checked;
  
  // Parse rows into question data
  const questions = [];
  const titles = [];
  const titleMap = new Map(); // header value -> temp qTID
  
  state.importData.rows.forEach(row => {
    const rowData = {};
    state.importData.headers.forEach((h, i) => rowData[h] = row[i]);
    
    // Extract title
    const titleCol = mappings.qTDetail;
    if (titleCol && rowData[titleCol]) {
      const titleVal = rowData[titleCol];
      if (!titleMap.has(titleVal)) {
        const tempId = titles.length;
        titleMap.set(titleVal, tempId);
        titles.push({ qTDetail: titleVal, description: '' });
      }
      rowData._temp_qTID = titleMap.get(titleVal);
    }
    
    // Extract question
    const qCol = state.importData.detected_org_type === 'university' ? mappings.uQDetail : mappings.mQDetail;
    if (qCol && rowData[qCol]) {
      questions.push({
        [state.importData.detected_org_type === 'university' ? 'uQDetail' : 'mQDetail']: rowData[qCol],
        qTID: rowData._temp_qTID,
        yID: parseInt(rowData[mappings.yID] || state.currentYearId),
      });
    }
  });
  
  try {
    const result = await api('/survey/import/bulk', {
      method: 'POST',
      body: {
        org_type: state.importData.detected_org_type,
        year_id: state.currentYearId,
        questions,
        question_titles: titles,
      },
    });
    
    toast(`Imported: ${result.created_titles} titles, ${result.created_questions} questions`);
    excelImportDialog?.close();
    state.importStep = 1;
    showImportStep(1);
    
    // Reload data
    if (state.importData.detected_org_type === 'university') {
      await loadUniQuestions();
    } else {
      await loadMinistryQuestions();
    }
    await loadQuestionTitles();
    if (builderContent && !builderContent.hidden) {
      await loadBuilder();
    }
  } catch (e) {
    console.error('Import failed:', e);
    toast('Import failed: ' + (e.message || 'Unknown error'));
  }
}

// ============================================================
// DIALOGS
// ============================================================
function initDialogs() {
  // Year form
  document.querySelector('[data-open-dialog][data-dialog="year-form"][data-action="create"]')?.addEventListener('click', () => openYearForm());
  yearForm?.addEventListener('submit', saveYear);
  
  // Title form
  document.querySelector('[data-open-dialog][data-dialog="title-form"][data-action="create"]')?.addEventListener('click', () => openTitleForm());
  titleForm?.addEventListener('submit', saveTitle);
  
  // Question form
  document.querySelectorAll('[data-open-dialog][data-dialog="question-form"][data-action="create"]').forEach(btn => {
    btn.addEventListener('click', () => openQuestionForm(btn.dataset.qtype));
  });
  questionForm?.addEventListener('submit', saveQuestion);
  
  // Close buttons
  document.querySelectorAll('[data-close-dialog]').forEach(btn => {
    btn.addEventListener('click', () => {
      const dialog = btn.closest('dialog');
      dialog?.close();
      resetForms();
    });
  });
  
  // Click backdrop to close
  document.querySelectorAll('dialog').forEach(dialog => {
    dialog.addEventListener('click', (e) => {
      if (e.target === dialog) {
        dialog.close();
        resetForms();
      }
    });
  });
}

function resetForms() {
  yearForm?.reset();
  titleForm?.reset();
  questionForm?.reset();
  document.getElementById('year-form-id').value = '';
  document.getElementById('title-form-id').value = '';
  document.getElementById('question-form-id').value = '';
}

async function openYearForm(year = null) {
  resetForms();
  document.getElementById('year-form-title').textContent = year ? 'Edit Year' : 'Create Year';
  
  if (year) {
    document.getElementById('year-form-id').value = year.yID;
    document.getElementById('year-from').value = year.year_from;
    document.getElementById('year-to').value = year.year_to;
    document.getElementById('year-status').value = year.status;
  }
  
  yearFormDialog?.showModal();
}

async function openTitleForm(title = null) {
  resetForms();
  document.getElementById('title-form-title').textContent = title ? 'Edit Question Title' : 'Create Question Title';
  
  if (title) {
    document.getElementById('title-form-id').value = title.qTID;
    document.getElementById('title-detail').value = title.qTDetail;
    document.getElementById('title-desc').value = title.description || '';
  }
  
  titleFormDialog?.showModal();
}

async function openQuestionForm(qtype, question = null) {
  resetForms();
  document.getElementById('question-form-title').textContent = `Create ${qtype === 'university' ? 'University' : 'Ministry'} Question`;
  document.getElementById('question-form-type').value = qtype;
  
  // Populate year select
  const yearSelect = document.getElementById('question-year');
  yearSelect.innerHTML = '<option value="">Select Year</option>' + 
    state.years.map(y => `<option value="${y.yID}">${escape(y.label)}</option>`).join('');
  yearSelect.disabled = false;
  
  // Populate title select
  const titleSelect = document.getElementById('question-title');
  titleSelect.innerHTML = '<option value="">— Ungrouped —</option>' + 
    state.questionTitles.map(t => `<option value="${t.qTID}">${escape(t.qTDetail)}</option>`).join('');
  
  if (question) {
    document.getElementById('question-form-id').value = question.uQId ?? question.mQId;
    yearSelect.value = question.yID;
    titleSelect.value = question.qTID ?? '';
    document.getElementById('question-detail').value = question.uQDetail ?? question.mQDetail;
    document.getElementById('question-form-title').textContent = 'Edit Question';
  }
  questionFormDialog?.showModal();
}

async function saveYear(e) {
  e.preventDefault();
  const formData = new FormData(yearForm);
  const data = {
    year_from: parseInt(formData.get('year_from')),
    year_to: parseInt(formData.get('year_to')),
    status: parseInt(formData.get('status')),
  };
  
  const id = formData.get('yID');
  const url = id ? `/survey/years/${id}` : '/survey/years';
  const method = id ? 'put' : 'post';
  
  try {
    await api(url, { method, body: data });
    toast(id ? 'Year updated' : 'Year created');
    yearFormDialog?.close();
    resetForms();
    await loadYears();
    await loadActiveYearsForBuilder();
  } catch (err) {
    toast('Failed to save year: ' + err.message);
  }
}

async function saveTitle(e) {
  e.preventDefault();
  const formData = new FormData(titleForm);
  const data = {
    qTDetail: formData.get('qTDetail'),
    description: formData.get('description') || null,
  };
  
  const id = formData.get('qTID');
  const url = id ? `/survey/question-titles/${id}` : '/survey/question-titles';
  const method = id ? 'put' : 'post';
  
  try {
    await api(url, { method, body: data });
    toast(id ? 'Title updated' : 'Title created');
    titleFormDialog?.close();
    resetForms();
    await loadQuestionTitles();
    updateTitleFilters();
  } catch (err) {
    toast('Failed to save title: ' + err.message);
  }
}

async function saveQuestion(e) {
  e.preventDefault();
  const formData = new FormData(questionForm);
  const qtype = formData.get('question_type');
  const data = {
    [qtype === 'university' ? 'uQDetail' : 'mQDetail']: formData.get('question_detail'),
    qTID: formData.get('qTID') || null,
    yID: parseInt(formData.get('yID')),
  };
  
  const id = formData.get('question_id');
  const url = id ? `/survey/questions/${qtype}/${id}` : `/survey/questions/${qtype}`;
  const method = id ? 'put' : 'post';
  
  try {
    await api(url, { method, body: data });
    toast(id ? 'Question updated' : 'Question created');
    questionFormDialog?.close();
    resetForms();
    if (qtype === 'university') await loadUniQuestions();
    else await loadMinistryQuestions();
    if (builderContent && !builderContent.hidden) await loadBuilder();
  } catch (err) {
    toast('Failed to save question: ' + err.message);
  }
}

// ============================================================
// TABLE ACTIONS (Edit/Delete)
// ============================================================
function initEventListeners() {
  // Years table
  yearsTable?.addEventListener('click', async (e) => {
    const editBtn = e.target.closest('[data-edit-year]');
    const delBtn = e.target.closest('[data-delete-year]');
    
    if (editBtn) {
      const yid = parseInt(editBtn.dataset.editYear);
      const year = state.years.find(y => y.yID === yid);
      if (year) openYearForm(year);
    }
    
    if (delBtn) {
      const yid = parseInt(delBtn.dataset.deleteYear);
      confirmDelete(
        'Delete Year',
        `Delete year ${yid}? This cannot be undone. Questions referencing this year will prevent deletion.`,
        'Delete',
        async () => {
          try {
            await api(`/survey/years/${yid}`, { method: 'delete' });
            toast('Year deleted');
            await loadYears();
            await loadActiveYearsForBuilder();
          } catch (err) {
            toast('Failed to delete: ' + err.message);
          }
        }
      );
    }
  });
  
  // Titles table
  titlesTable?.addEventListener('click', async (e) => {
    const editBtn = e.target.closest('[data-edit-title]');
    const delBtn = e.target.closest('[data-delete-title]');
    
    if (editBtn) {
      const tid = parseInt(editBtn.dataset.editTitle);
      const title = state.questionTitles.find(t => t.qTID === tid);
      if (title) openTitleForm(title);
    }
    
    if (delBtn) {
      const tid = parseInt(delBtn.dataset.deleteTitle);
      confirmDelete(
        'Delete Question Title',
        `Delete this question title? Questions using it will become ungrouped.`,
        'Delete',
        async () => {
          try {
            await api(`/survey/question-titles/${tid}`, { method: 'delete' });
            toast('Title deleted');
            await loadQuestionTitles();
          } catch (err) {
            toast('Failed to delete: ' + err.message);
          }
        }
      );
    }
  });
  
  // Uni questions table
  uniQTable?.addEventListener('click', async (e) => {
    const editBtn = e.target.closest('[data-edit-uni-q]');
    const delBtn = e.target.closest('[data-delete-uni-q]');
    
    if (editBtn) {
      await openQuestionForm('university', state.uniQuestions.find(q => q.uQId === Number(editBtn.dataset.editUniQ)));
    }
    
    if (delBtn) {
      const qid = parseInt(delBtn.dataset.deleteUniQ);
      confirmDelete(
        'Delete University Question',
        'Delete this university question? Survey responses referencing it will prevent deletion.',
        'Delete',
        async () => {
          try {
            await api(`/survey/questions/university/${qid}`, { method: 'delete' });
            toast('Question deleted');
            await loadUniQuestions();
          } catch (err) {
            toast('Failed to delete: ' + err.message);
          }
        }
      );
    }
  });
  
  // Ministry questions table
  minQTable?.addEventListener('click', async (e) => {
    const editBtn = e.target.closest('[data-edit-min-q]');
    const delBtn = e.target.closest('[data-delete-min-q]');
    
    if (editBtn) {
      await openQuestionForm('ministry', state.ministryQuestions.find(q => q.mQId === Number(editBtn.dataset.editMinQ)));
    }
    
    if (delBtn) {
      const qid = parseInt(delBtn.dataset.deleteMinQ);
      confirmDelete(
        'Delete Ministry Question',
        'Delete this ministry question? Survey responses referencing it will prevent deletion.',
        'Delete',
        async () => {
          try {
            await api(`/survey/questions/ministry/${qid}`, { method: 'delete' });
            toast('Question deleted');
            await loadMinistryQuestions();
          } catch (err) {
            toast('Failed to delete: ' + err.message);
          }
        }
      );
    }
  });
  
  // Search inputs
  yearsSearch?.addEventListener('input', debounce(() => loadYears(), 300));
  titlesSearch?.addEventListener('input', debounce(() => loadQuestionTitles(), 300));
  uniQSearch?.addEventListener('input', debounce(() => loadUniQuestions(), 300));
  minQSearch?.addEventListener('input', debounce(() => loadMinistryQuestions(), 300));
  
  // Filters
  yearsStatusFilter?.addEventListener('change', () => loadYears());
  uniQYearFilter?.addEventListener('change', () => loadUniQuestions());
  uniQTitleFilter?.addEventListener('change', () => loadUniQuestions());
  minQYearFilter?.addEventListener('change', () => loadMinistryQuestions());
  minQTitleFilter?.addEventListener('change', () => loadMinistryQuestions());
  
  // Builder controls
  builderOrgType?.addEventListener('change', updateBuilderYearSelect);
  loadBuilderBtn?.addEventListener('click', loadBuilder);
  
  availableQSearch?.addEventListener('input', debounce(renderAvailableQuestions, 300));
  availableTitleFilter?.addEventListener('change', renderAvailableQuestions);
  
  // Builder actions
  previewFormBtn?.addEventListener('click', previewForm);
  saveFormBtn?.addEventListener('click', saveFormStructure);
}

function previewForm() {
  if (state.formQuestions.length === 0) {
    toast('No questions in form');
    return;
  }
  // Navigate to public survey preview
  const url = `/surveys/${state.currentOrgType}/${state.currentYearId}`;
  window.open(url, '_blank');
}

function builderPeriod() {
  const period = state.years.find(y => y.yID === state.currentYearId);
  if (!period) return {};
  const month = String(period.year_from).padStart(2, '0');
  const lastDay = new Date(period.year_to, period.year_from, 0).getDate();
  return { reporting_start: `${period.year_to}-${month}-01`, reporting_end: `${period.year_to}-${month}-${lastDay}` };
}

async function saveFormStructure() {
  if (!state.formQuestions.length) return toast('Add questions before saving.');
  saveFormBtn.disabled = true;
  try {
    const sections = [];
    for (const q of state.formQuestions) {
      const title = q.question_title || 'မေးခွန်းများ';
      let section = sections.find(s => s.title === title);
      if (!section) { section = { title, questions: [] }; sections.push(section); }
      const key = `q${q.question_id}`;
      for (const [suffix, label, kind] of [
        ['present', 'ရှိ / မရှိ', 'yes_no'],
        ['count', 'အရေအတွက်', 'number'],
        ['details', 'အကြောင်းအရာ', 'long_text'],
      ]) section.questions.push({ key: `${key}_${suffix}`, title: `${q.question_detail} — ${label}`, kind, required: suffix === 'present' && q.is_required });
    }
    const form = await api('/forms', { method: 'POST', body: { title: canvasTitle.textContent, audience: state.currentOrgType } });
    const version = form.versions[0];
    await api(`/forms/${form.id}/versions/${version.id}`, { method: 'PUT', body: { title: form.title, revision: version.revision, sections, ...builderPeriod() } });
    location.href = `/dashboard/forms/${form.id}`;
  } catch (error) {
    toast(error.message);
  } finally { saveFormBtn.disabled = false; }
}

// ============================================================
// UTILITIES
// ============================================================
function debounce(fn, delay) {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn.apply(this, args), delay);
  };
}