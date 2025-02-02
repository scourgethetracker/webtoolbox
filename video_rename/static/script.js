let fileData = [];

async function loadFiles() {
    try {
        const response = await fetch('/api/files');
        const data = await response.json();
        if (data.success) {
            const parsed = Papa.parse(data.data, {
                header: true,
                skipEmptyLines: true
            });
            console.log("Sample row:", parsed.data[0]); // Debug log
            fileData = parsed.data.map(file => ({
                ...file,
                newName: file.filename,
                originalName: file.filename
            }));
            renderFiles();
        } else {
            alert('Error loading files: ' + data.error);
        }
    } catch (error) {
        alert('Error loading files: ' + error);
    }
}

function renderFiles() {
    const container = document.getElementById('file-list');
    container.innerHTML = fileData.map((file, index) => {
        // Ensure path starts with '/' and encode it properly
        const filePath = file.file_path.startsWith('/') ? file.file_path : '/' + file.file_path;
        const encodedPath = encodeURIComponent(filePath).replace(/%2F/g, '/');
        console.log("Original path:", file.file_path);  // Debug log
        console.log("Encoded path:", encodedPath);      // Debug log
        return `
        <div class="file-entry">
            <input type="text" 
                   value="${file.newName}"
                   onchange="updateFileName(${index}, this.value)">
            <div class="file-info">
                ${file.width}x${file.height}
            </div>
            <button onclick="showMetadata('${encodedPath}')" class="metadata-button">
                Metadata
            </button>
        </div>
    `}).join('');
}

function updateFileName(index, newName) {
    fileData[index].newName = newName;
}

function replacePeriodsWithSpaces() {
    fileData = fileData.map(file => {
        const ext = file.filename.split('.').pop();
        const baseName = file.filename.slice(0, -(ext.length + 1));
        const cleanedName = baseName.replace(/\./g, ' ');
        const newName = `${cleanedName}.${ext}`;
        return {
            ...file,
            newName
        };
    });
    renderFiles();
}

function applyPattern() {
    const pattern = document.getElementById('pattern').value;
    fileData = fileData.map(file => {
        let newName = pattern;
        newName = newName.replace('{title}', file.filename.replace(/\.[^/.]+$/, ""))
                        .replace('{ext}', file.filename.split('.').pop())
                        .replace('{width}', file.width)
                        .replace('{height}', file.height)
                        .replace('{codec}', file.video_codec);
        
        if (!newName.endsWith(`.${file.filename.split('.').pop()}`)) {
            newName += `.${file.filename.split('.').pop()}`;
        }
        
        return {
            ...file,
            newName
        };
    });
    renderFiles();
}

function formatMetadataValue(value) {
    if (typeof value === 'number') {
        return value.toString();
    }
    return value || '';
}

function createMetadataEditor(metadata, editableFields) {
    const sections = ['technical', 'global', 'video', 'audio'];
    let html = '';
    
    sections.forEach(section => {
        if (metadata[section] && Object.keys(metadata[section]).length > 0) {
            html += `
                <div class="metadata-section">
                    <h3>${section.charAt(0).toUpperCase() + section.slice(1)} Metadata</h3>
                    <table class="metadata-table">
                        <thead>
                            <tr>
                                <th>Key</th>
                                <th>Value</th>
                                ${section !== 'technical' ? '<th>Actions</th>' : ''}
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            Object.entries(metadata[section]).forEach(([key, value]) => {
                const isEditable = section !== 'technical' && editableFields[section].includes(key);
                const formattedValue = formatMetadataValue(value);
                
                html += `
                    <tr>
                        <td>${key}</td>
                        <td>
                            ${isEditable ? 
                                `<input type="text" value="${formattedValue}" 
                                        id="metadata-${section}-${key}"
                                        class="metadata-input">` :
                                `<span>${formattedValue}</span>`
                            }
                        </td>
                        ${section !== 'technical' ? `
                        <td>
                            ${isEditable ? `
                                <button onclick="updateMetadataField('${section}', '${key}')"
                                        class="small-button">
                                    Update
                                </button>
                            ` : ''}
                        </td>
                        ` : ''}
                    </tr>
                `;
            });
            
            html += `
                        </tbody>
                    </table>
                </div>
            `;
        }
    });
    
    return html;
}

async function showMetadata(encodedPath) {
    try {
        console.log("Requesting metadata for path:", encodedPath);
        const response = await fetch(`/api/metadata/${encodedPath}`);
        const data = await response.json();
        
        if (!data.success) {
            alert('Error loading metadata: ' + data.error);
            return;
        }

        window.currentFilePath = encodedPath;

        const modal = document.getElementById('metadata-modal');
        const content = document.getElementById('metadata-content');
        
        content.innerHTML = createMetadataEditor(data.metadata, data.editable_fields);
        modal.style.display = 'block';
        
        const closeBtn = modal.querySelector('.close');
        closeBtn.onclick = () => modal.style.display = 'none';
        
        window.onclick = (event) => {
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        };
    } catch (error) {
        console.error("Metadata request error:", error);
        alert('Error loading metadata: ' + error);
    }
}

async function updateMetadataField(section, key) {
    const input = document.getElementById(`metadata-${section}-${key}`);
    const value = input.value;
    
    try {
        const response = await fetch(`/api/metadata/${window.currentFilePath}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                metadata: {
                    [section]: {
                        [key]: value
                    }
                }
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Metadata updated successfully');
        } else {
            alert('Error updating metadata: ' + result.error);
        }
    } catch (error) {
        alert('Error updating metadata: ' + error);
    }
}

async function refreshMetadata() {
    try {
        const button = document.getElementById('refresh-button');
        button.disabled = true;
        button.textContent = 'Refreshing...';
        
        const response = await fetch('/api/refresh-metadata', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Metadata refresh complete');
            loadFiles();
        } else {
            alert('Error refreshing metadata: ' + result.error);
        }
    } catch (error) {
        alert('Error refreshing metadata: ' + error);
    } finally {
        const button = document.getElementById('refresh-button');
        button.disabled = false;
        button.textContent = 'Refresh Metadata';
    }
}

async function saveChanges() {
    const changedFiles = fileData.filter(f => f.newName !== f.originalName);
    if (changedFiles.length === 0) {
        alert('No files to rename');
        return;
    }
    
    try {
        console.log('Sending files to rename:', changedFiles);
        
        const response = await fetch('/api/rename', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                files: changedFiles.map(file => ({
                    file_path: file.file_path,
                    newName: file.newName
                }))
            })
        });
        
        const result = await response.json();
        console.log('Server response:', result);
        
        if (result.success) {
            alert('Files renamed successfully');
            loadFiles();
        } else {
            const errors = result.results
                .filter(r => !r.success)
                .map(r => r.error)
                .join('\n');
            alert('Error renaming files:\n' + errors);
        }
    } catch (error) {
        console.error('Error in saveChanges:', error);
        alert('Error saving changes: ' + error.message);
    }
}

// Load files when page loads
document.addEventListener('DOMContentLoaded', loadFiles);