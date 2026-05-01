// ui.js

const ui = {
    // 1. Navigation View Switcher
    switchView(viewId) {
        // Hide all views
        document.querySelectorAll('.view').forEach(el => el.style.display = 'none');
        // Show target view
        document.getElementById(`view-${viewId}`).style.display = 'block';
        
        // Update active state on nav buttons
        document.querySelectorAll('nav button').forEach(btn => btn.classList.remove('active'));
        const activeNav = document.getElementById(`nav-${viewId}`);
        if(activeNav) activeNav.classList.add('active');
    },

    // 2. Update File Upload Status Text
    setStatus(text, color = "var(--text-main)") {
        const el = document.getElementById('upload-status');
        el.innerText = text;
        el.style.color = color;
    },

    // 3. Render Extracted Data Preview Box
    renderExtractionPreview(data) {
        const container = document.getElementById('extraction-preview');
        
        if (!data) {
            container.style.display = 'none';
            return;
        }

        const formatVal = (val) => val !== null ? 
            `<span style="font-weight: bold; font-family: monospace;">${val}</span>` : 
            `<span style="color: #ff6b6b; font-size: 12px; font-weight: bold;">Missing</span>`;

        const cbcHtml = Object.entries(data.cbc || {}).map(([key, val]) => `
            <li style="display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding: 4px 0;">
                <span style="text-transform: capitalize; color: #555;">${key}</span>
                ${formatVal(val)}
            </li>
        `).join('');

        const cmpHtml = Object.entries(data.cmp || {}).map(([key, val]) => `
            <li style="display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding: 4px 0;">
                <span style="text-transform: capitalize; color: #555;">${key}</span>
                ${formatVal(val)}
            </li>
        `).join('');

        container.innerHTML = `
            <div style="background: white; border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin-top: 20px;">
                <h3 style="margin-top: 0; border-bottom: 2px solid #eee; padding-bottom: 10px; color: #333;">🔍 Extracted Data Preview</h3>
                
                <div style="display: flex; justify-content: space-between; background: #f8f9fa; padding: 15px; border-radius: 6px; margin-bottom: 20px;">
                    <div><span style="font-size: 12px; color: gray;">Patient ID</span><br><b style="color: #333;">${data.patientId || 'Not Found'}</b></div>
                    <div><span style="font-size: 12px; color: gray;">Name</span><br><b style="color: #333;">${data.patientName || 'Unknown'}</b></div>
                    <div><span style="font-size: 12px; color: gray;">Age</span><br><b style="color: #333;">${data.patientAge || 'Unknown'}</b></div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <h4 style="color: #2b8a3e; margin-bottom: 10px;">CBC (Blood Count)</h4>
                        <ul style="list-style: none; padding: 0; margin: 0;">${cbcHtml}</ul>
                    </div>
                    <div>
                        <h4 style="color: #1864ab; margin-bottom: 10px;">CMP (Metabolic Panel)</h4>
                        <ul style="list-style: none; padding: 0; margin: 0;">${cmpHtml}</ul>
                    </div>
                </div>
            </div>
        `;

        container.style.display = 'block';
    },

    // 4. Render Senior ICU Dashboard Cards (Critical & Moderate)
    renderSeniorCases(cases) {
        const grid = document.getElementById('patient-grid');
        grid.innerHTML = ''; 

        if (!cases || cases.length === 0) {
            grid.innerHTML = `<p style="color: gray; text-align: center; width: 100%;">No critical or moderate cases currently assigned.</p>`;
            return;
        }

        cases.forEach(patient => {
            const card = document.createElement('div');
            card.className = 'patient-card';
            card.style.background = "var(--box-bg, #111827)";
            card.style.padding = "20px";
            card.style.borderRadius = "8px";
            card.style.border = "1px solid #333";
            card.style.marginBottom = "15px";
            
            const color = patient.category === "Critical" ? "#EF4444" : "#F59E0B";

            const dateObj = new Date(patient.time);
            const timeStr = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            card.innerHTML = `
                <h3 style="margin-top:0;">${patient.name} <span style="font-size: 12px; color: gray;">Age ${patient.age || 'N/A'}</span></h3>
                <div style="background: ${color}22; color: ${color}; border: 1px solid ${color}; padding: 6px 12px; border-radius: 4px; display: inline-block; font-weight: bold; font-size: 14px;">
                    Risk: ${patient.score} / 100 (${patient.category})
                </div>
                <p style="font-size: 12px; color: gray; margin-top: 15px; font-family: monospace;">
                    ID: ${patient.patient_id.substring(0, 8).toUpperCase()}
                </p>
                <p style="font-size: 12px; color: gray; margin-top: 5px;">
                    Assessed: ${timeStr}
                </p>
                <button style="background: transparent; cursor: pointer; width: 100%; margin-top: 15px; padding: 8px; border: 1px solid ${color}; color: ${color}; border-radius: 4px;" onclick="alert('Opening full file for ${patient.name}')">View Full Report</button>
            `;
            
            grid.appendChild(card);
        });
    },

    // 5. Render Intern Dashboard Table (Normal Risk)
    renderInternCases(cases) {
        const tbody = document.getElementById('intern-table-body');
        tbody.innerHTML = ''; 

        if (!cases || cases.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 40px; color: gray;">🎉 Queue is clear! No normal cases assigned.</td></tr>`;
            return;
        }

        cases.forEach(patient => {
            const tr = document.createElement('tr');
            tr.style.borderBottom = "1px solid #333";
            tr.innerHTML = `
                <td style="padding: 15px; font-family: monospace; color: gray;">${patient.patient_id.substring(0, 8).toUpperCase()}</td>
                <td style="padding: 15px; font-weight: bold;">${patient.name}</td>
                <td style="padding: 15px;">${patient.age || 'N/A'}</td>
                <td style="padding: 15px; color: #10B981; font-weight: bold;">Score: ${patient.score}</td>
                <td style="padding: 15px;"><button style="background: transparent; border: 1px solid #10B981; color: #10B981; padding: 6px 12px; border-radius: 4px; cursor: pointer;" onclick="alert('Reviewing file for ${patient.name}')">Review</button></td>
            `;
            tbody.appendChild(tr);
        });
    }
};