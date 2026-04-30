let patients = []; // Central state

// ✅ Utility function (correct placement)
function val(id) {
    const v = document.getElementById(id).value;
    return v === "" ? null : v;
}

document.addEventListener("DOMContentLoaded", () => {
    
    // --- Navigation ---
    document.getElementById('nav-admit').addEventListener('click', () => ui.switchView('admit'));
    document.getElementById('nav-dashboard').addEventListener('click', () => ui.switchView('dashboard'));

    // --- File Upload & AI Extraction ---
    const fileInput = document.getElementById('report-upload');
    
    fileInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (!file) return;

        ui.setStatus(`Extracting data from ${file.name}... Please wait.`, "var(--accent)");

        const reader = new FileReader();
        reader.onload = async () => {
            const base64String = reader.result.split(',')[1];
            const result = await api.extractData(base64String, file.type);

            if (result && result.extracted) {
                try {
                    const data = result.extracted;

                    console.log("EXTRACTED DATA:", data);

                    // Patient info
                    if (data.patientName) document.getElementById('p-name').value = data.patientName;
                    if (data.patientAge) document.getElementById('p-age').value = data.patientAge;

                    // CBC values
                    if (data.cbc?.hemoglobin !== null && !isNaN(data.cbc.hemoglobin))
                        document.getElementById('val-hgb').value = parseFloat(data.cbc.hemoglobin);

                    if (data.cbc?.wbc !== null && !isNaN(data.cbc.wbc))
                        document.getElementById('val-wbc').value = parseFloat(data.cbc.wbc);

                    if (data.cbc?.platelets !== null && !isNaN(data.cbc.platelets))
                        document.getElementById('val-plt').value = parseFloat(data.cbc.platelets);

                    // CMP values
                    if (data.cmp?.creatinine !== null && !isNaN(data.cmp.creatinine))
                        document.getElementById('val-creat').value = parseFloat(data.cmp.creatinine);

                    if (data.cmp?.glucose !== null && !isNaN(data.cmp.glucose))
                        document.getElementById('val-sugar').value = parseFloat(data.cmp.glucose);

                    // 🔥 NEW PARAMETERS
                    if (data.cmp?.urea !== null && !isNaN(data.cmp.urea))
                        document.getElementById('val-urea').value = parseFloat(data.cmp.urea);

                    if (data.cmp?.sodium !== null && !isNaN(data.cmp.sodium))
                        document.getElementById('val-sodium').value = parseFloat(data.cmp.sodium);

                    if (data.cmp?.potassium !== null && !isNaN(data.cmp.potassium))
                        document.getElementById('val-potassium').value = parseFloat(data.cmp.potassium);

                    if (data.cmp?.chloride !== null && !isNaN(data.cmp.chloride))
                        document.getElementById('val-chloride').value = parseFloat(data.cmp.chloride);

                    if (data.cmp?.calcium !== null && !isNaN(data.cmp.calcium))
                        document.getElementById('val-calcium').value = parseFloat(data.cmp.calcium);

                    if (data.cmp?.albumin !== null && !isNaN(data.cmp.albumin))
                        document.getElementById('val-albumin').value = parseFloat(data.cmp.albumin);

                    if (data.cmp?.bilirubin !== null && !isNaN(data.cmp.bilirubin))
                        document.getElementById('val-bilirubin').value = parseFloat(data.cmp.bilirubin);

                    ui.setStatus("✅ Extraction complete! Please verify values.", "var(--normal)");
                    fileInput.value = "";

                } catch (err) {
                    console.error(err);
                    ui.setStatus("❌ Error parsing AI data. Enter manually.", "var(--critical)");
                }
            } else {
                ui.setStatus("❌ Extraction failed. Check backend connection.", "var(--critical)");
            }
        };

        reader.readAsDataURL(file);
    });

    // --- Manual Entry & Admitting ---
    document.getElementById('admit-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const payload = {
            patientName: document.getElementById('p-name').value,
            patientAge: parseInt(document.getElementById('p-age').value),

            hemoglobin: val('val-hgb') ? parseFloat(val('val-hgb')) : null,
            wbc: val('val-wbc') ? parseFloat(val('val-wbc')) : null,
            platelets: val('val-plt') ? parseFloat(val('val-plt')) : null,
            creatinine: val('val-creat') ? parseFloat(val('val-creat')) : null,
            glucose: val('val-sugar') ? parseFloat(val('val-sugar')) : null,

            // 🔥 ALL 12 PARAMETERS
            urea: val('val-urea') ? parseFloat(val('val-urea')) : null,
            sodium: val('val-sodium') ? parseFloat(val('val-sodium')) : null,
            potassium: val('val-potassium') ? parseFloat(val('val-potassium')) : null,
            chloride: val('val-chloride') ? parseFloat(val('val-chloride')) : null,
            calcium: val('val-calcium') ? parseFloat(val('val-calcium')) : null,
            albumin: val('val-albumin') ? parseFloat(val('val-albumin')) : null,
            bilirubin: val('val-bilirubin') ? parseFloat(val('val-bilirubin')) : null
        };

        const result = await api.predictRisk(payload);
        
        if (result) {
            const newPatient = {
                id: Date.now(),
                name: document.getElementById('p-name').value,
                age: document.getElementById('p-age').value,
                score: result.score,
                category: result.category,
                trend: result.trend,
                monitoring: result.monitoring,
                ruleAlerts: result.ruleAlerts,
                timestamp: Date.now()
            };

            patients.push(newPatient);
            ui.renderPatient(newPatient);

            e.target.reset();
            document.getElementById('upload-status').innerText = "";
            ui.switchView('dashboard');
        } else {
            alert("Failed to compute risk score. Is your Flask backend running?");
        }
    });
});