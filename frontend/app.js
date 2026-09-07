let defectsData = [];
let corridorsData = [];

document.addEventListener("DOMContentLoaded", () => {
    renderNavBar();
    initPageContent();
});

function renderNavBar() {
    const navContainer = document.getElementById("top-nav");
    if (!navContainer) return;

    const pathname = window.location.pathname;
    
    const navItems = [
        { path: "/overview", altPaths: ["/", "/overview.html"], label: "📊 Overview" },
        { path: "/defects", altPaths: ["/defects.html"], label: "🚨 Defects & Health" },
        { path: "/schedule", altPaths: ["/schedule.html"], label: "📅 Schedule" },
        { path: "/whatif", altPaths: ["/whatif.html"], label: "🧪 What-If Simulator" }
    ];

    const linksHtml = navItems.map(item => {
        const isActive = (pathname === item.path) || 
                         (item.altPaths && item.altPaths.includes(pathname)) ||
                         (pathname === "/" && item.path === "/overview");
        const activeClass = isActive ? "active" : "";
        return `<a href="${item.path}" class="nav-link ${activeClass}">${item.label}</a>`;
    }).join("");

    navContainer.className = "nav-bar";
    navContainer.innerHTML = linksHtml;
}

async function initPageContent() {
    // Overview page stats
    if (document.getElementById("stat-total-defects")) {
        await Promise.all([fetchDefects(), fetchCorridors()]);
    }
    // Defects page table
    else if (document.getElementById("defects-tbody")) {
        await fetchDefects();
    }
    // Schedule page table
    if (document.getElementById("schedule-tbody")) {
        await fetchExistingSchedule();
    }
    // What-if simulator dropdown
    if (document.getElementById("sim-task-select")) {
        if (defectsData.length === 0) {
            await fetchDefects();
        } else {
            populateWhatIfDropdown(defectsData);
        }
    }
}

async function fetchCorridors() {
    try {
        const res = await fetch("/api/corridors");
        if (res.ok) {
            corridorsData = await res.json();
            const corElem = document.getElementById("stat-corridors");
            if (corElem) corElem.innerText = corridorsData.length;
        }
    } catch (err) {
        console.error("Error fetching corridors:", err);
    }
}

async function fetchDefects() {
    try {
        const res = await fetch("/api/defects");
        if (!res.ok) throw new Error("Failed to fetch defects");
        
        defectsData = await res.json();
        
        if (document.getElementById("defects-tbody")) {
            renderDefectsTable(defectsData);
        }
        if (document.getElementById("stat-total-defects")) {
            updateStats(defectsData);
        }
        if (document.getElementById("sim-task-select")) {
            populateWhatIfDropdown(defectsData);
        }
    } catch (err) {
        console.error("Error fetching defects:", err);
        const tbody = document.getElementById("defects-tbody");
        if (tbody) {
            tbody.innerHTML = `
                <tr><td colspan="8" class="empty-text" style="color: #f87171;">Failed to load defects. Check backend connection.</td></tr>
            `;
        }
    }
}

