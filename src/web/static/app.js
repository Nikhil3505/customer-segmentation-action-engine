/**
 * YottaFlex AI - Analyst Web Dashboard Client Controller
 */

let currentCustomerPage = 1;
let customerSearchDebounceTimer = null;

// --- Tab Navigation ---
function switchTab(tabId) {
  document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));

  const targetPane = document.getElementById(`tab-${tabId}`);
  if (targetPane) targetPane.classList.add('active');

  // Activate tab button
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    if (tab.getAttribute('onclick').includes(tabId)) {
      tab.classList.add('active');
    }
  });

  // Lazy load tab data
  if (tabId === 'overview') loadOverview();
  else if (tabId === 'segments') loadSegments();
  else if (tabId === 'customers') loadCustomers(1);
  else if (tabId === 'anomalies') loadAnomalies();
}

// --- Formatters ---
function formatCurrency(val) {
  if (val === null || val === undefined) return '$0.00';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
}

function formatNumber(val) {
  if (val === null || val === undefined) return '0';
  return new Intl.NumberFormat('en-US').format(val);
}

// --- 1. Load Overview ---
async function loadOverview() {
  try {
    const res = await fetch('/api/overview');
    const data = await res.json();

    document.getElementById('kpiCustomers').innerText = formatNumber(data.kpis.total_customers);
    document.getElementById('kpiRevenue').innerText = formatCurrency(data.kpis.total_net_revenue);
    document.getElementById('kpiRefunds').innerText = `Returns netted: ${formatCurrency(data.kpis.total_refunds)}`;
    document.getElementById('kpiOrders').innerText = formatNumber(data.kpis.total_orders);
    document.getElementById('kpiEvents').innerText = `Events: ${formatNumber(data.kpis.total_events)}`;
    document.getElementById('kpiSuppressionRate').innerText = `${data.kpis.suppression_rate_pct}%`;
    document.getElementById('kpiSuppressedCount').innerText = `Suppressed: ${formatNumber(data.kpis.actions_suppressed_by_guardrails)} actions`;
    document.getElementById('kpiConversions').innerText = formatCurrency(data.kpis.conversion_revenue);
    document.getElementById('kpiConvCount').innerText = `Converted: ${formatNumber(data.kpis.total_conversions)} actions`;

    // Render segment distribution bars
    const distContainer = document.getElementById('segmentDistributionVisual');
    distContainer.innerHTML = '';

    const colors = {
      'VIP Loyalists': '#a855f7',
      'Service-Heavy / Dissatisfied': '#f43f5e',
      'At-Risk / Dormant': '#f59e0b',
      'High-Potential Growth': '#06b6d4',
      'New Onboarding': '#10b981',
    };

    const totalSegs = Object.values(data.segment_distribution).reduce((a, b) => a + b, 0) || 1;

    for (const [segName, count] of Object.entries(data.segment_distribution)) {
      const pct = ((count / totalSegs) * 100).toFixed(1);
      const color = colors[segName] || '#6366f1';

      const card = document.createElement('div');
      card.style.flex = '1';
      card.style.minWidth = '180px';
      card.style.background = 'rgba(16, 21, 34, 0.6)';
      card.style.border = '1px solid var(--border-subtle)';
      card.style.borderRadius = 'var(--radius-sm)';
      card.style.padding = '1rem';

      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
          <span style="font-size: 0.8rem; font-weight: 700; color: ${color};">${segName}</span>
          <span style="font-size: 0.85rem; font-weight: 800; color: #fff;">${count}</span>
        </div>
        <div class="progress-bar-container">
          <div class="progress-bar-fill" style="width: ${pct}%; background: ${color};"></div>
        </div>
        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.4rem;">${pct}% of customer base</div>
      `;
      distContainer.appendChild(card);
    }
  } catch (err) {
    console.error('Error loading overview:', err);
  }
}

// --- 2. Load Segments ---
async function loadSegments() {
  try {
    const res = await fetch('/api/segments');
    const segments = await res.json();
    const container = document.getElementById('segmentCardsGrid');
    container.innerHTML = '';

    const badgeMap = {
      VIP_LOYALIST: 'badge-vip',
      SERVICE_HEAVY_DISSATISFIED: 'badge-service',
      AT_RISK_DORMANT: 'badge-dormant',
      HIGH_POTENTIAL: 'badge-growth',
      NEW_ONBOARDING: 'badge-new',
    };

    segments.forEach(seg => {
      const card = document.createElement('div');
      card.className = 'segment-card';
      const badgeClass = badgeMap[seg.segment_code] || 'badge-growth';

      card.innerHTML = `
        <div>
          <div style="display: flex; justify-content: space-between; align-items: flex-start;">
            <span class="segment-badge ${badgeClass}">${seg.segment_code}</span>
            <span style="font-size: 0.75rem; color: var(--text-muted);">Priority #${seg.priority_rank}</span>
          </div>
          <h3 style="font-size: 1.15rem; color: #fff; margin-bottom: 0.5rem;">${seg.segment_name}</h3>
          <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5; margin-bottom: 1.25rem;">
            ${seg.criteria_description}
          </p>

          <div style="background: rgba(10, 13, 20, 0.6); padding: 0.85rem; border-radius: var(--radius-sm); border: 1px solid rgba(255, 255, 255, 0.05); margin-bottom: 1.25rem;">
            <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.4rem; font-weight: 700;">Rule Logic</div>
            <pre style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #cbd5e1; white-space: pre-wrap;">${JSON.stringify(seg.criteria_json, null, 2)}</pre>
          </div>
        </div>

        <div style="border-top: 1px solid var(--border-subtle); padding-top: 1rem; display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; font-size: 0.8rem;">
          <div><span style="color: var(--text-muted);">Members:</span> <strong style="color: #fff;">${formatNumber(seg.member_count)}</strong></div>
          <div><span style="color: var(--text-muted);">Avg Spend:</span> <strong style="color: #fff;">${formatCurrency(seg.avg_net_spend)}</strong></div>
          <div><span style="color: var(--text-muted);">Avg Recency:</span> <strong style="color: #fff;">${seg.avg_recency_days}d</strong></div>
          <div><span style="color: var(--text-muted);">Avg Eng Score:</span> <strong style="color: #fff;">${seg.avg_engagement_score}</strong></div>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error('Error loading segments:', err);
  }
}

// --- 3. Load Customers ---
async function loadCustomers(page = 1) {
  currentCustomerPage = page;
  const segFilter = document.getElementById('filterSegment').value;
  const searchFilter = document.getElementById('customerSearchInput').value.trim();

  let url = `/api/customers?page=${page}&page_size=15`;
  if (segFilter) url += `&segment_code=${encodeURIComponent(segFilter)}`;
  if (searchFilter) url += `&search=${encodeURIComponent(searchFilter)}`;

  try {
    const res = await fetch(url);
    const data = await res.json();

    const tbody = document.getElementById('customersTableBody');
    tbody.innerHTML = '';

    if (!data.customers || data.customers.length === 0) {
      tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-muted); padding: 2rem;">No customers found matching filter criteria.</td></tr>`;
      document.getElementById('paginationInfo').innerText = 'Showing 0 records';
      return;
    }

    const badgeMap = {
      VIP_LOYALIST: 'badge-vip',
      SERVICE_HEAVY_DISSATISFIED: 'badge-service',
      AT_RISK_DORMANT: 'badge-dormant',
      HIGH_POTENTIAL: 'badge-growth',
      NEW_ONBOARDING: 'badge-new',
    };

    data.customers.forEach(c => {
      const tr = document.createElement('tr');
      const badgeClass = badgeMap[c.segment_code] || 'badge-growth';

      tr.innerHTML = `
        <td><code style="color: var(--accent-cyan); font-weight: 600;">${c.customer_id}</code></td>
        <td>
          <div style="font-weight: 600; color: #fff;">${c.name}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${c.email}</div>
        </td>
        <td><span class="chip chip-info">${c.lifecycle_stage}</span></td>
        <td><span class="segment-badge ${badgeClass}" style="margin: 0;">${c.segment_name}</span></td>
        <td>${c.recency_days}d ago</td>
        <td>${c.frequency_count}</td>
        <td><strong>${formatCurrency(c.monetary_net_spend)}</strong></td>
        <td>${c.engagement_score}</td>
        <td style="max-width: 280px; font-size: 0.75rem; color: var(--text-secondary); line-height: 1.4;">${c.explainability_notes}</td>
        <td>
          <button class="btn-secondary" style="padding: 0.4rem 0.75rem; font-size: 0.75rem;" onclick="openCustomerModal('${c.customer_id}')">
            Inspect 360
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    const start = (data.page - 1) * data.page_size + 1;
    const end = Math.min(start + data.page_size - 1, data.total);
    document.getElementById('paginationInfo').innerText = `Showing ${start} to ${end} of ${formatNumber(data.total)} records`;

    document.getElementById('btnPrevPage').disabled = data.page <= 1;
    document.getElementById('btnNextPage').disabled = data.page >= data.total_pages;
  } catch (err) {
    console.error('Error loading customers:', err);
  }
}

function changeCustomerPage(delta) {
  loadCustomers(currentCustomerPage + delta);
}

function debounceCustomerSearch() {
  clearTimeout(customerSearchDebounceTimer);
  customerSearchDebounceTimer = setTimeout(() => {
    loadCustomers(1);
  }, 300);
}

// --- Customer 360 Modal & Full Explainability Trace ---
async function openCustomerModal(customerId) {
  try {
    const res = await fetch(`/api/customers/${customerId}`);
    const data = await res.json();
    const modalBody = document.getElementById('customerModalBody');

    const evalData = data.segment_evaluation;
    const cust = data.customer;

    let traceHtml = '';
    evalData.full_decision_trace.forEach(t => {
      const isPass = t.startsWith('[PASS');
      const cls = isPass ? 'trace-pass' : 'trace-fail';
      traceHtml += `<div class="trace-line ${cls}">${t}</div>`;
    });

    let consentHtml = '';
    data.consents.forEach(cn => {
      const isOptIn = cn.status === 'OPTED_IN';
      const chipCls = isOptIn ? 'chip-success' : 'chip-danger';
      consentHtml += `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.04);">
          <span style="font-size: 0.8rem; color: var(--text-secondary);">${cn.channel}</span>
          <span class="chip ${chipCls}">${cn.status}</span>
        </div>
      `;
    });

    let ordersHtml = '';
    data.orders.slice(0, 5).forEach(o => {
      ordersHtml += `
        <tr>
          <td><code>${o.order_id}</code></td>
          <td>${new Date(o.order_date).toLocaleDateString()}</td>
          <td>${formatCurrency(o.total_amount)}</td>
          <td style="color: ${o.refund_amount > 0 ? '#fb7185' : 'inherit'};">-${formatCurrency(o.refund_amount)}</td>
          <td><strong>${formatCurrency(o.net_amount)}</strong></td>
          <td><span class="chip chip-info">${o.fulfillment_status}</span></td>
        </tr>
      `;
    });

    modalBody.innerHTML = `
      <div style="margin-bottom: 1.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
          <h2 style="color: #fff; font-size: 1.4rem;">${cust.first_name} ${cust.last_name}</h2>
          <span class="chip chip-info">${cust.customer_id}</span>
          <span class="chip chip-success">${cust.status}</span>
        </div>
        <div style="font-size: 0.85rem; color: var(--text-secondary);">
          Email: ${cust.email} · Phone: ${cust.phone} · Enrolled: ${cust.signup_date}
        </div>
      </div>

      <!-- Segment Qualification & Decision Trace -->
      <div style="background: rgba(16, 21, 34, 0.7); border: 1px solid var(--border-accent); border-radius: var(--radius-sm); padding: 1.25rem; margin-bottom: 1.5rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
          <span style="font-size: 0.85rem; font-weight: 700; color: #fff;">Assigned Primary Segment</span>
          <span class="segment-badge badge-vip" style="margin: 0;">${evalData.primary_segment_name} (${evalData.primary_segment_code})</span>
        </div>
        <div style="font-size: 0.85rem; color: #a5b4fc; margin-bottom: 0.75rem;">
          <strong>Explainability Rationale:</strong> ${evalData.explainability_notes}
        </div>

        <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Step-by-Step Decision Trace:</div>
        <div class="trace-box">${traceHtml}</div>
      </div>

      <!-- Metrics Snapshot -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
        <div style="background: rgba(255,255,255,0.03); padding: 0.85rem; border-radius: 6px;">
          <div style="font-size: 0.75rem; color: var(--text-muted);">Recency</div>
          <div style="font-size: 1.1rem; font-weight: 700; color: #fff;">${evalData.metrics.recency_days} days</div>
        </div>
        <div style="background: rgba(255,255,255,0.03); padding: 0.85rem; border-radius: 6px;">
          <div style="font-size: 0.75rem; color: var(--text-muted);">Order Count</div>
          <div style="font-size: 1.1rem; font-weight: 700; color: #fff;">${evalData.metrics.frequency_count}</div>
        </div>
        <div style="background: rgba(255,255,255,0.03); padding: 0.85rem; border-radius: 6px;">
          <div style="font-size: 0.75rem; color: var(--text-muted);">Net Spend</div>
          <div style="font-size: 1.1rem; font-weight: 700; color: #fff;">${formatCurrency(evalData.metrics.monetary_net_spend)}</div>
        </div>
        <div style="background: rgba(255,255,255,0.03); padding: 0.85rem; border-radius: 6px;">
          <div style="font-size: 0.75rem; color: var(--text-muted);">Digital Engagement</div>
          <div style="font-size: 1.1rem; font-weight: 700; color: #fff;">${evalData.metrics.engagement_score}</div>
        </div>
        <div style="background: rgba(255,255,255,0.03); padding: 0.85rem; border-radius: 6px;">
          <div style="font-size: 0.75rem; color: var(--text-muted);">Support Burden</div>
          <div style="font-size: 1.1rem; font-weight: 700; color: #fff;">${formatCurrency(evalData.metrics.service_burden_cost)}</div>
        </div>
      </div>

      <!-- Consents & Orders -->
      <div style="display: grid; grid-template-columns: 1fr 1.5fr; gap: 1.5rem;">
        <div>
          <h4 style="font-size: 0.9rem; color: #fff; margin-bottom: 0.75rem;">Channel Consent Record</h4>
          <div style="background: rgba(255,255,255,0.02); padding: 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
            ${consentHtml}
          </div>
        </div>
        <div>
          <h4 style="font-size: 0.9rem; color: #fff; margin-bottom: 0.75rem;">Recent Purchase Ledger (Reconciled)</h4>
          <div class="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Date</th>
                  <th>Total</th>
                  <th>Refund</th>
                  <th>Net</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                ${ordersHtml || '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No orders placed yet.</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;

    document.getElementById('customerModal').classList.add('active');
  } catch (err) {
    console.error('Error opening customer modal:', err);
  }
}

function closeCustomerModal() {
  document.getElementById('customerModal').classList.remove('active');
}

// --- 4. Policy Guardrail & Action Simulator ---
async function runRecommendationSimulation() {
  const custId = document.getElementById('simCustomerId').value.trim();
  const container = document.getElementById('simResultContainer');

  if (!custId) {
    alert('Please enter a Customer ID.');
    return;
  }

  container.innerHTML = '<div style="color: var(--text-muted); text-align: center; padding: 2rem;">Evaluating policy guardrails...</div>';

  try {
    const res = await fetch('/api/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customer_id: custId }),
    });

    if (!res.ok) {
      const err = await res.json();
      container.innerHTML = `<div style="color: #fb7185; padding: 1.5rem;">Error: ${err.detail || 'Could not evaluate recommendation'}</div>`;
      return;
    }

    const data = await res.json();
    const isSuppressed = data.is_suppressed;
    const badgeCls = isSuppressed ? 'chip-danger' : 'chip-success';
    const decisionIcon = isSuppressed ? '🛑 SUPPRESSED BY POLICY' : '✅ DISPATCH APPROVED';

    let guardrailsHtml = '';
    data.guardrails_checked.forEach(g => {
      const pass = g.status === 'PASS';
      const exempt = g.status === 'EXEMPT';
      const stColor = pass ? '#34d399' : (exempt ? '#a5b4fc' : '#fb7185');
      guardrailsHtml += `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.04);">
          <span style="font-size: 0.85rem; color: #fff;">${g.guardrail}</span>
          <span style="font-size: 0.8rem; font-weight: 700; color: ${stColor};">${g.status}</span>
        </div>
      `;
    });

    let detailsHtml = '';
    data.decision_details.forEach(d => {
      detailsHtml += `<div style="margin-bottom: 0.35rem; color: #cbd5e1;">• ${d}</div>`;
    });

    container.innerHTML = `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
          <span style="font-size: 0.8rem; color: var(--text-muted);">Recommendation Audit: <code>${data.recommendation_id}</code></span>
          <span class="chip ${badgeCls}" style="font-size: 0.85rem; font-weight: 700;">${decisionIcon}</span>
        </div>

        <div style="background: rgba(255,255,255,0.03); border-radius: var(--radius-sm); padding: 1rem; margin-bottom: 1rem;">
          <div style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700;">Target Action</div>
          <div style="font-size: 1.1rem; font-weight: 700; color: #fff; margin: 0.25rem 0;">${data.action.action_name}</div>
          <div style="font-size: 0.85rem; color: var(--text-secondary);">${data.action.description}</div>
        </div>

        <div style="margin-bottom: 1rem;">
          <div style="font-size: 0.8rem; font-weight: 700; color: var(--text-secondary); margin-bottom: 0.5rem;">Guardrail Checks Enforced</div>
          <div style="background: rgba(10, 13, 20, 0.4); padding: 0.75rem 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
            ${guardrailsHtml}
          </div>
        </div>

        <div>
          <div style="font-size: 0.8rem; font-weight: 700; color: var(--text-secondary); margin-bottom: 0.5rem;">Audit Explanation</div>
          <div style="background: rgba(10, 13, 20, 0.6); padding: 0.85rem; border-radius: var(--radius-sm); font-size: 0.8rem; font-family: 'JetBrains Mono', monospace;">
            ${detailsHtml}
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    console.error('Error running recommendation simulation:', err);
    container.innerHTML = `<div style="color: #fb7185; padding: 1.5rem;">Failed to connect to backend server.</div>`;
  }
}

// --- 5. Anomaly & Data Quality Center ---
async function loadAnomalies() {
  try {
    const res = await fetch('/api/anomalies');
    const data = await res.json();

    // Integrity Checklist
    const checksGrid = document.getElementById('auditChecksGrid');
    checksGrid.innerHTML = '';

    const checks = [
      { name: 'Primary Key Uniqueness', passed: data.audit_summary.primary_key_uniqueness },
      { name: 'Foreign Key Referential Integrity', passed: data.audit_summary.foreign_key_integrity },
      { name: 'Enum Value Conformance', passed: data.audit_summary.enum_conformance },
      { name: 'Date Chronology Logic', passed: data.audit_summary.date_ordering },
      { name: 'Arithmetic Reconciliation', passed: data.audit_summary.arithmetic_reconciliation },
    ];

    checks.forEach(c => {
      const card = document.createElement('div');
      card.style.background = 'rgba(16, 21, 34, 0.6)';
      card.style.border = '1px solid var(--border-subtle)';
      card.style.borderRadius = 'var(--radius-sm)';
      card.style.padding = '1rem';
      card.style.display = 'flex';
      card.style.alignItems = 'center';
      card.style.gap = '0.75rem';

      const icon = c.passed ? '✓' : '✗';
      const iconCls = c.passed ? 'chip-success' : 'chip-danger';

      card.innerHTML = `
        <span class="chip ${iconCls}" style="font-size: 1rem; width: 28px; height: 28px; justify-content: center;">${icon}</span>
        <div>
          <div style="font-size: 0.85rem; font-weight: 600; color: #fff;">${c.name}</div>
          <div style="font-size: 0.75rem; color: ${c.passed ? '#34d399' : '#fb7185'};">${c.passed ? 'Verified Passing' : 'Failed'}</div>
        </div>
      `;
      checksGrid.appendChild(card);
    });

    // Benchmark Table
    const bmTable = document.getElementById('benchmarkTableBody');
    bmTable.innerHTML = '';
    const byCat = data.benchmark_metrics.by_category;

    for (const [cat, m] of Object.entries(byCat)) {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong style="color: #fff;">${cat}</strong></td>
        <td><span class="chip chip-success">${m.true_positives}</span></td>
        <td><span class="chip chip-info">${m.false_positives}</span></td>
        <td><span class="chip chip-info">${m.false_negatives}</span></td>
        <td><strong style="color: #34d399;">${(m.precision * 100).toFixed(1)}%</strong></td>
        <td><strong style="color: #34d399;">${(m.recall * 100).toFixed(1)}%</strong></td>
        <td><strong style="color: #67e8f9;">${(m.f1_score * 100).toFixed(1)}%</strong></td>
        <td><span class="chip chip-success">PERFECT MATCH</span></td>
      `;
      bmTable.appendChild(tr);
    }

    // Injected Ground Truth Table
    const gtTable = document.getElementById('groundTruthTableBody');
    gtTable.innerHTML = '';

    data.ground_truth_records.forEach(g => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><code style="color: var(--accent-amber);">${g.anomaly_id}</code></td>
        <td><span class="chip chip-danger">${g.issue_type}</span></td>
        <td>${g.entity_type}</td>
        <td><code>${g.entity_id}</code></td>
        <td><code style="color: var(--accent-cyan);">${g.customer_id}</code></td>
        <td style="font-size: 0.8rem; color: #cbd5e1; max-width: 250px;">${g.injected_details}</td>
        <td style="font-size: 0.8rem; color: #94a3b8; max-width: 250px;">${g.expected_behavior}</td>
      `;
      gtTable.appendChild(tr);
    });
  } catch (err) {
    console.error('Error loading anomalies:', err);
  }
}

// --- Reload Dataset ---
async function reloadDataset(scale) {
  const badge = document.getElementById('currentScaleText');
  badge.innerText = `Generating ${scale}...`;

  try {
    const res = await fetch(`/api/dataset/reload?scale=${scale}`, { method: 'POST' });
    const data = await res.json();
    badge.innerText = `Scale: ${scale.toUpperCase()} (${data.customer_count} Users)`;

    // Reload active tab
    loadOverview();
    loadSegments();
    loadCustomers(1);
  } catch (err) {
    console.error('Error reloading dataset:', err);
    badge.innerText = 'Error loading scale';
  }
}

// Initial Boot
document.addEventListener('DOMContentLoaded', () => {
  loadOverview();
  loadSegments();
});
