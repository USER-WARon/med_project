const ui = {
    switchView(viewId) {
        document.querySelectorAll('.view').forEach(el => el.style.display = 'none');
        document.getElementById(`view-${viewId}`).style.display = 'block';
        
        document.querySelectorAll('nav button').forEach(btn => btn.classList.remove('active'));
        document.getElementById(`nav-${viewId}`).classList.add('active');
    },

    renderPatient(patient) {
        const grid = document.getElementById('patient-grid');
        const card = document.createElement('div');
        card.className = 'patient-card';
        card.id = `patient-${patient.id}`;
        
        const color = patient.category === "Critical" ? "var(--critical)" : 
                      patient.category === "Moderate" ? "var(--moderate)" : "var(--normal)";

        card.innerHTML = `
    <h3>${patient.name} <span style="font-size: 12px; color: gray;">Age ${patient.age}</span></h3>

    <div class="score-badge" style="background: ${color}22; color: ${color}; border: 1px solid ${color}">
        Risk: ${patient.score} / 100 (${patient.category})
    </div>

    <p style="font-size: 13px; margin-top: 10px;">
        Trend: <b>${patient.trend || "N/A"}</b> ${patient.trend === "increasing" ? "📈" : patient.trend === "decreasing" ? "📉" : ""}
    </p>

    <p style="font-size: 13px;">
        Monitoring: ${patient.monitoring ? "⏱️ Active" : "❌ Off"}
    </p>

    <p style="font-size: 13px; color: #ff6b6b;">
        ${patient.ruleAlerts?.join("<br>") || ""}
    </p>

    <p style="font-size: 12px; color: gray; margin-top: 15px;">
        Assessed: ${new Date(patient.timestamp).toLocaleTimeString()}
    </p>
`;
        
        grid.prepend(card);
    },

    setStatus(text, color) {
        const el = document.getElementById('upload-status');
        el.innerText = text;
        el.style.color = color;
    },
    renderExtractionPreview(data) {
        const container = document.getElementById('extraction-preview');
        
        if (!data) {
            container.style.display = 'none';
            return;
        }

        // Helper to format missing values in red
        const formatVal = (val) => val !== null ? 
            `<span style="font-weight: bold; font-family: monospace;">${val}</span>` : 
            `<span style="color: #ff6b6b; font-size: 12px; font-weight: bold;">Missing</span>`;

        // Generate list items for CBC dynamically
        const cbcHtml = Object.entries(data.cbc).map(([key, val]) => `
            <li style="display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding: 4px 0;">
                <span style="text-transform: capitalize; color: #555;">${key}</span>
                ${formatVal(val)}
            </li>
        `).join('');

        // Generate list items for CMP dynamically
        const cmpHtml = Object.entries(data.cmp).map(([key, val]) => `
            <li style="display: flex; justify-content: space-between; border-bottom: 1px solid #eee; padding: 4px 0;">
                <span style="text-transform: capitalize; color: #555;">${key}</span>
                ${formatVal(val)}
            </li>
        `).join('');

        // Inject the HTML into the container
        container.innerHTML = `
            <div style="background: white; border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin-top: 20px;">
                <h3 style="margin-top: 0; border-bottom: 2px solid #eee; padding-bottom: 10px;">🔍 Extracted Data Preview</h3>
                
                <div style="display: flex; justify-content: space-between; background: #f8f9fa; padding: 15px; border-radius: 6px; margin-bottom: 20px;">
                    <div><span style="font-size: 12px; color: gray;">Patient ID</span><br><b>${data.patientId || 'Not Found'}</b></div>
                    <div><span style="font-size: 12px; color: gray;">Name</span><br><b>${data.patientName || 'Unknown'}</b></div>
                    <div><span style="font-size: 12px; color: gray;">Age</span><br><b>${data.patientAge || 'Unknown'}</b></div>
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
                
                <button id="btn-calculate-risk" style="width: 100%; margin-top: 20px; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">
                    Process & Calculate Risk 🚀
                </button>
            </div>
        `;

        container.style.display = 'block';
    }
};
