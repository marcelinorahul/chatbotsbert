// frontend/js/chatbot.js

$(document).ready(function() {
    // Config
    const USE_MOCK_API = false; // Set ke true untuk demonstrasi tanpa backend
    const API_URL = 'http://localhost:5000/api'; // URL Flask API
    
    // Avatar constants
    const USER_AVATAR = '<i class="fas fa-user"></i>';
    const BOT_AVATAR = '<i class="fas fa-robot"></i>';
    
    // DOM Elements
    const chatMessages = $('#chat-messages');
    const userInput = $('#user-input');
    const sendButton = $('#send-btn');
    const infoButton = $('#chatbot-info-btn'); // ✅ PERBAIKAN: ID yang benar
    const closeButton = $('#close-btn');
    const clearButton = $('#clear-btn');
    const printButton = $('#print-btn');
    const currentTimeDisplay = $('#current-time');
    const todayDateDisplay = $('#today-date');
    const chatbotContainer = $('.chatbot-container');
    const widgetButton = $('.chatbot-widget-button');
    const tabButtons = $('.tab-btn');
    const tabPanes = $('.tab-pane');
    const quickReplyItems = $('.quick-reply-item');
    const faqQuestions = $('.faq-question');
    const feedbackYes = $('#feedback-yes');
    const feedbackNo = $('#feedback-no');
    const voiceButton = $('#voice-btn');
    
    // State
    let isTyping = false;
    let chatHistory = [];
    let lastMessageTime = null;
    let messageIdCounter = 0;
    
    // Initialize
    initializeChatbot();
    
    // Functions
    function initializeChatbot() {
        console.log('Initializing chatbot...');
        
        // Set today's date
        const today = new Date();
        todayDateDisplay.text(formatDate(today));
        
        // Start real-time clock
        updateClock();
        setInterval(updateClock, 1000);
        
        // Show chatbot
        chatbotContainer.show();
        widgetButton.hide();
        
        // Set up event listeners
        setupEventListeners();
        
        // Initialize FAQ items
        initializeFAQ();
        
        // Show welcome message
        showWelcomeMessage();
        
        // Check API connection
        checkAPIConnection();
    }
    
    function setupEventListeners() {
        console.log('Setting up event listeners...');
        
        // Send button click
        sendButton.click(function() {
            console.log('Send button clicked');
            if (!isTyping) {
                sendUserMessage();
            }
        });
        
        // Enter key press
        userInput.keypress(function(e) {
            if (e.which === 13 && !isTyping) {
                sendUserMessage();
                e.preventDefault();
            }
        });
        
        // ✅ PERBAIKAN: Info button dengan ID yang benar
        infoButton.click(function() {
            console.log('Info button clicked'); // Debug log
            if ($('#info-popup').length > 0) {
                $('#info-popup').addClass('show');
            } else {
                showInfoPopup();
            }
        });
        
        // Info popup close button - menggunakan event delegation
        $(document).on('click', '#info-popup-close', function() {
            console.log('Info popup close clicked');
            $('#info-popup').removeClass('show');
            setTimeout(() => {
                $('#info-popup').remove(); // Hapus dari DOM setelah animasi
            }, 300);
        });
        
        // ✅ PERBAIKAN: Close popup ketika klik di luar area popup
        $(document).on('click', '#info-popup', function(e) {
            if (e.target === this) {
                $('#info-popup').removeClass('show');
                setTimeout(() => {
                    $('#info-popup').remove();
                }, 300);
            }
        });
        
        // Close button
        closeButton.click(function() {
            chatbotContainer.hide();
            widgetButton.show();
        });
        
        // Widget button click
        widgetButton.click(function() {
            widgetButton.hide();
            chatbotContainer.show();
        });
        
        // Clear button
        clearButton.click(function() {
            clearChat();
        });
        
        // Print button
        printButton.click(function() {
            printChat();
        });
        
        // Tab switching
        tabButtons.click(function() {
            switchTab($(this).data('tab'));
        });
        
        // Quick reply items
        quickReplyItems.click(function() {
            const question = $(this).text();
            userInput.val(question);
            sendUserMessage();
        });
        
        // FAQ questions - menggunakan event delegation untuk dynamic content
        $(document).on('click', '.faq-question', function() {
            const question = $(this).text();
            userInput.val(question);
            sendUserMessage();
        });
        
        // Feedback buttons
        feedbackYes.click(function() {
            provideFeedback('positive');
        });
        
        feedbackNo.click(function() {
            provideFeedback('negative');
        });
        
        // Voice button (if implemented)
        voiceButton.click(function() {
            startVoiceInput();
        });
        
        // ✅ PERBAIKAN: Debug - cek apakah event listener terpasang
        console.log('Info button element:', infoButton.length > 0 ? 'Found' : 'Not found');
    }
    
    function checkAPIConnection() {
        if (USE_MOCK_API) {
            console.log('Using mock API mode');
            return;
        }
        
        $.ajax({
            url: `${API_URL.replace('/api', '')}/health`,
            type: 'GET',
            timeout: 5000,
            success: function(response) {
                console.log('API connection successful:', response);
                if (response.chatbot_ready) {
                    console.log('Chatbot is ready');
                } else {
                    console.warn('Chatbot is not ready yet');
                }
            },
            error: function(xhr, status, error) {
                console.error('API connection failed:', error);
                showSystemMessage(' Koneksi ke server terputus. Menggunakan mode offline.', 'warning');
            }
        });
    }
    
    function sendUserMessage() {
        const message = userInput.val().trim();
        
        if (message === '' || isTyping) {
            return;
        }
        
        // Add user message to chat
        addMessage(message, 'user');
        
        // Clear input
        userInput.val('');
        
        // Show typing indicator
        showTypingIndicator();
        
        // Send to chatbot
        if (USE_MOCK_API) {
            // Mock response for demo
            setTimeout(() => {
                hideTypingIndicator();
                const mockResponse = getMockResponse(message);
                addMessage(mockResponse.message, 'bot', mockResponse.category, mockResponse.confidence);
            }, 1000 + Math.random() * 2000);
        } else {
            // Send to real API
            sendToAPI(message);
        }
    }
    
    function sendToAPI(message) {
        $.ajax({
            url: `${API_URL}/chat`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                message: message
            }),
            timeout: 10000,
            success: function(response) {
                console.log('API Response:', response);
                hideTypingIndicator();
                
                if (response.status === 'success') {
                    addMessage(
                        response.message, 
                        'bot', 
                        response.category, 
                        response.confidence,
                        {
                            responseTime: response.response_time,
                            timestamp: response.timestamp
                        }
                    );
                } else {
                    addMessage('Maaf, terjadi kesalahan. Silakan coba lagi.', 'bot', 'Error', 0);
                }
            },
            error: function(xhr, status, error) {
                console.error('API Error:', error);
                hideTypingIndicator();
                
                let errorMessage = 'Maaf, tidak dapat terhubung ke server.';
                if (status === 'timeout') {
                    errorMessage = 'Koneksi timeout. Silakan coba lagi.';
                } else if (xhr.status === 503) {
                    errorMessage = 'Server sedang tidak tersedia. Silakan coba lagi nanti.';
                }
                
                addMessage(errorMessage, 'bot', 'Error', 0);
            }
        });
    }
    
    function addMessage(content, sender, category = '', confidence = 0, metadata = {}) {
        const messageId = ++messageIdCounter;
        const timestamp = new Date();
        const timeString = timestamp.toLocaleTimeString('id-ID', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        const messageData = {
            id: messageId,
            content: content,
            sender: sender,
            category: category,
            confidence: confidence,
            timestamp: timestamp,
            metadata: metadata
        };
        
        chatHistory.push(messageData);
        
        const messageClass = sender === 'user' ? 'user-message' : 'bot-message';
        const avatar = sender === 'user' ? USER_AVATAR : BOT_AVATAR;
        
        let confidenceHtml = '';
        if (sender === 'bot' && confidence > 0) {
            const confidencePercent = Math.round(confidence * 100);
            const confidenceColor = confidence >= 0.7 ? '#28a745' : confidence >= 0.5 ? '#ffc107' : '#dc3545';
            confidenceHtml = `
                <div class="message-confidence" style="color: ${confidenceColor}; font-size: 0.7em; margin-top: 4px;">
                    <i class="fas fa-chart-line"></i> ${confidencePercent}%
                    ${category ? `• ${category}` : ''}
                </div>
            `;
        }
        
        let metadataHtml = '';
        if (metadata.responseTime) {
            metadataHtml = `
                <div class="message-metadata" style="color: #666; font-size: 0.6em; margin-top: 2px;">
                    Response time: ${metadata.responseTime}s
                </div>
            `;
        }
        
        const messageHtml = `
            <div class="message ${messageClass}" data-message-id="${messageId}">
                <div class="message-avatar">${avatar}</div>
                <div class="message-content">
                    <div class="message-text">${content}</div>
                    ${confidenceHtml}
                    ${metadataHtml}
                    <div class="message-time">${timeString}</div>
                </div>
            </div>
        `;
        
        chatMessages.append(messageHtml);
        scrollToBottom();
        
        lastMessageTime = timestamp;
        
        // Auto-scroll and focus
        setTimeout(() => {
            userInput.focus();
        }, 100);
    }
    
    function showTypingIndicator() {
        isTyping = true;
        sendButton.prop('disabled', true);
        userInput.prop('disabled', true);
        
        const typingHtml = `
            <div class="message bot-message typing-indicator" id="typing-indicator">
                <div class="message-avatar">${BOT_AVATAR}</div>
                <div class="message-content">
                    <div class="typing-animation">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        `;
        
        chatMessages.append(typingHtml);
        scrollToBottom();
    }
    
    function hideTypingIndicator() {
        isTyping = false;
        sendButton.prop('disabled', false);
        userInput.prop('disabled', false);
        $('#typing-indicator').remove();
    }
    
    function showWelcomeMessage() {
        setTimeout(() => {
            addMessage(
                'Halo! Saya adalah Asisten Virtual UPA TIK UNJA. Silakan tanyakan apa saja tentang layanan teknologi informasi universitas. 😊',
                'bot',
                'Greeting',
                1.0
            );
        }, 500);
    }
    
    function showSystemMessage(message, type = 'info') {
        const typeIcons = {
            'info': 'fas fa-info-circle',
            'warning': 'fas fa-exclamation-triangle',
            'error': 'fas fa-times-circle',
            'success': 'fas fa-check-circle'
        };
        
        const typeColors = {
            'info': '#17a2b8',
            'warning': '#ffc107',
            'error': '#dc3545',
            'success': '#28a745'
        };
        
        const icon = typeIcons[type] || typeIcons.info;
        const color = typeColors[type] || typeColors.info;
        
        const systemMessageHtml = `
            <div class="system-message" style="text-align: center; margin: 10px 0; color: ${color};">
                <i class="${icon}"></i> ${message}
            </div>
        `;
        
        chatMessages.append(systemMessageHtml);
        scrollToBottom();
    }
    
    function getMockResponse(message) {
        // Simple mock responses for demo
        const responses = {
            'password': {
                message: 'Untuk reset password SIAKAD, silakan hubungi helpdesk LPTIK di (0741) 583111 atau email ke helpdesk.lptik@unja.ac.id',
                category: 'Akademik',
                confidence: 0.95
            },
            'elearning': {
                message: 'Password elearning sama dengan password SIAKAD. Jika lupa, silakan hubungi helpdesk LPTIK.',
                category: 'Akademik', 
                confidence: 0.88
            },
            'beasiswa': {
                message: 'Informasi beasiswa dapat dilihat di website resmi UNJA atau hubungi bagian kemahasiswaan.',
                category: 'Beasiswa',
                confidence: 0.82
            },
            'default': {
                message: 'Maaf, saya belum memahami pertanyaan Kamu. Silakan hubungi helpdesk UPA TIK di (0741) 583111.',
                category: 'Unknown',
                confidence: 0.3
            }
        };
        
        const lowerMessage = message.toLowerCase();
        
        for (const key in responses) {
            if (key !== 'default' && lowerMessage.includes(key)) {
                return responses[key];
            }
        }
        
        return responses.default;
    }
    
    function initializeFAQ() {
        // Sample FAQ items - dapat disesuaikan dengan kebutuhan
        const faqItems = [
            'Lupa password SIAKAD',
            'Cara mengakses elearning',
            'Informasi beasiswa',
            'Koneksi internet kampus',
            'Bantuan teknis komputer'
        ];
        
        // Populate FAQ if container exists
        const faqContainer = $('#faq-list');
        if (faqContainer.length > 0) {
            faqContainer.empty();
            faqItems.forEach(item => {
                faqContainer.append(`
                    <div class="faq-question" style="cursor: pointer; padding: 8px; margin: 4px 0; background: #f8f9fa; border-radius: 4px;">
                        <i class="fas fa-question-circle"></i> ${item}
                    </div>
                `);
            });
        }
    }
    
    function scrollToBottom() {
        chatMessages.scrollTop(chatMessages[0].scrollHeight);
    }
    
    function updateClock() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('id-ID', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        if (currentTimeDisplay.length > 0) {
            currentTimeDisplay.text(timeString);
        }
    }
    
    function formatDate(date) {
        return date.toLocaleDateString('id-ID', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }
    
    function clearChat() {
        if (confirm('Yakin ingin menghapus semua percakapan?')) {
            chatMessages.empty();
            chatHistory = [];
            
            // Re-add date separator
            const today = new Date();
            chatMessages.append(`
                <div class="chat-date-separator">
                    <span id="today-date">${formatDate(today)}</span>
                </div>
            `);
            
            showWelcomeMessage();
        }
    }
    
    function printChat() {
        const printWindow = window.open('', '_blank');
        const chatContent = chatMessages.html();
        
        printWindow.document.write(`
            <html>
                <head>
                    <title>Chat History - UPA TIK UNJA</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; }
                        .message { margin: 10px 0; padding: 10px; border-radius: 8px; }
                        .user-message { background: #e3f2fd; text-align: right; }
                        .bot-message { background: #f5f5f5; }
                        .message-time { font-size: 0.8em; color: #666; margin-top: 5px; }
                    </style>
                </head>
                <body>
                    <h2>Chat History - UPA TIK UNJA</h2>
                    <p>Dicetak pada: ${new Date().toLocaleString('id-ID')}</p>
                    <hr>
                    ${chatContent}
                </body>
            </html>
        `);
        
        printWindow.document.close();
        printWindow.print();
    }
    
    function switchTab(tabName) {
        tabButtons.removeClass('active');
        tabPanes.removeClass('active');
        
        $(`.tab-btn[data-tab="${tabName}"]`).addClass('active');
        $(`#${tabName}-tab`).addClass('active');
    }
    
    function provideFeedback(type) {
        console.log(`Feedback provided: ${type}`);
        
        // Optional: Send feedback to server
        if (!USE_MOCK_API) {
            $.ajax({
                url: `${API_URL}/feedback`,
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    type: type,
                    message_id: messageIdCounter,
                    timestamp: new Date().toISOString()
                }),
                success: function(response) {
                    console.log('Feedback sent successfully');
                },
                error: function(error) {
                    console.error('Failed to send feedback:', error);
                }
            });
        }
        
        showSystemMessage(`Terima kasih atas feedbacknya! 👍`, 'success');
    }
    
    function startVoiceInput() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            showSystemMessage('Maaf, browser kamu tidak mendukung input suara. Silakan gunakan keyboard untuk mengetik pertanyaan kamu.', 'warning');
            return;
        }
        
        // Create speech recognition instance
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        
        // Configure
        recognition.lang = 'id-ID';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        
        // Visual feedback
        voiceButton.addClass('listening');
        voiceButton.html('<i class="fas fa-microphone-alt"></i>');
        showSystemMessage('Silakan bicara... (klik mikrofon lagi untuk berhenti)', 'info');
        
        // Start listening
        recognition.start();

        // Handle results
        recognition.onresult = function(event) {
            const speechResult = event.results[0][0].transcript;
            userInput.val(speechResult);
            sendUserMessage();
        };
        
        // Handle end
        recognition.onend = function() {
            voiceButton.removeClass('listening');
            voiceButton.html('<i class="fas fa-microphone"></i>');
        };
        
        // Handle error
        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
            voiceButton.removeClass('listening');
            voiceButton.html('<i class="fas fa-microphone"></i>');
            showSystemMessage('Maaf, terjadi kesalahan pada input suara. Silakan coba lagi atau gunakan keyboard.', 'error');
        };
        
        // Handle click to stop
        voiceButton.one('click', function() {
            recognition.stop();
        });
    }
    
    // ✅ PERBAIKAN: Fungsi popup yang lebih robust
    function showInfoPopup() {
        console.log('Showing info popup...');
        
        // Hapus popup yang sudah ada jika ada
        $('#info-popup').remove();
        
        const popupHtml = `
            <div id="info-popup" class="popup-overlay">
                <div class="popup-content">
                    <div class="popup-header">
                        <h3><i class="fas fa-robot"></i> Tentang Chatbot UPA TIK</h3>
                        <button id="info-popup-close" class="popup-close">&times;</button>
                    </div>
                    <div class="popup-body">
                        <div class="info-section">
                            <h4><i class="fas fa-info-circle"></i> Informasi Sistem</h4>
                            <p><strong>Chatbot UPA TIK UNJA</strong> adalah asisten virtual yang dikembangkan untuk membantu kamu mendapatkan informasi tentang layanan teknologi informasi Universitas Jambi dengan cepat dan akurat.</p>
                        </div>
                        
                        <div class="info-section">
                            <h4><i class="fas fa-cogs"></i> Teknologi</h4>
                            <p>Menggunakan teknologi Natural Language Processing (NLP) modern yaitu SBERT(Sentence Bert) sebagai telinga dan otak chatbot dengan metode Cosine Similarity untuk pencocokan pertanyaan yang akurat sebagai penggaris ajaib.</p>
                        </div>
                        
                        <div class="info-section">
                            <h4><i class="fas fa-headset"></i> Kontak Helpdesk</h4>
                            <div class="contact-info">
                                <p><i class="fas fa-phone"></i> <strong>Whatsapp:</strong> 0851-2488-9516</p>
                                <p><i class="fas fa-envelope"></i> <strong>Email:</strong> helpdesk.lptik@unja.ac.id</p>
                                <p><i class="fas fa-globe"></i> <strong>Website:</strong> abcd.unja.ac.id</p>
                                <p><i class="fas fa-clock"></i> <strong>Jam Layanan:</strong> 08:00 - 16:00 WIB</p>
                            </div>
                        </div>
                        
                        <div class="info-section">
                            <h4><i class="fas fa-question-circle"></i> Layanan Yang Tersedia</h4>
                            <ul class="service-list">
                                <li>Reset password SIAKAD</li>
                                <li>Bantuan akses e-learning</li>
                                <li>Informasi sistem akademik</li>
                                <li>Panduan penggunaan aplikasi kampus</li>
                                <li>Bantuan prosedur-prosedur di unja dan lainnya</li>
                            </ul>
                        </div>
                        
                        <div class="info-section">
                            <h4><i class="fas fa-code"></i> Informasi Versi</h4>
                            <p><strong>Versi:</strong> 2.0.0</p>
                            <p><strong>Terakhir Diperbarui:</strong> Juli 2025</p>
                            <p><strong>Dikembangkan oleh:</strong> Rahul Marcellino Holis</p>
                        </div>
                    </div>
                    <div class="popup-footer">
                        <button id="info-popup-ok" class="popup-button">Mengerti</button>
                    </div>
                </div>
            </div>
        `;
        
        // Tambahkan CSS untuk popup jika belum ada
        if ($('#popup-styles').length === 0) {
            $('head').append(`
                <style id="popup-styles">
                    .popup-overlay {
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(0, 0, 0, 0.5);
                        z-index: 10000;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        opacity: 0;
                        transition: opacity 0.3s ease;
                    }
                    .popup-overlay.show {
                        opacity: 1;
                    }
                    .popup-content {
                        background: white;
                        border-radius: 12px;
                        max-width: 500px;
                        max-height: 80vh;
                        width: 90%;
                        overflow: hidden;
                        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                        transform: scale(0.9);
                        transition: transform 0.3s ease;
                    }
                    .popup-overlay.show .popup-content {
                        transform: scale(1);
                    }
                    .popup-header {
                        background: #ff9d00ff;
                        color: white;
                        padding: 20px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }
                    .popup-header h3 {
                        margin: 0;
                        font-size: 1.2em;
                    }
                    .popup-close {
                        background: none;
                        border: none;
                        color: white;
                        font-size: 24px;
                        cursor: pointer;
                        padding: 0;
                        width: 30px;
                        height: 30px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        border-radius: 50%;
                        transition: background 0.3s ease;
                    }
                    .popup-close:hover {
                        background: rgba(255, 255, 255, 0.2);
                    }
                    .popup-body {
                        padding: 20px;
                        max-height: 60vh;
                        overflow-y: auto;
                    }
                    .info-section {
                        margin-bottom: 20px;
                    }
                    .info-section h4 {
                        color: #ff8000ff;
                        margin: 0 0 10px 0;
                        font-size: 1em;
                    }
                    .info-section p {
                        margin: 8px 0;
                        line-height: 1.5;
                    }
                    .contact-info p {
                        margin: 6px 0;
                    }
                    .service-list {
                        margin: 8px 0;
                        padding-left: 20px;
                    }
                    .service-list li {
                        margin: 4px 0;
                    }
                    .popup-footer {
                        padding: 15px 20px;
                        border-top: 1px solid #eee;
                        text-align: right;
                    }
                    .popup-button {
                        background: #f28500ff;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 6px;
                        cursor: pointer;
                        font-size: 14px;
                        transition: background 0.3s ease;
                    }
                    .popup-button:hover {
                        background: #fa931eff;
                    }
                </style>
            `);
        }
        
        // Tambahkan popup ke DOM
        $('body').append(popupHtml);
        
        // Show dengan animasi
        setTimeout(() => {
            $('#info-popup').addClass('show');
        }, 10);
        
        // Event listener untuk tombol OK
        $('#info-popup-ok').click(function() {
            $('#info-popup').removeClass('show');
            setTimeout(() => {
                $('#info-popup').remove();
            }, 300);
        });
    }
    
    // Expose functions for external use if needed
    window.chatbotAPI = {
        sendMessage: sendUserMessage,
        clearChat: clearChat,
        showInfo: showInfoPopup, // ✅ TAMBAHAN: Expose function info popup
        toggleWidget: function() {
            if (chatbotContainer.is(':visible')) {
                closeButton.click();
            } else {
                widgetButton.click();
            }
        }
    };
});