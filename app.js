/**
 * Creative Radar - Interactive Frontend Application
 * Vanilla JS with zero external dependencies, accessible, and responsive.
 */

(function () {
  'use strict';

  // State Management
  const state = {
    items: [],
    healthData: null,
    payloadMeta: null,
    activeView: 'all',
    categoryFilter: 'all',
    trustFilter: 'all',
    sortBy: 'priority',
    searchQuery: '',
    unreadOnly: false,
    savedItemIds: new Set(),
    readItemIds: new Set(),
    briefingExpanded: true,
  };

  // DOM Elements
  const elements = {
    cardsContainer: document.getElementById('cards-container'),
    emptyState: document.getElementById('empty-state'),
    emptyResetBtn: document.getElementById('empty-reset-btn'),
    errorState: document.getElementById('error-state'),
    errorDesc: document.getElementById('error-desc'),
    errorRetryBtn: document.getElementById('error-retry-btn'),
    errorDemoBtn: document.getElementById('error-demo-btn'),
    briefingSection: document.getElementById('briefing-section'),
    briefingItems: document.getElementById('briefing-items'),
    briefingDate: document.getElementById('briefing-date'),
    toggleBriefingBtn: document.getElementById('toggle-briefing-btn'),
    briefingToggleIcon: document.getElementById('briefing-toggle-icon'),
    searchInput: document.getElementById('search-input'),
    clearSearchBtn: document.getElementById('clear-search-btn'),
    categoryFilter: document.getElementById('category-filter'),
    trustFilter: document.getElementById('trust-filter'),
    sortSelect: document.getElementById('sort-select'),
    toggleUnreadBtn: document.getElementById('toggle-unread-btn'),
    markAllReadBtn: document.getElementById('mark-all-read-btn'),
    refreshDataBtn: document.getElementById('refresh-data-btn'),
    filterChipsBar: document.getElementById('filter-chips-bar'),
    filterChips: document.getElementById('filter-chips'),
    resetFiltersBtn: document.getElementById('reset-filters-btn'),
    navTabs: document.querySelectorAll('.nav-tab'),
    staleBanner: document.getElementById('stale-banner'),
    demoBanner: document.getElementById('demo-banner'),
    dismissDemoBtn: document.getElementById('dismiss-demo-btn'),
    statTotalItems: document.getElementById('stat-total-items'),
    statUrgentAlerts: document.getElementById('stat-urgent-alerts'),
    statGeminiStatus: document.getElementById('stat-gemini-status'),
    statLastRun: document.getElementById('stat-last-run'),
    statLastRunRel: document.getElementById('stat-last-run-rel'),
    systemStatusBadge: document.getElementById('system-status-badge'),
    themeToggle: document.getElementById('theme-toggle'),
    themeIcon: document.getElementById('theme-icon'),
    healthModal: document.getElementById('health-modal'),
    healthModalBtn: document.getElementById('health-modal-btn'),
    closeModalBtn: document.getElementById('close-modal-btn'),
    modalDoneBtn: document.getElementById('modal-done-btn'),
    healthTableBody: document.getElementById('health-table-body'),
    healthLastChecked: document.getElementById('health-last-checked'),
    modalStatusBadge: document.getElementById('modal-status-badge'),
    toastContainer: document.getElementById('toast-container'),
    counts: {
      all: document.getElementById('count-all'),
      urgent: document.getElementById('count-urgent'),
      firmware: document.getElementById('count-firmware'),
      software: document.getElementById('count-software'),
      offers: document.getElementById('count-offers'),
      saved: document.getElementById('count-saved'),
    },
  };

  // Local Storage Helpers
  function loadPersistedState() {
    try {
      const saved = localStorage.getItem('creative_radar_saved');
      if (saved) state.savedItemIds = new Set(JSON.parse(saved));

      const read = localStorage.getItem('creative_radar_read');
      if (read) state.readItemIds = new Set(JSON.parse(read));

      const savedTheme = localStorage.getItem('creative_radar_theme') || 'dark';
      document.documentElement.setAttribute('data-theme', savedTheme);
      updateThemeIcon(savedTheme);
    } catch (e) {
      console.warn('Could not read localStorage:', e);
    }
  }

  function savePersistedState() {
    try {
      localStorage.setItem('creative_radar_saved', JSON.stringify(Array.from(state.savedItemIds)));
      localStorage.setItem('creative_radar_read', JSON.stringify(Array.from(state.readItemIds)));
    } catch (e) {
      console.warn('Could not save to localStorage:', e);
    }
  }

  // Theme Management
  function updateThemeIcon(theme) {
    if (elements.themeIcon) {
      elements.themeIcon.textContent = theme === 'light' ? '🌙' : '☀️';
    }
  }

  function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', nextTheme);
    localStorage.setItem('creative_radar_theme', nextTheme);
    updateThemeIcon(nextTheme);
  }

  // Toast Notification
  function showToast(message, icon = '✓') {
    if (!elements.toastContainer) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `<span aria-hidden="true">${icon}</span> <span>${escapeHtml(message)}</span>`;
    elements.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 300ms ease';
      setTimeout(() => toast.remove(), 300);
    }, 2500);
  }

  // Format Dates
  function formatRelativeTime(isoString) {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      const now = new Date();
      const diffSecs = Math.floor((now - date) / 1000);

      if (diffSecs < 60) return 'Just now';
      if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)}m ago`;
      if (diffSecs < 86400) return `${Math.floor(diffSecs / 3600)}h ago`;
      if (diffSecs < 604800) return `${Math.floor(diffSecs / 86400)}d ago`;

      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch (e) {
      return '';
    }
  }

  function formatDateTime(isoString) {
    if (!isoString) return '--';
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (e) {
      return isoString;
    }
  }

  function escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Data Ingestion
  async function fetchRadarData(forceDemo = false) {
    if (elements.cardsContainer) {
      elements.cardsContainer.innerHTML = `
        <div class="loading-state">
          <div class="spinner" aria-hidden="true"></div>
          <p>Loading curated creative intelligence...</p>
        </div>`;
    }
    if (elements.errorState) elements.errorState.classList.add('hidden');
    if (elements.emptyState) elements.emptyState.classList.add('hidden');

    try {
      const targetUrl = forceDemo ? 'data/demo_radar.json' : 'data/radar.json';
      let response = await fetch(targetUrl);
      if (!response.ok && !forceDemo) {
        console.warn('Could not load data/radar.json, falling back to data/demo_radar.json');
        response = await fetch('data/demo_radar.json');
      }
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: Unable to load ${targetUrl}`);
      }
      const data = await response.json();
      state.payloadMeta = data;
      state.items = data.items || [];
      initOverviewKPIs(data);
      if (elements.errorState) elements.errorState.classList.add('hidden');
      return true;
    } catch (err) {
      console.error('Failed to load radar data:', err);
      state.items = [];
      if (elements.cardsContainer) elements.cardsContainer.innerHTML = '';
      if (elements.errorState) {
        elements.errorState.classList.remove('hidden');
        if (elements.errorDesc) {
          const isFileProtocol = window.location.protocol === 'file:';
          elements.errorDesc.innerHTML = isFileProtocol
            ? 'Browser security restricts direct <code>file://</code> data fetching. Please run <code>.\\serve.bat</code> in PowerShell to preview via local web server (<code>http://localhost:8000</code>).'
            : `Could not load intelligence data (${escapeHtml(err.message)}). Ensure <code>data/radar.json</code> exists or click below to load sample data.`;
        }
      }
      return false;
    }
  }

  async function fetchHealthData() {
    try {
      const response = await fetch('data/health.json');
      if (response.ok) {
        state.healthData = await response.json();
      }
    } catch (err) {
      console.warn('Health data not yet available.');
    }
  }

  // KPI & Metric Updates
  function initOverviewKPIs(meta) {
    if (!meta) return;

    if (elements.statTotalItems) {
      elements.statTotalItems.textContent = meta.total_items ?? state.items.length;
    }
    if (elements.statUrgentAlerts) {
      const urgentCount = state.items.filter(i => (i.urgency_score >= 8.5 || i.composite_priority >= 8.5)).length;
      elements.statUrgentAlerts.textContent = urgentCount;
    }
    if (elements.statGeminiStatus) {
      elements.statGeminiStatus.textContent = meta.gemini_enabled ? 'Gemini 2.5' : 'Extractive';
    }
    if (elements.statLastRun) {
      elements.statLastRun.textContent = formatDateTime(meta.generated_at);
    }
    if (elements.statLastRunRel) {
      elements.statLastRunRel.textContent = formatRelativeTime(meta.generated_at);
    }

    // Stale banner
    if (meta.is_stale && elements.staleBanner) {
      elements.staleBanner.classList.remove('hidden');
    }

    // Demo banner
    if (meta.is_demo && elements.demoBanner) {
      elements.demoBanner.classList.remove('hidden');
    }
  }

  // Category Icon Resolver
  function getCategoryEmoji(cat) {
    const emojis = {
      'adobe': '🎨',
      'davinci-blackmagic': '🎞️',
      'cameras-lenses-firmware': '📷',
      'motion-vfx-blender': '🧊',
      'design-fonts-plugins': '✒️',
      'ai-tools-offers': '🤖',
      'photography-filmmaking-freelance': '🎬',
    };
    return emojis[cat] || '📡';
  }

  // Render Today's Briefing Hero
  function renderBriefing() {
    if (!elements.briefingItems) return;

    if (elements.briefingDate && state.payloadMeta?.generated_at) {
      elements.briefingDate.textContent = `Ingested: ${formatDateTime(state.payloadMeta.generated_at)}`;
    }

    // Top 3-4 highest composite priority items
    const topItems = [...state.items]
      .sort((a, b) => b.composite_priority - a.composite_priority)
      .slice(0, 4);

    if (topItems.length === 0) {
      elements.briefingItems.innerHTML = '<p class="text-muted text-sm">No briefing items compiled yet.</p>';
      return;
    }

    elements.briefingItems.innerHTML = topItems.map(item => `
      <article class="briefing-card">
        <div class="briefing-meta">
          <span class="badge ${item.is_official ? 'badge-operational' : 'badge-pulse'}">
            ${getCategoryEmoji(item.category)} ${escapeHtml(item.verification_label)}
          </span>
          <span class="priority-pill ${item.composite_priority >= 8.5 ? 'priority-critical' : ''}">
            ⚡ ${item.composite_priority}/10
          </span>
        </div>
        <a href="${escapeHtml(item.link || item.canonical_url)}" target="_blank" rel="noopener noreferrer" class="briefing-item-title">
          ${escapeHtml(item.title)}
        </a>
        <ul class="briefing-bullets">
          <li><strong>What:</strong> ${escapeHtml(item.summary_what || item.title)}</li>
          ${item.summary_why ? `<li><strong>Impact:</strong> ${escapeHtml(item.summary_why)}</li>` : ''}
          ${item.summary_action ? `<li><strong>Action:</strong> ${escapeHtml(item.summary_action)}</li>` : ''}
        </ul>
      </article>
    `).join('');
  }

  // Filter & Search Logic
  function getFilteredItems() {
    const q = state.searchQuery.trim().toLowerCase();

    return state.items.filter(item => {
      // 1. Navigation Tab View Filter
      if (state.activeView === 'urgent') {
        if (!(item.urgency_score >= 8.5 || item.composite_priority >= 8.5)) return false;
      } else if (state.activeView === 'firmware') {
        if (!item.is_firmware) return false;
      } else if (state.activeView === 'software') {
        if (!item.is_software_update) return false;
      } else if (state.activeView === 'offers') {
        if (!item.is_offer) return false;
      } else if (state.activeView === 'saved') {
        if (!state.savedItemIds.has(item.id)) return false;
      }

      // 2. Category Dropdown
      if (state.categoryFilter !== 'all' && item.category !== state.categoryFilter) {
        return false;
      }

      // 3. Trust Level Dropdown
      if (state.trustFilter !== 'all' && item.trust_level !== state.trustFilter) {
        return false;
      }

      // 4. Unread Only Filter
      if (state.unreadOnly && state.readItemIds.has(item.id)) {
        return false;
      }

      // 5. Search Query
      if (q) {
        const titleMatch = item.title.toLowerCase().includes(q);
        const sourceMatch = item.source_name.toLowerCase().includes(q);
        const whatMatch = (item.summary_what || '').toLowerCase().includes(q);
        const whyMatch = (item.summary_why || '').toLowerCase().includes(q);
        const tagMatch = (item.tags || []).some(t => t.toLowerCase().includes(q));
        const codeMatch = item.offer_details?.coupon_code?.toLowerCase().includes(q);
        if (!titleMatch && !sourceMatch && !whatMatch && !whyMatch && !tagMatch && !codeMatch) {
          return false;
        }
      }

      return true;
    });
  }

  function sortItems(items) {
    const sorted = [...items];
    switch (state.sortBy) {
      case 'priority':
        return sorted.sort((a, b) => b.composite_priority - a.composite_priority || b.published_at.localeCompare(a.published_at));
      case 'newest':
        return sorted.sort((a, b) => b.published_at.localeCompare(a.published_at));
      case 'urgency':
        return sorted.sort((a, b) => b.urgency_score - a.urgency_score);
      case 'value':
        return sorted.sort((a, b) => b.value_score - a.value_score);
      case 'reliability':
        return sorted.sort((a, b) => b.reliability_score - a.reliability_score);
      default:
        return sorted;
    }
  }

  // Update Tab Badges Count
  function updateTabCounts() {
    if (elements.counts.all) elements.counts.all.textContent = state.items.length;
    if (elements.counts.urgent) {
      elements.counts.urgent.textContent = state.items.filter(i => (i.urgency_score >= 8.5 || i.composite_priority >= 8.5)).length;
    }
    if (elements.counts.firmware) {
      elements.counts.firmware.textContent = state.items.filter(i => i.is_firmware).length;
    }
    if (elements.counts.software) {
      elements.counts.software.textContent = state.items.filter(i => i.is_software_update).length;
    }
    if (elements.counts.offers) {
      elements.counts.offers.textContent = state.items.filter(i => i.is_offer).length;
    }
    if (elements.counts.saved) {
      elements.counts.saved.textContent = state.savedItemIds.size;
    }
  }

  // Filter Chips UI
  function updateFilterChips() {
    if (!elements.filterChipsBar || !elements.filterChips) return;

    const chips = [];
    if (state.searchQuery) {
      chips.push({ label: `Query: "${state.searchQuery}"`, type: 'search' });
    }
    if (state.categoryFilter !== 'all') {
      chips.push({ label: `Category: ${state.categoryFilter}`, type: 'category' });
    }
    if (state.trustFilter !== 'all') {
      chips.push({ label: `Trust: ${state.trustFilter}`, type: 'trust' });
    }
    if (state.unreadOnly) {
      chips.push({ label: 'Filter: Unread Only', type: 'unread' });
    }

    if (chips.length > 0) {
      elements.filterChipsBar.classList.remove('hidden');
      elements.filterChips.innerHTML = chips.map(c => `
        <span class="filter-chip">
          ${escapeHtml(c.label)}
          <button class="filter-chip-remove" data-chip-type="${c.type}" aria-label="Remove filter">✕</button>
        </span>
      `).join('');
    } else {
      elements.filterChipsBar.classList.add('hidden');
      elements.filterChips.innerHTML = '';
    }
  }

  // Render Radar Cards
  function renderCards() {
    const filtered = getFilteredItems();
    const sorted = sortItems(filtered);

    updateTabCounts();
    updateFilterChips();

    if (sorted.length === 0) {
      elements.cardsContainer.innerHTML = '';
      elements.emptyState.classList.remove('hidden');
      return;
    }

    elements.emptyState.classList.add('hidden');

    elements.cardsContainer.innerHTML = sorted.map(item => {
      const isSaved = state.savedItemIds.has(item.id);
      const isRead = state.readItemIds.has(item.id);
      const isUrgent = item.urgency_score >= 8.5 || item.composite_priority >= 8.5;
      const trustClass = item.trust_level === 'official' ? 'trust-official' : (item.trust_level === 'reputable' ? 'trust-reputable' : 'trust-community');

      // Offer Box markup
      let offerHtml = '';
      if (item.offer_details) {
        const off = item.offer_details;
        offerHtml = `
          <div class="offer-box">
            <div class="offer-header">
              <span class="offer-discount">🏷️ ${escapeHtml(off.discount || 'Special Offer')}</span>
              ${off.coupon_code ? `
                <div class="offer-coupon-group">
                  <span class="coupon-code">${escapeHtml(off.coupon_code)}</span>
                  <button class="btn-copy-code" data-code="${escapeHtml(off.coupon_code)}" title="Copy discount code">Copy</button>
                </div>
              ` : ''}
            </div>
            <div class="offer-details-list">
              <span>📍 Region: <strong>${escapeHtml(off.region || 'Global')}</strong></span>
              <span>👥 Eligibility: <strong>${escapeHtml(off.eligibility || 'All users')}</strong></span>
              ${off.expires_at ? `<span>⏳ Expiry: <strong>${escapeHtml(off.expires_at)}</strong></span>` : ''}
            </div>
          </div>
        `;
      }

      // Media thumbnail fallback
      const fallbackThumb = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400" viewBox="0 0 800 400"><rect fill="%23111622" width="800" height="400"/><text fill="%2338bdf8" font-family="sans-serif" font-size="28" font-weight="bold" x="50%" y="50%" dominant-baseline="middle" text-anchor="middle">📡 CREATIVE RADAR</text></svg>';
      const imageUrl = item.image_url || fallbackThumb;

      return `
        <article class="radar-card ${isRead ? 'is-read' : ''} ${isUrgent ? 'is-urgent' : ''}" data-id="${escapeHtml(item.id)}">
          <div class="card-media">
            <img src="${escapeHtml(imageUrl)}" alt="" class="card-image" loading="lazy" onerror="this.onerror=null;this.src='${fallbackThumb}';">
          </div>
          <div class="card-body">
            <div class="card-meta-row">
              <div class="meta-source-group">
                <span class="source-name">${getCategoryEmoji(item.category)} ${escapeHtml(item.source_name)}</span>
                <span class="trust-badge ${trustClass}">${escapeHtml(item.verification_label)}</span>
              </div>
              <span class="priority-pill ${item.composite_priority >= 8.5 ? 'priority-critical' : ''}" title="Composite Priority Score">
                ⚡ ${item.composite_priority}
              </span>
            </div>

            <h3 class="card-title">
              <a href="${escapeHtml(item.link || item.canonical_url)}" target="_blank" rel="noopener noreferrer" class="card-title-link">
                ${escapeHtml(item.title)}
              </a>
            </h3>

            <!-- 3-Part Intelligence Block -->
            <div class="summary-block">
              <div class="summary-item summary-item-what">
                <span class="summary-label">📌 What happened</span>
                <p class="summary-text">${escapeHtml(item.summary_what || item.title)}</p>
              </div>
              ${item.summary_why ? `
                <div class="summary-item summary-item-why">
                  <span class="summary-label">💡 Why it matters</span>
                  <p class="summary-text">${escapeHtml(item.summary_why)}</p>
                </div>
              ` : ''}
              ${item.summary_action ? `
                <div class="summary-item summary-item-action">
                  <span class="summary-label">⚡ Practical next steps</span>
                  <p class="summary-text">${escapeHtml(item.summary_action)}</p>
                </div>
              ` : ''}
            </div>

            ${offerHtml}

            <div class="card-footer">
              <span class="card-date" title="${escapeHtml(item.published_at)}">
                🕒 ${formatRelativeTime(item.published_at)}
              </span>
              <div class="card-actions">
                <button class="btn-card-action btn-toggle-read" data-id="${escapeHtml(item.id)}" title="${isRead ? 'Mark unread' : 'Mark as read'}">
                  ${isRead ? 'Mark unread' : 'Mark read'}
                </button>
                <button class="btn-card-action btn-toggle-bookmark ${isSaved ? 'active-bookmark' : ''}" data-id="${escapeHtml(item.id)}" title="${isSaved ? 'Remove bookmark' : 'Bookmark story'}">
                  ${isSaved ? '★ Saved' : '☆ Save'}
                </button>
                <a href="${escapeHtml(item.link || item.canonical_url)}" target="_blank" rel="noopener noreferrer" class="btn-card-action" title="Open source">
                  🔗 Link
                </a>
              </div>
            </div>
          </div>
        </article>
      `;
    }).join('');
  }

  // Health Modal Diagnostics
  function openHealthModal() {
    if (!elements.healthModal) return;

    if (!state.healthData) {
      elements.healthTableBody.innerHTML = '<tr><td colspan="6" class="text-center">No diagnostic health run records found yet.</td></tr>';
      elements.healthModal.showModal();
      return;
    }

    const { sources, overall_system_status, last_checked_at } = state.healthData;

    if (elements.modalStatusBadge) {
      elements.modalStatusBadge.textContent = overall_system_status || 'Operational';
      elements.modalStatusBadge.className = `badge ${overall_system_status === 'Operational' ? 'badge-operational' : 'badge-pulse'}`;
    }

    if (elements.healthLastChecked) {
      elements.healthLastChecked.textContent = `Last run: ${formatDateTime(last_checked_at)}`;
    }

    if (elements.healthTableBody && Array.isArray(sources)) {
      elements.healthTableBody.innerHTML = sources.map(s => `
        <tr>
          <td><strong>${escapeHtml(s.source_name)}</strong></td>
          <td>${escapeHtml(s.category)}</td>
          <td><code>HTTP ${s.status_code || '--'}</code></td>
          <td>${s.response_time_ms ? `${s.response_time_ms}ms` : '--'}</td>
          <td>${s.items_fetched ?? 0} items</td>
          <td>
            <span class="badge ${s.is_healthy ? 'badge-operational' : 'badge-pulse'}">
              ${s.is_healthy ? 'Healthy' : 'Degraded'}
            </span>
          </td>
        </tr>
      `).join('');
    }

    elements.healthModal.showModal();
  }

  function closeHealthModal() {
    if (elements.healthModal) elements.healthModal.close();
  }

  // Event Listeners
  function setupEventListeners() {
    // Theme toggle
    if (elements.themeToggle) {
      elements.themeToggle.addEventListener('click', toggleTheme);
    }

    // Navigation tab switching
    elements.navTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        elements.navTabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        state.activeView = tab.getAttribute('data-view');
        renderCards();
      });
    });

    // Search input
    if (elements.searchInput) {
      elements.searchInput.addEventListener('input', (e) => {
        state.searchQuery = e.target.value;
        if (elements.clearSearchBtn) {
          elements.clearSearchBtn.classList.toggle('hidden', !state.searchQuery);
        }
        renderCards();
      });
    }

    if (elements.clearSearchBtn) {
      elements.clearSearchBtn.addEventListener('click', () => {
        state.searchQuery = '';
        elements.searchInput.value = '';
        elements.clearSearchBtn.classList.add('hidden');
        renderCards();
      });
    }

    // Dropdowns
    if (elements.categoryFilter) {
      elements.categoryFilter.addEventListener('change', (e) => {
        state.categoryFilter = e.target.value;
        renderCards();
      });
    }

    if (elements.trustFilter) {
      elements.trustFilter.addEventListener('change', (e) => {
        state.trustFilter = e.target.value;
        renderCards();
      });
    }

    if (elements.sortSelect) {
      elements.sortSelect.addEventListener('change', (e) => {
        state.sortBy = e.target.value;
        renderCards();
      });
    }

    // Reset filters
    const resetAllFilters = () => {
      state.searchQuery = '';
      state.categoryFilter = 'all';
      state.trustFilter = 'all';
      state.unreadOnly = false;
      if (elements.searchInput) elements.searchInput.value = '';
      if (elements.categoryFilter) elements.categoryFilter.value = 'all';
      if (elements.trustFilter) elements.trustFilter.value = 'all';
      if (elements.clearSearchBtn) elements.clearSearchBtn.classList.add('hidden');
      if (elements.toggleUnreadBtn) elements.toggleUnreadBtn.setAttribute('aria-pressed', 'false');
      renderCards();
    };

    if (elements.resetFiltersBtn) elements.resetFiltersBtn.addEventListener('click', resetAllFilters);
    if (elements.emptyResetBtn) elements.emptyResetBtn.addEventListener('click', resetAllFilters);

    // Filter chip removal delegation
    if (elements.filterChips) {
      elements.filterChips.addEventListener('click', (e) => {
        const btn = e.target.closest('.filter-chip-remove');
        if (!btn) return;
        const type = btn.getAttribute('data-chip-type');
        if (type === 'search') {
          state.searchQuery = '';
          if (elements.searchInput) elements.searchInput.value = '';
          if (elements.clearSearchBtn) elements.clearSearchBtn.classList.add('hidden');
        } else if (type === 'category') {
          state.categoryFilter = 'all';
          if (elements.categoryFilter) elements.categoryFilter.value = 'all';
        } else if (type === 'trust') {
          state.trustFilter = 'all';
          if (elements.trustFilter) elements.trustFilter.value = 'all';
        } else if (type === 'unread') {
          state.unreadOnly = false;
          if (elements.toggleUnreadBtn) elements.toggleUnreadBtn.setAttribute('aria-pressed', 'false');
        }
        renderCards();
      });
    }

    // Briefing collapse toggle
    if (elements.toggleBriefingBtn) {
      elements.toggleBriefingBtn.addEventListener('click', () => {
        state.briefingExpanded = !state.briefingExpanded;
        elements.briefingItems.classList.toggle('hidden', !state.briefingExpanded);
        elements.briefingToggleIcon.textContent = state.briefingExpanded ? '−' : '+';
        elements.toggleBriefingBtn.setAttribute('aria-expanded', state.briefingExpanded);
      });
    }

    // Card Actions Delegation (Save, Read, Copy Coupon)
    document.addEventListener('click', (e) => {
      // Copy discount code
      const copyBtn = e.target.closest('.btn-copy-code');
      if (copyBtn) {
        const code = copyBtn.getAttribute('data-code');
        if (code) {
          navigator.clipboard.writeText(code).then(() => {
            showToast(`Coupon code '${code}' copied to clipboard!`, '📋');
          }).catch(() => {
            showToast(`Code: ${code}`, '📋');
          });
        }
        return;
      }

      // Bookmark toggle
      const bookmarkBtn = e.target.closest('.btn-toggle-bookmark');
      if (bookmarkBtn) {
        const id = bookmarkBtn.getAttribute('data-id');
        if (state.savedItemIds.has(id)) {
          state.savedItemIds.delete(id);
          showToast('Removed from bookmarks');
        } else {
          state.savedItemIds.add(id);
          showToast('Story saved to bookmarks', '★');
        }
        savePersistedState();
        renderCards();
        return;
      }

      // Read status toggle
      const readBtn = e.target.closest('.btn-toggle-read');
      if (readBtn) {
        const id = readBtn.getAttribute('data-id');
        if (state.readItemIds.has(id)) {
          state.readItemIds.delete(id);
        } else {
          state.readItemIds.add(id);
        }
        savePersistedState();
        renderCards();
        return;
      }
    });

    // Health Modal buttons
    if (elements.healthModalBtn) elements.healthModalBtn.addEventListener('click', openHealthModal);
    if (elements.closeModalBtn) elements.closeModalBtn.addEventListener('click', closeHealthModal);
    if (elements.modalDoneBtn) elements.modalDoneBtn.addEventListener('click', closeHealthModal);

    // Dismiss demo banner
    if (elements.dismissDemoBtn) {
      elements.dismissDemoBtn.addEventListener('click', () => {
        elements.demoBanner.classList.add('hidden');
      });
    }

    // Refresh button — re-fetch data and re-render
    if (elements.refreshDataBtn) {
      elements.refreshDataBtn.addEventListener('click', async () => {
        await fetchRadarData();
        renderBriefing();
        renderCards();
        showToast('Dashboard refreshed', '🔄');
      });
    }

    // Unread Only toggle
    if (elements.toggleUnreadBtn) {
      elements.toggleUnreadBtn.addEventListener('click', () => {
        state.unreadOnly = !state.unreadOnly;
        elements.toggleUnreadBtn.setAttribute('aria-pressed', String(state.unreadOnly));
        renderCards();
        updateFilterChips();
      });
    }

    // Mark All Read — marks every currently visible item as read
    if (elements.markAllReadBtn) {
      elements.markAllReadBtn.addEventListener('click', () => {
        const filtered = getFilteredItems();
        filtered.forEach(item => state.readItemIds.add(item.id));
        savePersistedState();
        renderCards();
        showToast(`Marked ${filtered.length} stor${filtered.length === 1 ? 'y' : 'ies'} as read`, '✓');
      });
    }

    // Error state — Retry button re-fetches real data
    if (elements.errorRetryBtn) {
      elements.errorRetryBtn.addEventListener('click', async () => {
        await fetchRadarData();
        renderBriefing();
        renderCards();
      });
    }

    // Error state — Load Demo button forces demo data
    if (elements.errorDemoBtn) {
      elements.errorDemoBtn.addEventListener('click', async () => {
        await fetchRadarData(true); // forceDemo = true
        renderBriefing();
        renderCards();
      });
    }
  }

  // Application Entry Point
  async function init() {
    loadPersistedState();
    setupEventListeners();
    await fetchRadarData();
    await fetchHealthData();
    renderBriefing();
    renderCards();
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
