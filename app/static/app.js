/* Frontend logic: API calls, login, upload, search and record actions. */
let currentUser = null;
const $ = (selector) => document.querySelector(selector);

async function api(url, options = {}) {
    const response = await fetch(url, { credentials: "same-origin", ...options });
    let result = {};
    try { result = await response.json(); } catch (_) {}
    if (!response.ok) throw new Error(result.error || "Request failed.");
    return result;
}
function notify(message) {
    const box = $("#toast");
    box.textContent = message;
    box.classList.add("show");
    setTimeout(() => box.classList.remove("show"), 2800);
}
function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char =>
        ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
}
function showTab(name) {
    $("#loginForm").classList.toggle("hidden", name !== "login");
    $("#registerForm").classList.toggle("hidden", name !== "register");
    document.querySelectorAll(".tab").forEach(button =>
        button.classList.toggle("active", button.dataset.tab === name));
    $("#authMessage").textContent = "";
}
document.querySelectorAll(".tab").forEach(button =>
    button.addEventListener("click", () => showTab(button.dataset.tab)));

$("#loginForm").addEventListener("submit", async event => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target));
    try {
        await api("/api/auth/login", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(data)});
        await startWorkspace();
    } catch (error) { $("#authMessage").textContent = error.message; }
});
$("#registerForm").addEventListener("submit", async event => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.target));
    try {
        await api("/api/auth/register", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(data)});
        await startWorkspace();
    } catch (error) { $("#authMessage").textContent = error.message; }
});
$("#logoutBtn").addEventListener("click", async () => {
    try { await api("/api/auth/logout", {method:"POST"}); } finally {
        currentUser = null;
        $("#workspace").classList.add("hidden");
        $("#authView").classList.remove("hidden");
        $("#userArea").classList.add("hidden");
        showTab("login");
    }
});

async function startWorkspace() {
    try {
        currentUser = await api("/api/auth/me");
        $("#authView").classList.add("hidden");
        $("#workspace").classList.remove("hidden");
        $("#userArea").classList.remove("hidden");
        $("#userName").textContent = `${currentUser.name} · ${currentUser.role}`;
        $("#greeting").textContent = `Hello, ${currentUser.name.split(" ")[0]}`;
        $("#roleHint").textContent = currentUser.role === "patient"
            ? "Upload your medical records and control doctor access."
            : currentUser.role === "doctor"
            ? "Only patient records shared with your doctor account appear here."
            : "View system users and monitor platform activity.";
        $("#uploadPanel").classList.toggle("hidden", currentUser.role !== "patient");
        $("#adminPanel").classList.toggle("hidden", currentUser.role !== "admin");
        await loadRecords();
        await loadLogs();
        if (currentUser.role === "admin") await loadUsers();
    } catch (_) {
        $("#authView").classList.remove("hidden");
        $("#workspace").classList.add("hidden");
    }
}

$("#uploadForm").addEventListener("submit", async event => {
    event.preventDefault();
    try {
        await api("/api/records/upload", {method:"POST", body:new FormData(event.target)});
        event.target.reset();
        notify("Medical record uploaded successfully.");
        await loadRecords();
        await loadLogs();
    } catch (error) { notify(error.message); }
});
$("#searchBox").addEventListener("input", () => loadRecords());
$("#refreshLogs").addEventListener("click", loadLogs);

