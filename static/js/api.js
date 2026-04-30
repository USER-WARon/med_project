const api = {
    async predictRisk(bloodValues) {
        try {
            const response = await fetch('/api/predict', {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(bloodValues)
            });
            if (!response.ok) throw new Error("API Error");
            return await response.json();
        } catch (error) {
            console.error("Prediction failed:", error);
            return null;
        }
    },

    async extractData(base64Data, mimeType) {
        try {
            const response = await fetch('/api/extract', {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ file_base64: base64Data, media_type: mimeType })
            });
            if (!response.ok) throw new Error("Extraction API Error");
            return await response.json();
        } catch (error) {
            console.error("Extraction failed:", error);
            return null;
        }
    }
};