document.addEventListener('DOMContentLoaded', () => {

  // --- Get All Elements ---
  const navButtons = document.querySelectorAll('.nav-btn');
  const pages = document.querySelectorAll('.page');
  const googleLoginBtn = document.getElementById('googleLoginBtn');
  const viewReportBtn = document.getElementById('viewReportBtn');
  const sendMsgBtn = document.getElementById('sendMsgBtn');
  const captureBtn = document.getElementById('captureBtn');
  const fileInput = document.getElementById('fileInput');
  const videoFeed = document.getElementById('camera-feed');
  const canvas = document.getElementById('capture-canvas');
  const loader = document.getElementById('loader');
  const resultSection = document.getElementById('result-section');
  const quickVerdict = document.getElementById('quickVerdict');
  const detailedReport = document.getElementById('detailedReport');
  const historyList = document.getElementById('historyList'); 
  const chatWindow = document.getElementById('chatWindow');
  const chatInput = document.getElementById('chatInput');
  const fallbackLabel = document.getElementById('file-fallback-label');
  const scannerOverlay = document.getElementById('scanner-overlay');
  const scanAgainBtn = document.getElementById('scanAgainBtn');
  const cameraContainer = document.getElementById('camera-container');

  // --- Global State ---
  let cameraStream = null;
  window.latestReport = null;
  // --- We no longer need lastCapturedBlob ---
  
  // --- 1. Page Navigation Logic ---
  function activatePage(pageId) {
    pages.forEach(page => page.classList.remove('active'));
    navButtons.forEach(btn => btn.classList.remove('active'));

    document.getElementById(pageId).classList.add('active');
    const activeNavBtn = document.querySelector(`.nav-btn[data-page="${pageId}"]`);
    if (activeNavBtn) {
      activeNavBtn.classList.add('active');
    }

    if (pageId !== 'page-scan' && cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      videoFeed.srcObject = null;
      cameraStream = null;
    } else if (pageId === 'page-scan' && !cameraStream) {
      startCamera();
    }

    if (pageId === 'page-history') {
      fetchHistory();
    }
  }

  navButtons.forEach(button => {
    button.addEventListener('click', () => {
      activatePage(button.dataset.page);
    });
  });

  activatePage('page-scan');


  // --- 2. Camera Logic ---
  async function startCamera() {
    if (cameraStream) return;

    cameraContainer.style.display = 'block';

    scannerOverlay.style.display = 'block';
    videoFeed.style.display = 'block';
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }
      });
      videoFeed.srcObject = stream;
      cameraStream = stream;
      fallbackLabel.style.display = 'none';
    } catch (err) {
      console.warn("Environment camera not found, trying user camera:", err);
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        videoFeed.srcObject = stream;
        cameraStream = stream;
        fallbackLabel.style.display = 'none';
      } catch (finalErr) {
        console.error("Could not access camera:", finalErr);
        cameraContainer.style.display = 'none';
        fallbackLabel.style.display = 'block';
        scannerOverlay.style.display = 'none';
        videoFeed.style.display = 'none';
      }
    }
  }
  
  // --- 3. Capture & Upload Logic ---

  // --- UPDATED: Helper function to create a history item (with buttons) ---
  function renderHistoryItem(scanData, prepend = false) {
    const item = document.createElement('li');
    item.className = 'history-item';

    // Image
    const img = document.createElement('img');
    img.src = `static/uploads/${scanData.filename}`;
    img.alt = `Scan from ${scanData.timestamp}`;

    // Info (Verdict + Timestamp)
    const info = document.createElement('div');
    info.className = 'history-info';
    info.innerHTML = `<strong>${scanData.quick_verdict}</strong><p>${scanData.timestamp}</p>`;

    // --- NEW: Action Buttons Container ---
    const actions = document.createElement('div');
    actions.className = 'history-item-actions';

    // Chat Button
    const chatBtn = document.createElement('button');
    chatBtn.className = 'history-chat-btn';
    chatBtn.innerHTML = '<i class="fa-solid fa-robot"></i>';
    // Store data on the button itself for the listener
    chatBtn.dataset.topic = scanData.ocr_text || scanData.quick_verdict; 
    
    // Share Button
    const shareBtn = document.createElement('button');
    shareBtn.className = 'history-share-btn';
    shareBtn.innerHTML = '<i class="fa-solid fa-share"></i>';
    // Store data on the button
    shareBtn.dataset.filename = scanData.filename;
    shareBtn.dataset.verdict = scanData.quick_verdict;
    
    actions.appendChild(chatBtn);
    actions.appendChild(shareBtn);
    
    // Assemble the item
    item.appendChild(img);
    item.appendChild(info);
    item.appendChild(actions); // Add the new actions div

    if (prepend) {
      historyList.prepend(item); 
    } else {
      historyList.appendChild(item); 
    }
  }
  // -----------------------------------------------------------------
  
  async function handleUpload(formData) {
    loader.style.display = 'block';
    resultSection.style.display = 'none';
    
    // --- HIDE ALL CAMERA ELEMENTS ---
    scannerOverlay.style.display = 'none';
    videoFeed.style.display = 'none';
    cameraContainer.style.display = 'none'; // <-- ADD THIS LINE

    try {
      const res = await fetch("/analyze", { method: "POST", body: formData }); 
      const data = await res.json(); 

      loader.style.display = 'none';
      resultSection.style.display = 'block'; // <-- This will now be visible

      quickVerdict.innerText = data.quick_verdict;
      window.latestReport = data.detailed_report;
      
      if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
      }
      
    } catch (err) {
      console.error("Error during analysis:", err);
      loader.style.display = 'none';
      alert("Error during analysis.");
      
      // On error, reshow the camera
      cameraContainer.style.display = 'block'; // <-- ADD THIS
      startCamera(); // <-- Restart the camera
    }
  }

  // "Scan Again" button listener
  scanAgainBtn.addEventListener('click', () => {
      resultSection.style.display = 'none';
      
      cameraContainer.style.display = 'block'; // <-- ADD THIS LINE
      
      startCamera(); // Restart the camera
  });

  // (Smarter Capture Button logic is unchanged)
  captureBtn.addEventListener('click', () => {
    const activePage = document.querySelector('.page.active');
    
    if (activePage.id === 'page-scan') {
      if (!cameraStream) {
        alert("Camera not active. Please allow camera access or upload a file.");
        fileInput.click();
        return;
      }
      canvas.width = videoFeed.videoWidth;
      canvas.height = videoFeed.videoHeight;
      const context = canvas.getContext('2d');
      context.drawImage(videoFeed, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(blob => {
        // --- We no longer save the blob globally ---
        const formData = new FormData();
        formData.append('file', blob, 'scan.jpg');
        handleUpload(formData);
      }, 'image/jpeg', 0.9);
    
    } else {
      activatePage('page-scan');
    }
  });

  // (Fallback file input logic is unchanged)
  fileInput.addEventListener('change', () => {
    if (!fileInput.files.length) return;
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    handleUpload(formData);
  });
  fallbackLabel.addEventListener('click', () => {
      fileInput.click();
  });


  // --- 4. Other Logic (Unchanged) ---
  // (Your login, viewReportBtn, and sendMsgBtn listeners remain here)
  
  // View Detailed Report
  viewReportBtn.addEventListener("click", () => {
    detailedReport.style.display = detailedReport.style.display === "none" ? "block" : "none";
    if (detailedReport.style.display === "block" && window.latestReport) {
      let html = "<table><tr><th>Nutrient</th><th>Impact</th></tr>";
      window.latestReport.forEach(r => {
        html += `<tr><td>${r.nutrient}</td><td>${r.impact}</td></tr>`;
      });
      html += "</table>";
      detailedReport.innerHTML = html;
    } else {
      detailedReport.innerHTML = '';
    }
  });

  // Simple chatbot placeholder
  sendMsgBtn.addEventListener("click", () => {
    const msg = chatInput.value.trim();
    if (!msg) return;
    
    // Call the function to send a message
    sendMessageToBot(msg);
  });
  
  // Helper function to send chat messages
  function sendMessageToBot(msg) {
    if (!msg) return;
    
    const userMsg = document.createElement("p");
    userMsg.textContent = "🧑: " + msg;
    chatWindow.appendChild(userMsg);

    // Very basic bot reply
    const botReply = document.createElement("p");
    botReply.textContent = "🤖: I'm still learning! Detailed nutrition chat coming soon.";
    chatWindow.appendChild(botReply);

    chatInput.value = "";
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }
  
  
  // --- 5. History Page Logic ---

  // --- NEW: Function to start chat with a topic ---
  function startChatWithTopic(topic) {
    // 1. Switch to the chatbot page
    activatePage('page-chatbot');
    
    // 2. Programmatically "ask" about the topic
    const prefillMsg = `Tell me more about: "${topic}"`;
    sendMessageToBot(prefillMsg);
  }

  // --- NEW: Function to share a history item ---
  async function shareHistoryItem(filename, verdict) {
    const imageUrl = `${window.location.origin}/static/uploads/${filename}`;
    
    try {
      // 1. Fetch the image and convert it to a blob
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      
      // 2. Create a File object
      const file = new File([blob], filename, { type: blob.type });
      
      // 3. Create share data
      const shareData = {
        title: 'My NutriScanAI Result',
        text: `NutriScanAI verdict: ${verdict}`,
        files: [file]
      };

      // 4. Try to share
      if (navigator.canShare && navigator.canShare(shareData)) {
        await navigator.share(shareData);
      } else {
        alert("Sharing files is not supported on this browser.");
      }
    } catch (err) {
      console.error('Share failed:', err);
      alert("Sharing failed. You may need to be on a secure (https) connection or use a supported browser.");
    }
  }

  // --- NEW: Event Delegation for History List ---
  // We add ONE listener to the <ul> and check what was clicked
  historyList.addEventListener('click', (e) => {
    // Find the button that was clicked, even if the <i> icon was clicked
    const shareButton = e.target.closest('.history-share-btn');
    const chatButton = e.target.closest('.history-chat-btn');

    if (shareButton) {
      // Get the data we stored on the button
      const { filename, verdict } = shareButton.dataset;
      shareHistoryItem(filename, verdict);
      return; // Stop further checks
    }

    if (chatButton) {
      // Get the data from the button
      const { topic } = chatButton.dataset;
      startChatWithTopic(topic);
      return; // Stop further checks
    }
  });
  
  
  // Function to Fetch and Render History (unchanged)
  async function fetchHistory() {
    historyList.innerHTML = '<p class="loading-msg">Loading history...</p>';
    try {
      const res = await fetch('/history'); // Assumes you're logged in
      if (!res.ok) {
         // If we get a 401 (unauthorized), redirect to login
         if (res.status === 401) {
            window.location.href = '/login';
         }
         throw new Error('Failed to fetch history');
      }
      
      const data = await res.json(); 
      historyList.innerHTML = ''; 

      if (data.length === 0) {
        historyList.innerHTML = '<p class="loading-msg">No scan history found.</p>';
        return;
      }
      
      data.forEach(scanData => {
        renderHistoryItem(scanData, false); 
      });

    } catch (err) {
      console.error('Error loading history:', err);
      historyList.innerHTML = '<p class="loading-msg">Error loading history. Please try again.</p>';
    }
  }
  
  // --- We removed the old shareBtn listener ---

});