function renderDefectsTable(defects) {
    const tbody = document.getElementById("defects-tbody");
    const countElem = document.getElementById("defects-count");
    if (countElem) countElem.innerText = `${defects.length} Total Defects`;

    if (!tbody) return;

    if (!defects || defects.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="empty-text">No defects reported in database.</td></tr>`;
        return;
    }

    tbody.innerHTML = defects.map(d => {
        const pScore = parseFloat(d.priority_score || 0);
        const hScore = parseFloat(d.health_score || 0);

        let pBadgeClass = "badge-success";
        if (pScore > 7) pBadgeClass = "badge-danger";
        else if (pScore >= 4) pBadgeClass = "badge-warning";

        let hHealthClass = "health-good";
        if (hScore < 40) hHealthClass = "health-poor";
        else if (hScore <= 70) hHealthClass = "health-mid";

        const locationText = d.location_marker ? escapeHtml(d.location_marker) : "N/A";

        return `
            <tr>
                <td><strong>TASK-${d.task_id}</strong></td>
                <td>${escapeHtml(d.defect_type || "N/A")}</td>
                <td><code>${escapeHtml(d.corridor_id || "N/A")}</code></td>
                <td><span style="font-size: 0.85rem; color: #a78bfa;">${locationText}</span></td>
                <td>${escapeHtml(d.department || "N/A")}</td>
                <td><span style="font-weight: 600;">L${d.severity}</span></td>
                <td><span class="badge ${pBadgeClass}">${pScore.toFixed(2)}</span></td>
                <td><span class="${hHealthClass}">${hScore.toFixed(1)}</span></td>
            </tr>
        `;
    }).join("");
}

function updateStats(defects) {
    const totalElem = document.getElementById("stat-total-defects");
    const critElem = document.getElementById("stat-high-priority");
    const healthElem = document.getElementById("stat-avg-health");

    if (totalElem) totalElem.innerText = defects.length;
    if (critElem) {
        const criticalCount = defects.filter(d => (parseFloat(d.priority_score) > 7)).length;
        critElem.innerText = criticalCount;
    }
    if (healthElem && defects.length > 0) {
        const avgHealth = defects.reduce((acc, curr) => acc + parseFloat(curr.health_score || 0), 0) / defects.length;
        healthElem.innerText = avgHealth.toFixed(1);
    }
}

function populateWhatIfDropdown(defects) {
    const select = document.getElementById("sim-task-select");
    if (!select) return;

    select.innerHTML = '<option value="">Select a defect task...</option>';
    
    defects.forEach(d => {
        const opt = document.createElement("option");
        opt.value = d.task_id;
        const loc = d.location_marker ? ` [${d.location_marker}]` : "";
        opt.textContent = `TASK-${d.task_id}: ${d.defect_type} (${d.corridor_id})${loc}`;
        select.appendChild(opt);
    });
}

function onTaskSelectChange() {
    const select = document.getElementById("sim-task-select");
    if (!select) return;
    const taskId = select.value;
    if (!taskId) return;

    const selectedDefect = defectsData.find(d => String(d.task_id) === String(taskId));
    if (selectedDefect) {
        const sev = selectedDefect.severity || 3;
        const dur = selectedDefect.estimated_block_duration || 3.0;

        const sevElem = document.getElementById("sim-severity");
        const sevValElem = document.getElementById("severity-val");
        const durElem = document.getElementById("sim-duration");

        if (sevElem) sevElem.value = sev;
        if (sevValElem) sevValElem.innerText = sev;
        if (durElem) durElem.value = dur;
    }
}

async function fetchExistingSchedule() {
    try {
        const res = await fetch("/api/schedule");
        if (res.ok) {
            const schedule = await res.json();
            if (schedule && schedule.length > 0) {
                renderScheduleTable(schedule);
            }
        }
    } catch (err) {
        console.error("Error fetching existing schedule:", err);
    }
}

async function generateSchedule() {
    const btn = document.getElementById("btn-generate-schedule");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<div class="spinner"></div><span>Generating...</span>`;
    }

    try {
        const res = await fetch("/api/schedule/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });

        if (!res.ok) throw new Error("Schedule generation failed");
        const data = await res.json();

        if (data.schedule) {
            renderScheduleTable(data.schedule);
        }
    } catch (err) {
        console.error("Error generating schedule:", err);
        alert("Failed to generate schedule. Check backend logs.");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<span>⚡ Generate Schedule</span>`;
        }
    }
}

function renderScheduleTable(schedule) {
    const tbody = document.getElementById("schedule-tbody");
    const countElem = document.getElementById("schedule-count");
    if (countElem) countElem.innerText = `${schedule.length} Committed Items`;

    if (!tbody) return;

    if (!schedule || schedule.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="empty-text">No schedule items generated.</td></tr>`;
        return;
    }

    tbody.innerHTML = schedule.map(s => {
        const pScore = parseFloat(s.priority_score || 0);
        let pBadgeClass = "badge-success";
        if (pScore > 7) pBadgeClass = "badge-danger";
        else if (pScore >= 4) pBadgeClass = "badge-warning";

        const mergedText = s.merged_with ? `<span class="badge badge-warning">${escapeHtml(s.merged_with)}</span>` : "—";
        const windowText = `${escapeHtml(s.slot_start || "")} - ${escapeHtml(s.slot_end || "")}`;

        return `
            <tr>
                <td><strong>TASK-${s.task_id}</strong></td>
                <td><code>${escapeHtml(s.corridor_id || "N/A")}</code></td>
                <td>${escapeHtml(s.date || "N/A")}</td>
                <td><strong>${windowText}</strong></td>
                <td><span class="badge ${pBadgeClass}">${pScore.toFixed(2)}</span></td>
                <td>${mergedText}</td>
                <td style="font-size: 0.85rem; color: #d1d5db;">${escapeHtml(s.explanation_text || "")}</td>
            </tr>
        `;
    }).join("");
}

async function runWhatIf() {
    const select = document.getElementById("sim-task-select");
    if (!select || !select.value) {
        alert("Please select a task to simulate.");
        return;
    }
    const taskId = select.value;
    const severity = parseInt(document.getElementById("sim-severity").value);
    const duration = parseFloat(document.getElementById("sim-duration").value);

    const btn = document.getElementById("btn-run-whatif");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<div class="spinner"></div><span>Simulating...</span>`;
    }

    try {
        const payload = {
            override_defect: {
                task_id: parseInt(taskId),
                severity: severity,
                estimated_block_duration: duration
            }
        };

        const res = await fetch("/api/whatif", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error("What-if simulation failed");
        const data = await res.json();

        if (data.schedule) {
            const simItem = data.schedule.find(item => String(item.task_id) === String(taskId));
            if (simItem) {
                displayWhatIfResult(simItem);
            } else {
                alert("Task not found in simulation output.");
            }
        }
    } catch (err) {
        console.error("Error running what-if:", err);
        alert("Error running simulation.");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<span>🧪 Run What-If Simulation</span>`;
        }
    }
}

function displayWhatIfResult(simItem) {
    const container = document.getElementById("sim-result-container");
    if (!container) return;
    container.style.display = "block";

    document.getElementById("sim-res-taskid").innerText = `TASK-${simItem.task_id}`;
    document.getElementById("sim-res-date").innerText = simItem.date || "N/A";
    document.getElementById("sim-res-slot").innerText = `${simItem.slot_start} - ${simItem.slot_end}`;
    document.getElementById("sim-res-priority").innerText = parseFloat(simItem.priority_score || 0).toFixed(2);
    document.getElementById("sim-res-corridor").innerText = simItem.corridor_id || "N/A";
    document.getElementById("sim-res-explanation").innerText = simItem.explanation_text || "No notes.";
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
