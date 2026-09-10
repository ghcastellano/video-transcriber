const API_URL = "http://localhost:8000";

const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const fileInfo = document.getElementById("file-info");
const fileName = document.getElementById("file-name");
const fileSize = document.getElementById("file-size");
const removeFile = document.getElementById("remove-file");
const uploadBtn = document.getElementById("upload-btn");
const uploadSection = document.getElementById("upload-section");
const progressSection = document.getElementById("progress-section");
const progressFill = document.getElementById("progress-fill");
const progressText = document.getElementById("progress-text");
const resultsSection = document.getElementById("results-section");

let selectedFile = null;

// --- File Selection ---

dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("drag-over");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file) selectFile(file);
});

fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) selectFile(fileInput.files[0]);
});

removeFile.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    fileInfo.classList.add("hidden");
    uploadBtn.classList.add("hidden");
    dropZone.classList.remove("hidden");
});

function selectFile(file) {
    if (!file.type.startsWith("video/")) {
        alert("Por favor, selecione um arquivo de vídeo.");
        return;
    }
    if (file.size > 100 * 1024 * 1024) {
        alert("O arquivo excede o limite de 100MB.");
        return;
    }

    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatSize(file.size);
    fileInfo.classList.remove("hidden");
    uploadBtn.classList.remove("hidden");
    uploadBtn.disabled = false;
    dropZone.classList.add("hidden");
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

// --- Upload ---

uploadBtn.addEventListener("click", uploadVideo);

async function uploadVideo() {
    if (!selectedFile) return;

    uploadBtn.disabled = true;
    uploadSection.classList.add("hidden");
    progressSection.classList.remove("hidden");
    resultsSection.classList.add("hidden");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
        // Upload with progress tracking via XMLHttpRequest
        const result = await new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            xhr.upload.addEventListener("progress", (e) => {
                if (e.lengthComputable) {
                    const pct = Math.round((e.loaded / e.total) * 100);
                    progressFill.style.width = pct + "%";
                    if (pct < 100) {
                        progressText.textContent = `Enviando vídeo... ${pct}%`;
                    } else {
                        progressText.textContent = "Processando transcrição e análise de slides...";
                        progressFill.style.width = "100%";
                    }
                }
            });

            xhr.addEventListener("load", () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(JSON.parse(xhr.responseText));
                } else {
                    try {
                        const err = JSON.parse(xhr.responseText);
                        reject(new Error(err.detail || "Erro no servidor"));
                    } catch {
                        reject(new Error(`Erro ${xhr.status}`));
                    }
                }
            });

            xhr.addEventListener("error", () => reject(new Error("Erro de conexão")));
            xhr.addEventListener("timeout", () => reject(new Error("Timeout na requisição")));

            xhr.open("POST", `${API_URL}/api/upload`);
            xhr.timeout = 600000; // 10 minutes
            xhr.send(formData);
        });

        showResults(result);
    } catch (err) {
        alert("Erro: " + err.message);
        resetUI();
    }
}

function resetUI() {
    progressSection.classList.add("hidden");
    uploadSection.classList.remove("hidden");
    uploadBtn.disabled = false;
    fileInfo.classList.add("hidden");
    dropZone.classList.remove("hidden");
    uploadBtn.classList.add("hidden");
    selectedFile = null;
    fileInput.value = "";
    progressFill.style.width = "0%";
}

// --- Results ---

function showResults(data) {
    progressSection.classList.add("hidden");
    resultsSection.classList.remove("hidden");

    // Transcription
    const transcription = data.transcription;
    const langBadge = document.getElementById("language-badge");
    langBadge.textContent = `Idioma: ${transcription.language}`;

    const transcriptionText = document.getElementById("transcription-text");
    transcriptionText.textContent = transcription.full_text;

    const segmentsList = document.getElementById("segments-list");
    segmentsList.innerHTML = "";

    if (transcription.segments && transcription.segments.length > 0) {
        transcription.segments.forEach((seg) => {
            const div = document.createElement("div");
            div.className = "segment";
            div.innerHTML = `
                <span class="segment-time">${formatTime(seg.start)} → ${formatTime(seg.end)}</span>
                <span class="segment-text">${escapeHtml(seg.text)}</span>
            `;
            segmentsList.appendChild(div);
        });
    }

    // Slides
    const slidesList = document.getElementById("slides-list");
    slidesList.innerHTML = "";

    if (data.slides && data.slides.length > 0) {
        data.slides.forEach((slide, idx) => {
            const card = document.createElement("div");
            card.className = "slide-card";
            card.innerHTML = `
                <div class="slide-header">
                    <div class="slide-number">${idx + 1}</div>
                    <span class="slide-timestamp">${formatTime(slide.timestamp)}</span>
                </div>
                <div class="slide-analysis">${formatMarkdown(slide.analysis)}</div>
            `;
            slidesList.appendChild(card);
        });
    } else {
        slidesList.innerHTML = '<p style="color:#888;">Nenhum slide detectado no vídeo.</p>';
    }

    // Copy button
    document.getElementById("copy-transcription").addEventListener("click", () => {
        navigator.clipboard.writeText(transcription.full_text).then(() => {
            const btn = document.getElementById("copy-transcription");
            btn.textContent = "Copiado!";
            setTimeout(() => (btn.textContent = "Copiar"), 2000);
        });
    });

    // New upload button
    const uploadArea = document.createElement("div");
    uploadArea.style.textAlign = "center";
    uploadArea.style.marginTop = "32px";
    const newBtn = document.createElement("button");
    newBtn.className = "btn-secondary";
    newBtn.textContent = "Processar outro vídeo";
    newBtn.addEventListener("click", () => {
        resultsSection.classList.add("hidden");
        resetUI();
    });
    uploadArea.appendChild(newBtn);
    resultsSection.appendChild(uploadArea);
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

function formatMarkdown(text) {
    // Simple markdown-like formatting
    return escapeHtml(text)
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\n/g, "<br>");
}

// --- Tabs ---

document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
        tab.classList.add("active");
        document.getElementById(`tab-${tab.dataset.tab}`).classList.add("active");
    });
});
