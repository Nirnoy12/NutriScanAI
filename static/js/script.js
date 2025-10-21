// ---- Firebase auth placeholders ----
// Later you’ll plug in your Firebase config here
document.getElementById("googleLoginBtn").onclick = () => {
  alert("Google login coming soon (Firebase integration placeholder).");
};

// ---- File upload and analysis ----
document.getElementById("uploadBtn").addEventListener("click", async () => {
  const fileInput = document.getElementById("fileInput");
  const loader = document.getElementById("loader");
  const resultSection = document.getElementById("result-section");

  if (!fileInput.files.length) {
    alert("Please choose an image first.");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  loader.style.display = "block";

  try {
    const res = await fetch("/upload", { method: "POST", body: formData });
    const data = await res.json();

    loader.style.display = "none";
    resultSection.style.display = "block";

    document.getElementById("quickVerdict").innerText = data.quick_verdict;
    window.latestReport = data.detailed_report;

    // Add to history
    const li = document.createElement("li");
    li.textContent = `${data.timestamp} - ${data.filename}`;
    document.getElementById("historyList").appendChild(li);
  } catch (err) {
    loader.style.display = "none";
    alert("Error during analysis.");
  }
});

// ---- View Detailed Report ----
document.getElementById("viewReportBtn").addEventListener("click", () => {
  const detailedDiv = document.getElementById("detailedReport");
  detailedDiv.style.display = detailedDiv.style.display === "none" ? "block" : "none";

  if (!window.latestReport) return;

  let html = "<table><tr><th>Nutrient</th><th>Impact</th></tr>";
  window.latestReport.forEach(r => {
    html += `<tr><td>${r.nutrient}</td><td>${r.impact}</td></tr>`;
  });
  html += "</table>";
  detailedDiv.innerHTML = html;
});

// ---- Simple chatbot placeholder ----
document.getElementById("sendMsgBtn").addEventListener("click", () => {
  const chatWindow = document.getElementById("chatWindow");
  const input = document.getElementById("chatInput");
  const msg = input.value.trim();
  if (!msg) return;

  const userMsg = document.createElement("p");
  userMsg.textContent = "🧑: " + msg;
  chatWindow.appendChild(userMsg);

  // Very basic bot reply
  const botReply = document.createElement("p");
  botReply.textContent = "🤖: I'm still learning! Detailed nutrition chat coming soon.";
  chatWindow.appendChild(botReply);

  input.value = "";
  chatWindow.scrollTop = chatWindow.scrollHeight;
});