async function loadRecords() {
    if (!currentUser) return;
    try {
        const keyword = encodeURIComponent($("#searchBox").value || "");
        const records = await api(`/api/records?q=${keyword}`);
        $("#recordCount").textContent = records.length;
        const grid = $("#recordGrid");
        if (!records.length) {
            grid.innerHTML = '<div class="empty">No records found. Upload a record or check your search.</div>';
            return;
        }
        grid.innerHTML = records.map(record => `
            <article class="record">
                <div class="file-icon">📄</div>
                <h3>${escapeHTML(record.title)}</h3>
                <span class="tag">${escapeHTML(record.category)}</span>
                <p>${escapeHTML(record.description || "No description added.")}</p>
                <p>${escapeHTML(record.original_filename || "")}<br>${escapeHTML(record.record_date || "Date not provided")}
                ${record.patient_name ? "<br>Patient: " + escapeHTML(record.patient_name) : ""}</p>
                <div class="actions">
                    <button class="btn btn-primary" onclick="downloadRecord(${record.id})">Download</button>
                    ${currentUser.role === "patient" ? `
                    <button class="btn btn-light" onclick="shareRecord(${record.id})">Share</button>
                    <button class="btn btn-light" onclick="grantAccess(${record.id})">Grant</button>
                    <button class="btn btn-light" onclick="revokeAccess(${record.id})">Revoke</button>
                    <button class="btn btn-light" onclick="deleteRecord(${record.id})">Delete</button>` : ""}
                    ${currentUser.role === "doctor" ? `<button class="btn btn-light" onclick="addNote(${record.id})">Add note</button>` : ""}
                </div>
            </article>`).join("");
    } catch (error) { notify(error.message); }
}
function downloadRecord(id) { window.location.href = `/api/records/${id}/download`; }

async function shareRecord(id) {
    const email = prompt("Enter registered doctor email. Leave blank for a secure link:");
    if (email === null) return;
    const hours = prompt("Link validity in hours (1 to 720):", "24");
    if (hours === null) return;
    try {
        const result = await api(`/api/records/${id}/share`, {
            method:"POST", headers:{"Content-Type":"application/json"},
            body:JSON.stringify({doctor_email:email, expiry_hours:Number(hours)})
        });
        alert(`Temporary share created. Expires: ${result.expires_at}\n\n${result.share_url}`);
        notify(result.message);
        await loadLogs();
    } catch (error) { notify(error.message); }
}
async function grantAccess(id) {
    const email = prompt("Enter the registered doctor's email:");
    if (!email) return;
    try {
        const result = await api(`/api/records/${id}/grant`, {
            method:"POST", headers:{"Content-Type":"application/json"},
            body:JSON.stringify({doctor_email:email})
        });
        notify(result.message);
        await loadLogs();
    } catch (error) { notify(error.message); }
}
async function revokeAccess(id) {
    if (!confirm("Revoke all active share links and doctor access for this record?")) return;
    try {
        const result = await api(`/api/records/${id}/revoke`, {method:"POST"});
        notify(result.message);
        await loadLogs();
    } catch (error) { notify(error.message); }
}
async function deleteRecord(id) {
    if (!confirm("Permanently delete this record and its share links?")) return;
    try {
        const result = await api(`/api/records/${id}`, {method:"DELETE"});
        notify(result.message);
        await loadRecords();
        await loadLogs();
    } catch (error) { notify(error.message); }
}
async function addNote(id) {
    const note = prompt("Enter your note for this shared record:");
    if (!note) return;
    try {
        const result = await api(`/api/records/${id}/notes`, {
            method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({note})
        });
        notify(result.message);
        await loadLogs();
    } catch (error) { notify(error.message); }
}
async function loadLogs() {
    try {
        const logs = await api("/api/logs");
        $("#logs").innerHTML = logs.length ? logs.map(log => `
            <div class="log-row"><span><b>${escapeHTML(log.action)}</b> · ${escapeHTML(log.record_title || log.details || "Account activity")}
            ${log.user_name ? " · " + escapeHTML(log.user_name) : ""}</span><time>${escapeHTML(log.created_at)}</time></div>
        `).join("") : '<p>No activity yet.</p>';
    } catch (_) {}
}
async function loadUsers() {
    try {
        const users = await api("/api/admin/users");
        $("#users").innerHTML = users.map(user => `
            <div class="log-row"><span><b>${escapeHTML(user.name)}</b> · ${escapeHTML(user.email)} · ${escapeHTML(user.role)}</span>
            <time>${escapeHTML(user.created_at)}</time></div>`).join("");
    } catch (error) { notify(error.message); }
}
startWorkspace();
