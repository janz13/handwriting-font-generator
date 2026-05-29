document.addEventListener('DOMContentLoaded', () => {
    let alphaJobId = null;
    let symJobId = null;

    const combineSection = document.getElementById('combineSection');
    const combineBtn = document.getElementById('combineBtn');
    const combineBtnText = combineBtn.querySelector('.btn-text');
    const combineSpinner = combineBtn.querySelector('.spinner');
    const combineHint = document.getElementById('combineHint');
    const errorCardCombine = document.getElementById('errorCardCombine');
    const errorTextCombine = document.getElementById('errorTextCombine');

    function checkCombineReady() {
        if (alphaJobId && symJobId) {
            combineBtn.disabled = false;
            combineBtnText.textContent = 'Download Combined Font';
            if (combineHint) combineHint.textContent = 'Both fonts ready — click to merge them into one file.';
        }
    }

    function showCombineError(msg) {
        errorTextCombine.textContent = msg;
        errorCardCombine.classList.remove('hidden');
    }

    // --- Setup a mode (alphabet | symbols) ---
    function setupMode(mode) {
        const suffix = mode === 'alphabet' ? 'Alpha' : 'Sym';
        const uploadUrl = mode === 'alphabet' ? '/api/upload/alphabet' : '/api/upload/symbols';

        const dropZone = document.getElementById('dropZone' + suffix);
        const fileInput = document.getElementById('fileInput' + suffix);
        const previewContainer = document.getElementById('previewContainer' + suffix);
        const previewImage = document.getElementById('previewImage' + suffix);
        const removeFileBtn = document.getElementById('removeFile' + suffix);
        const generateBtn = document.getElementById('generateBtn' + suffix);
        const resultsCard = document.getElementById('resultsCard' + suffix);
        const errorCard = document.getElementById('errorCard' + suffix);
        const statusMessage = document.getElementById('statusMessage' + suffix);
        const fontPreview = document.getElementById('fontPreview' + suffix);
        const verifyPreview = document.getElementById('verifyPreview' + suffix);
        const downloadLink = document.getElementById('downloadLink' + suffix);
        const errorText = document.getElementById('errorText' + suffix);
        const btnText = generateBtn.querySelector('.btn-text');
        const spinner = generateBtn.querySelector('.spinner');

        let currentFile = null;

        // --- Drag & Drop ---
        dropZone.addEventListener('click', () => fileInput.click());

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length) handleFile(files[0]);
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) handleFile(fileInput.files[0]);
        });

        removeFileBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            clearFile();
        });

        // --- File handling ---
        function handleFile(file) {
            if (!file.type.startsWith('image/')) {
                alert('Please upload an image file.');
                return;
            }
            currentFile = file;
            const reader = new FileReader();
            reader.onload = (e) => {
                previewImage.src = e.target.result;
                dropZone.querySelector('.upload-prompt').classList.add('hidden');
                previewContainer.classList.remove('hidden');
                generateBtn.disabled = false;
            };
            reader.readAsDataURL(file);
        }

        function clearFile() {
            currentFile = null;
            fileInput.value = '';
            previewImage.src = '';
            dropZone.querySelector('.upload-prompt').classList.remove('hidden');
            previewContainer.classList.add('hidden');
            generateBtn.disabled = true;
            resultsCard.classList.add('hidden');
            errorCard.classList.add('hidden');
            btnText.textContent = mode === 'alphabet' ? 'Generate Alphabet Font' : 'Generate Symbol Font';
            spinner.classList.add('hidden');
        }

        // --- Upload & Pipeline ---
        generateBtn.addEventListener('click', async () => {
            if (!currentFile) return;

            generateBtn.disabled = true;
            btnText.textContent = 'Processing…';
            spinner.classList.remove('hidden');
            resultsCard.classList.add('hidden');
            errorCard.classList.add('hidden');

            const formData = new FormData();
            formData.append('image', currentFile);

            try {
                const response = await fetch(uploadUrl, {
                    method: 'POST',
                    body: formData,
                });
                const data = await response.json();

                if (data.success) {
                    statusMessage.textContent = data.message;
                    downloadLink.href = data.download_url;
                    fontPreview.src = data.preview_url;
                    verifyPreview.src = data.verify_url;
                    resultsCard.classList.remove('hidden');
                    errorCard.classList.add('hidden');

                    // Store job ID for combine
                    if (mode === 'alphabet') alphaJobId = data.job_id;
                    else symJobId = data.job_id;
                    checkCombineReady();
                } else {
                    showError(data.error || 'Unknown error');
                }
            } catch (err) {
                showError('Network error: ' + err.message);
            } finally {
                generateBtn.disabled = false;
                btnText.textContent = mode === 'alphabet' ? 'Generate Alphabet Font' : 'Generate Symbol Font';
                spinner.classList.add('hidden');
            }
        });

        function showError(msg) {
            errorText.textContent = msg;
            errorCard.classList.remove('hidden');
            resultsCard.classList.add('hidden');
        }

        // Retry buttons
        document.querySelectorAll('.retry-btn').forEach(btn => {
            if (btn.dataset.mode === mode) {
                btn.addEventListener('click', clearFile);
            }
        });
    }

    setupMode('alphabet');
    setupMode('symbols');

    // --- Combine handler ---
    combineBtn.addEventListener('click', async () => {
        if (!alphaJobId || !symJobId) return;

        combineBtn.disabled = true;
        combineBtnText.textContent = 'Merging…';
        combineSpinner.classList.remove('hidden');
        errorCardCombine.classList.add('hidden');

        try {
            const response = await fetch('/api/combine', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ alpha_job_id: alphaJobId, sym_job_id: symJobId }),
            });
            const data = await response.json();

            if (data.success) {
                // Trigger download
                const a = document.createElement('a');
                a.href = data.download_url;
                a.download = 'MyHandwriting_Combined.ttf';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                combineBtnText.textContent = 'Downloaded!';
            } else {
                showCombineError(data.error || 'Merge failed.');
                combineBtnText.textContent = 'Download Combined Font';
            }
        } catch (err) {
            showCombineError('Network error: ' + err.message);
            combineBtnText.textContent = 'Download Combined Font';
        } finally {
            combineBtn.disabled = false;
            combineSpinner.classList.add('hidden');
        }
    });
});
