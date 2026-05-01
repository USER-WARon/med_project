// main.js

let patients = []; // Central state

// main.js

// Utility function to handle empty inputs cleanly
function val(id) {
    const v = document.getElementById(id).value;
    return v === "" ? null : v;
}

// Data Fetchers for the Dashboards
async function loadInternData() {
    document.getElementById('intern-table-body').innerHTML = '<tr><td colspan="5" style="text-align:center; padding:30px;">Loading cases...</td></tr>';
    const data = await api.getInternCases();
    if (data && data.cases) {
        ui.renderInternCases(data.cases);
    } else {
        document.getElementById('intern-table-body').innerHTML = '<tr><td colspan="5" style="color:#EF4444; text-align:center; padding:30px;">Failed to load cases.</td></tr>';
    }
}

async function loadSeniorData() {
    document.getElementById('patient-grid').innerHTML = '<p style="text-align:center; color:gray; width:100%;">Loading ICU cases...</p>';
    const data = await api.getSeniorCases();
    if (data && data.cases) {
        ui.renderSeniorCases(data.cases);
    } else {
        document.getElementById('patient-grid').innerHTML = '<p style="color:#EF4444; text-align:center; width:100%;">Failed to load cases.</p>';
    }
}

document.addEventListener("DOMContentLoaded", () => {
    
    // --- Navigation Listeners ---
    document.getElementById('nav-admit').addEventListener('click', () => {
        ui.switchView('admit');
    });

    document.getElementById('nav-dashboard').addEventListener('click', async () => {
        ui.switchView('dashboard');
        await loadSeniorData(); // Fetch fresh DB data
    });
    
    document.getElementById('nav-intern')?.addEventListener('click', async () => {
        ui.switchView('intern');
        await loadInternData(); // Fetch fresh DB data
    });

    // --- Dashboard Refresh Buttons ---
    document.getElementById('btn-refresh-senior')?.addEventListener('click', loadSeniorData);
    document.getElementById('btn-refresh-intern')?.addEventListener('click', loadInternData);


    // --- File Upload & AI Extraction ---
    const fileInput = document.getElementById('report-upload');
    
    fileInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (!file) return;

        ui.setStatus(`Extracting data from ${file.name}... Please wait.`, "#3B82F6");

        const reader = new FileReader();
        reader.onload = async () => {
            const base64String = reader.result.split(',')[1];
            const result = await api.extractData(base64String, file.type);

            if (result && result.extracted) {
                try {
                    const data = result.extracted;
                    
                    // Populate Form: Patient info
                    if (data.patientId) document.getElementById('p-id').value = data.patientId;
                    if (data.patientName) document.getElementById('p-name').value = data.patientName;
                    if (data.patientAge) document.getElementById('p-age').value = data.patientAge;

                    // Populate Form: CBC values
                    if (data.cbc?.hemoglobin !== null) document.getElementById('val-hgb').value = parseFloat(data.cbc.hemoglobin);
                    if (data.cbc?.wbc !== null) document.getElementById('val-wbc').value = parseFloat(data.cbc.wbc);
                    if (data.cbc?.platelets !== null) document.getElementById('val-plt').value = parseFloat(data.cbc.platelets);

                    // Populate Form: CMP values
                    if (data.cmp?.creatinine !== null) document.getElementById('val-creat').value = parseFloat(data.cmp.creatinine);
                    if (data.cmp?.glucose !== null) document.getElementById('val-sugar').value = parseFloat(data.cmp.glucose);
                    if (data.cmp?.urea !== null) document.getElementById('val-urea').value = parseFloat(data.cmp.urea);
                    if (data.cmp?.sodium !== null) document.getElementById('val-sodium').value = parseFloat(data.cmp.sodium);
                    if (data.cmp?.potassium !== null) document.getElementById('val-potassium').value = parseFloat(data.cmp.potassium);
                    if (data.cmp?.chloride !== null) document.getElementById('val-chloride').value = parseFloat(data.cmp.chloride);
                    if (data.cmp?.calcium !== null) document.getElementById('val-calcium').value = parseFloat(data.cmp.calcium);
                    if (data.cmp?.albumin !== null) document.getElementById('val-albumin').value = parseFloat(data.cmp.albumin);
                    if (data.cmp?.bilirubin !== null) document.getElementById('val-bilirubin').value = parseFloat(data.cmp.bilirubin);

                    // Show Preview & Update Status
                    ui.renderExtractionPreview(data);
                    ui.setStatus("✅ Extraction complete! Please verify values.", "#10B981");
                    fileInput.value = ""; // Reset input

                } catch (err) {
                    console.error(err);
                    ui.setStatus("❌ Error parsing AI data. Enter manually.", "#EF4444");
                }
            } else {
                ui.setStatus("❌ Extraction failed. Check backend connection.", "#EF4444");
            }
        };

        reader.readAsDataURL(file);
    });

    // --- Manual Entry & Admitting (Triggering the ML Model) ---
    document.getElementById('admit-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Construct the nested payload expected by Flask
        const payload = {
            patientId: document.getElementById('p-id').value || null,
            patientName: document.getElementById('p-name').value,
            patientAge: parseInt(document.getElementById('p-age').value),
            
            cbc: {
                hemoglobin: val('val-hgb') ? parseFloat(val('val-hgb')) : null,
                wbc: val('val-wbc') ? parseFloat(val('val-wbc')) : null,
                platelets: val('val-plt') ? parseFloat(val('val-plt')) : null
            },
            cmp: {
                creatinine: val('val-creat') ? parseFloat(val('val-creat')) : null,
                glucose: val('val-sugar') ? parseFloat(val('val-sugar')) : null,
                urea: val('val-urea') ? parseFloat(val('val-urea')) : null,
                sodium: val('val-sodium') ? parseFloat(val('val-sodium')) : null,
                potassium: val('val-potassium') ? parseFloat(val('val-potassium')) : null,
                chloride: val('val-chloride') ? parseFloat(val('val-chloride')) : null,
                calcium: val('val-calcium') ? parseFloat(val('val-calcium')) : null,
                albumin: val('val-albumin') ? parseFloat(val('val-albumin')) : null,
                bilirubin: val('val-bilirubin') ? parseFloat(val('val-bilirubin')) : null
            }
        };

        const result = await api.predictRisk(payload);
        
        if (result && !result.error) {
            
            // Triage Routing Logic
            if (result.category === "Normal") {
                alert(`Patient ${payload.patientName} assessed as NORMAL (Score: ${result.score}). Routed to Intern Dashboard.`);
            } else {
                alert(`Patient ${payload.patientName} assessed as ${result.category.toUpperCase()} (Score: ${result.score}). Routed to Senior ICU.`);
                // Instantly switch to the Senior dashboard and reload it
                ui.switchView('dashboard');
                await loadSeniorData();
            }

            // Clean up the form
            e.target.reset();
            document.getElementById('upload-status').innerText = "";
            document.getElementById('extraction-preview').style.display = 'none';
        } else {
            alert(`Error: ${result?.error || "Failed to connect to backend."}`);
        }
    });
});