const USER_AVATAR = '<i class="fas fa-user"></i>';// frontend/js/chatbot.js

$(document).ready(function() {
    // Config
    // PERBAIKAN: Tambahkan opsi untuk mengaktifkan/menonaktifkan API (untuk demo tanpa backend)
    //const USE_MOCK_API = false; // Ubah ke false untuk connect ke backend asli
    const USE_MOCK_API = true; // Set ke true untuk demonstrasi tanpa backend
    //const API_URL = 'http://localhost:5000/api';
    //const API_URL = 'http://127.0.0.1:5000/api';
    //const API_URL = 'http://10.117.60.138:5000'; //harus sesuai api 
    
    // DOM Elements
    const chatMessages = $('#chat-messages');
    const userInput = $('#user-input');
    const sendButton = $('#send-btn');
    const infoButton = $('#info-btn');
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
    
    // Initialize
    initializeChatbot();
    
    // Functions
    function initializeChatbot() {
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
    }
    
    function setupEventListeners() {
        // Send button click
        sendButton.click(function() {
            sendUserMessage();
        });
        
        // Enter key press
        userInput.keypress(function(e) {
            if (e.which === 13) {
                sendUserMessage();
                e.preventDefault();
            }
        });
        
        // Info button - PERBAIKAN: Gunakan popup khusus sebagai popup informasi
        infoButton.click(function() {
            $('#info-popup').addClass('show');
        });
        
        // Info popup close button
        $('#info-popup-close').click(function() {
            $('#info-popup').removeClass('show');
        });
        
        // Minimize function now handled by close button
        closeButton.click(function() {
            chatbotContainer.hide();
            widgetButton.show();
        });
        
        // Widget button (maximize)
        widgetButton.click(function() {
            chatbotContainer.show();
            widgetButton.hide();
        });
        
        // Function sudah diubah di atas (Close button sekarang berfungsi sebagai minimize)
        
        // Clear chat button
        clearButton.click(function() {
            clearChat();
        });
        
        // Print button
        printButton.click(function() {
            printChat();
        });
        
        // Tab navigation
        tabButtons.click(function() {
            const tabId = $(this).data('tab');
            switchTab(tabId);
        });
        
        // Quick reply items
        quickReplyItems.click(function() {
            const replyText = $(this).text();
            userInput.val(replyText);
            sendUserMessage();
        });
        
        // FAQ questions
        faqQuestions.click(function() {
            const faqItem = $(this).parent();
            toggleFAQItem(faqItem);
        });
        
        // Feedback buttons
        feedbackYes.click(function() {
            sendFeedback(true);
        });
        
        feedbackNo.click(function() {
            sendFeedback(false);
        });
        
        // Voice input
        voiceButton.click(function() {
            startVoiceInput();
        });
    }
    
    function updateClock() {
        const now = new Date();
        const timeString = formatTime(now, true); // with seconds
        currentTimeDisplay.text(timeString);
    }
    
    function formatTime(date, showSeconds = false) {
        let hours = date.getHours();
        let minutes = date.getMinutes();
        let seconds = date.getSeconds();
        
        // Add leading zeros
        hours = hours < 10 ? '0' + hours : hours;
        minutes = minutes < 10 ? '0' + minutes : minutes;
        seconds = seconds < 10 ? '0' + seconds : seconds;
        
        return showSeconds ? `${hours}:${minutes}:${seconds}` : `${hours}:${minutes}`;
    }
    
    function formatDate(date) {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        return date.toLocaleDateString('id-ID', options);
    }
    
    function sendUserMessage() {
        const message = userInput.val().trim();
        if (!message) return;
        
        // Add to chat
        appendMessage(message, true);
        
        // Clear input
        userInput.val('');
        
        // Add to history
        addToHistory(message, true);
        
        // Send to API and get response
        sendToAPI(message);
    }
    
    function appendMessage(message, isUser = false) {
        const now = new Date();
        
        // Check if we need a new date separator
        if (!lastMessageTime || !isSameDay(lastMessageTime, now)) {
            appendDateSeparator(now);
        }
        
        lastMessageTime = now;
        
        const time = formatTime(now);
        const sender = isUser ? 'Anda' : 'UNJA Helpdesk';
        const avatar = isUser ? USER_AVATAR : '<img src="/assets/Logo Universitas Jambi (Unja).png" alt="UNJA Bot">';
        const messageClass = isUser ? 'user-message' : 'bot-message';
        
        const messageHtml = `
            <div class="message ${messageClass}">
                <div class="message-avatar">
                    ${avatar}
                </div>
                <div class="message-bubble">
                    <div class="message-info">
                        <span class="message-sender">${sender}</span>
                        <span class="message-time">${time}</span>
                    </div>
                    <div class="message-content">${message}</div>
                </div>
            </div>
        `;
        
        chatMessages.append(messageHtml);
        scrollToBottom();
    }
    
    function appendDateSeparator(date) {
        const dateString = formatDate(date);
        const isToday = isSameDay(date, new Date());
        const displayText = isToday ? 'Hari ini' : dateString;
        
        const separatorHtml = `
            <div class="chat-date-separator">
                <span>${displayText}</span>
            </div>
        `;
        
        chatMessages.append(separatorHtml);
    }
    
    function isSameDay(date1, date2) {
        return date1.getDate() === date2.getDate() &&
               date1.getMonth() === date2.getMonth() &&
               date1.getFullYear() === date2.getFullYear();
    }
    
    function showTypingIndicator() {
        if (isTyping) return;
        
        isTyping = true;
        
        const typingHtml = `
            <div class="message bot-message" id="typing-indicator">
                <div class="message-avatar">
                    <img src="/assets/Logo Universitas Jambi (Unja).png" alt="UNJA Bot">
                </div>
                <div class="message-bubble">
                    <div class="message-info">
                        <span class="message-sender">UNJA Helpdesk</span>
                        <span class="message-time">${formatTime(new Date())}</span>
                    </div>
                    <div class="typing-indicator">
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
        $('#typing-indicator').remove();
        isTyping = false;
    }
    
    function scrollToBottom() {
        chatMessages.scrollTop(chatMessages[0].scrollHeight);
    }
    
    function sendToAPI(message) {
        // Show typing indicator
        showTypingIndicator();
        
        // PERBAIKAN: Gunakan mode mock untuk demonstrasi jika backend tidak tersedia
        if (USE_MOCK_API) {
            console.log("Connecting to backend API...");
            
            // Simulate typing delay
            setTimeout(function() {
                // Hide typing indicator
                hideTypingIndicator();
                
                // Get mock response
                const mockResponse = getMockResponse(message);
                
                // Add bot response
                appendMessage(mockResponse);
                
                // Add to history
                addToHistory(mockResponse, false);
                
                // Add suggestions if relevant
                if (message.toLowerCase().includes('beasiswa')) {
                    appendSuggestions([
                        "Syarat beasiswa PPA",
                        "Beasiswa Bidikmisi",
                        "Jadwal seleksi beasiswa"
                    ]);
                }
            }, 1000);
            
            return;
        }
        
        // Jika menggunakan API real:
        console.log("Connecting to backend API...");
        
        // Simulate API call with delay
        setTimeout(function() {
            // Call the actual API
            $.ajax({
                url: `${API_URL}/chat`,
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ message: message }),
                success: function(response) {
                    console.log("API response received:", response);
                    
                    // Hide typing indicator
                    hideTypingIndicator();
                    
                    // Add bot response
                    appendMessage(response.answer);
                    
                    // Add to history
                    addToHistory(response.answer, false);
                    
                    // If there are suggested questions
                    if (response.similar_questions && response.similar_questions.length > 0) {
                        appendSuggestions(response.similar_questions);
                    }
                },
                error: function(xhr, status, error) {
                    console.error("API Error:", error);
                    console.error("Status:", status);
                    console.error("XHR:", xhr);
                    
                    // Hide typing indicator
                    hideTypingIndicator();
                    
                    // Check if it's a connection error
                    if (xhr.status === 0) {
                        appendMessage("Maaf, saya tidak dapat terhubung ke server backend. Beralih ke mode demo.", false);
                        
                        // Switch to mock mode for future requests
                        USE_MOCK_API = true;
                        
                        // Return mock response
                        setTimeout(function() {
                            const mockResponse = getMockResponse(message);
                            appendMessage(mockResponse);
                            addToHistory(mockResponse, false);
                        }, 1000);
                    } else {
                        // Other errors
                        appendMessage("Maaf, terjadi kesalahan dalam memproses permintaan Anda. Silakan coba lagi nanti.");
                    }
                }
            });
        }, 500);
    }
    
    function getMockResponse(message) {
        // PERBAIKAN: Respons yang lebih lengkap dan bervariasi untuk mode demo
        // Untuk demonstrasi purposes only
        
        const lowercaseMsg = message.toLowerCase();
        
        // Respons untuk pertanyaan tentang pendaftaran
        if (lowercaseMsg.includes('daftar') || lowercaseMsg.includes('registrasi') || lowercaseMsg.includes('pendaftaran')) {
            return `Untuk pendaftaran dan registrasi mahasiswa, silakan ikuti langkah berikut:
                <ol>
                    <li>Akses portal akademik Universitas Jambi di <strong>portal.unja.ac.id</strong></li>
                    <li>Login menggunakan NIM/username dan password yang telah diberikan</li>
                    <li>Pilih menu "Registrasi Semester" dan ikuti petunjuk yang tersedia</li>
                    <li>Lakukan pembayaran UKT melalui bank yang telah ditentukan</li>
                    <li>Unggah bukti pembayaran pada portal</li>
                    <li>Tunggu verifikasi dari bagian akademik</li>
                </ol>
                Jika mengalami kendala, silakan hubungi bagian akademik fakultas Anda atau kirim email ke akademik@unja.ac.id.`;
        } 
        // Respons untuk pertanyaan tentang beasiswa
        else if (lowercaseMsg.includes('beasiswa')) {
            return `Informasi beasiswa Universitas Jambi periode tahun 2025:
                <ul>
                    <li><strong>Beasiswa PPA:</strong> Dibuka setiap awal semester dengan syarat minimal IPK 3.25</li>
                    <li><strong>Beasiswa Bidikmisi:</strong> Untuk mahasiswa dengan keterbatasan ekonomi, pendaftaran via bidikmisi.belmawa.ristekdikti.go.id</li>
                    <li><strong>Beasiswa Bank Jambi:</strong> Kerja sama dengan pemerintah daerah, dibuka pada bulan April-Mei</li>
                </ul>
                Dokumen yang biasanya dibutuhkan: Surat keterangan tidak mampu, transkrip nilai, sertifikat prestasi, dan fotokopi KTP/KK.`;
        } 
        // Respons untuk pertanyaan tentang jadwal
        else if (lowercaseMsg.includes('jadwal') || lowercaseMsg.includes('uas') || lowercaseMsg.includes('ujian')) {
            return `Jadwal akademik semester genap tahun ajaran 2024/2025:
                <ul>
                    <li>UTS: 18 - 29 Maret 2025</li>
                    <li>UAS: 13 - 24 Juni 2025</li>
                    <li>Pengisian KRS: 10 - 21 Januari 2025</li>
                    <li>Pengumuman nilai: Maksimal 2 minggu setelah ujian</li>
                </ul>
                Untuk jadwal spesifik per fakultas/prodi, silakan kunjungi website fakultas masing-masing atau portal akademik.`;
        } 
        // Respons untuk pertanyaan tentang biaya
        else if (lowercaseMsg.includes('biaya') || lowercaseMsg.includes('ukt')) {
            return `Biaya UKT Universitas Jambi bervariasi berdasarkan program studi dan kelompok UKT:
                <ul>
                    <li>Kelompok I: Rp 0,- (Bidikmisi)</li>
                    <li>Kelompok II: Rp 1.000.000,- s/d Rp 2.000.000,-</li>
                    <li>Kelompok III: Rp 2.000.000,- s/d Rp 3.500.000,-</li>
                    <li>Kelompok IV: Rp 3.500.000,- s/d Rp 5.000.000,-</li>
                    <li>Kelompok V: Rp 5.000.000,- s/d Rp 7.500.000,-</li>
                </ul>
                Untuk informasi lengkap, silakan lihat di portal.unja.ac.id atau hubungi bagian keuangan universitas.`;
        }
        // Respons untuk salam atau ucapan
        else if (lowercaseMsg.includes('halo') || lowercaseMsg.includes('hi') || lowercaseMsg.includes('selamat')) {
            return `Halo! Selamat datang di Layanan Chatbot Helpdesk Universitas Jambi. Ada yang bisa saya bantu terkait informasi akademik, beasiswa, pendaftaran, atau layanan kampus lainnya?`;
        }
        // Respons untuk terima kasih
        else if (lowercaseMsg.includes('terima kasih') || lowercaseMsg.includes('makasih')) {
            return `Sama-sama! Senang bisa membantu. Jika ada pertanyaan lain, jangan ragu untuk bertanya kembali.`;
        }
        // Respons default
        else {
            return `Mohon maaf, saya belum memahami pertanyaan Anda. Silakan coba formulasikan kembali atau pilih topik berikut:
                <ul>
                    <li>Informasi pendaftaran dan registrasi</li>
                    <li>Jadwal akademik</li>
                    <li>Beasiswa dan keuangan</li>
                    <li>Administrasi kampus</li>
                </ul>
                Anda juga dapat menghubungi helpdesk@unja.ac.id untuk bantuan lebih lanjut.`;
        }
    }
    
    function appendSuggestions(suggestions) {
        const suggestionHtml = `
            <div class="message bot-message">
                <div class="message-avatar">
                    <img src="/assets/Logo Universitas Jambi (Unja).png" alt="UNJA Bot">
                </div>
                <div class="message-bubble">
                    <div class="message-info">
                        <span class="message-sender">UNJA Helpdesk</span>
                        <span class="message-time">${formatTime(new Date())}</span>
                    </div>
                    <div class="message-content">
                        Mungkin Anda juga ingin tahu:
                        <div class="suggestions">
                            ${suggestions.map(suggestion => 
                                `<div class="suggestion-chip">${suggestion}</div>`
                            ).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        chatMessages.append(suggestionHtml);
        scrollToBottom();
        
        // Add click handler to suggestions
        $('.suggestion-chip').click(function() {
            const text = $(this).text();
            userInput.val(text);
            sendUserMessage();
        });
    }
    
    function clearChat() {
        // Confirm before clearing
        if (confirm('Apakah Anda yakin ingin menghapus seluruh percakapan?')) {
            // Keep only the first welcome message
            const welcomeMessage = chatMessages.children().first();
            chatMessages.empty();
            chatMessages.append(welcomeMessage);
            
            // Reset history
            chatHistory = [];
            lastMessageTime = null;
            
            // Add today's date separator
            appendDateSeparator(new Date());
        }
    }
    
    function printChat() {
        // Create a new window for printing
        const printWindow = window.open('', '_blank');
        
        // Generate print-friendly content
        let printContent = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Riwayat Percakapan UNJA Helpdesk</title>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }
                    .header { text-align: center; margin-bottom: 20px; }
                    .logo { max-width: 80px; }
                    .chat-item { margin-bottom: 10px; padding: 10px; border-radius: 5px; }
                    .user { background-color: #f0f0f0; text-align: right; }
                    .bot { background-color: #fff8e6; }
                    .time { font-size: 12px; color: #666; }
                    .date-separator { text-align: center; margin: 15px 0; position: relative; }
                    .date-separator:after { content: ''; display: block; border-bottom: 1px solid #ddd; position: absolute; top: 50%; width: 100%; z-index: -1; }
                    .date-text { background: white; padding: 0 10px; display: inline-block; font-weight: bold; }
                    @media print {
                        .no-print { display: none; }
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <img src="/assets/Logo Universitas Jambi (Unja).png" alt="UNJA Logo" class="logo">
                    <h1>Riwayat Percakapan UNJA Helpdesk</h1>
                    <p>Dicetak pada: ${new Date().toLocaleString('id-ID')}</p>
                </div>
                <div class="no-print">
                    <button onclick="window.print()">Cetak</button>
                    <button onclick="window.close()">Tutup</button>
                </div>
                <div id="chat-history">
        `;
        
        // Process chat history
        let currentDate = null;
        
        for (const item of chatHistory) {
            const msgDate = new Date(item.timestamp);
            const dateString = formatDate(msgDate);
            
            // Add date separator if needed
            if (currentDate !== dateString) {
                printContent += `
                    <div class="date-separator">
                        <span class="date-text">${dateString}</span>
                    </div>
                `;
                currentDate = dateString;
            }
            
            // Add message
            printContent += `
                <div class="chat-item ${item.isUser ? 'user' : 'bot'}">
                    <div class="time">${formatTime(msgDate)}</div>
                    <div>${item.isUser ? 'Anda' : 'UNJA Helpdesk'}: ${item.message}</div>
                </div>
            `;
        }
        
        printContent += `
                </div>
                <div class="footer">
                    <p>© ${new Date().getFullYear()} Universitas Jambi - Helpdesk System</p>
                </div>
            </body>
            </html>
        `;
        
        // Write to new window and trigger print
        printWindow.document.open();
        printWindow.document.write(printContent);
        printWindow.document.close();
        
        // Wait for content to load then print
        printWindow.onload = function() {
            printWindow.focus();
            printWindow.print();
        };
    }
    
    function addToHistory(message, isUser) {
        chatHistory.push({
            message: message,
            isUser: isUser,
            timestamp: new Date()
        });
    }
    
    function switchTab(tabId) {
        // Remove active class from all tabs
        tabButtons.removeClass('active');
        tabPanes.removeClass('active');
        
        // Add active class to selected tab
        $(`.tab-btn[data-tab="${tabId}"]`).addClass('active');
        $(`#${tabId}-tab`).addClass('active');
    }
    
    function initializeFAQ() {
        // Add click handlers to FAQ items
        faqQuestions.click(function() {
            const faqItem = $(this).parent();
            toggleFAQItem(faqItem);
        });
    }
    
    function toggleFAQItem(faqItem) {
        // Close other open FAQ items
        $('.faq-item.active').not(faqItem).removeClass('active');
        
        // Toggle current item
        faqItem.toggleClass('active');
    }
    
    function sendFeedback(isHelpful) {
        // Visual feedback
        if (isHelpful) {
            feedbackYes.css('transform', 'scale(1.2)');
            setTimeout(() => feedbackYes.css('transform', 'scale(1)'), 300);
        } else {
            feedbackNo.css('transform', 'scale(1.2)');
            setTimeout(() => feedbackNo.css('transform', 'scale(1)'), 300);
        }
        
        // Get the last message exchange
        let userQuestion = '';
        let botAnswer = '';
        
        if (chatHistory.length >= 2) {
            // Find the last user message
            for (let i = chatHistory.length - 1; i >= 0; i--) {
                if (chatHistory[i].isUser) {
                    userQuestion = chatHistory[i].message;
                    break;
                }
            }
            
            // Find the last bot message
            for (let i = chatHistory.length - 1; i >= 0; i--) {
                if (!chatHistory[i].isUser) {
                    botAnswer = chatHistory[i].message;
                    break;
                }
            }
        }
        
        // Prepare feedback data
        const feedbackData = {
            question: userQuestion,
            answer: botAnswer,
            helpful: isHelpful,
            timestamp: new Date().toISOString()
        };
        
        // Send to API
        $.ajax({
            url: `${API_URL}/feedback`,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(feedbackData),
            success: function(response) {
                // Show thank you message
                appendMessage('Terima kasih atas feedback Anda! Ini membantu kami meningkatkan layanan chatbot.');
                
                // If not helpful, suggest contacting helpdesk
                if (!isHelpful) {
                    setTimeout(() => {
                        appendMessage('Jika Anda membutuhkan bantuan lebih lanjut, silakan hubungi Helpdesk Universitas Jambi di helpdesk@unja.ac.id atau kunjungi kantor kami di Gedung Rektorat lantai 1.');
                    }, 1000);
                }
            },
            error: function(xhr, status, error) {
                console.error('Error sending feedback:', error);
                
                // Still show thank you message
                appendMessage('Terima kasih atas feedback Anda!');
            }
        });
    }
    
    function startVoiceInput() {
        // Check if browser supports speech recognition
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            appendMessage('Maaf, browser Anda tidak mendukung input suara. Silakan gunakan keyboard untuk mengetik pertanyaan Anda.');
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
        appendMessage('Silakan bicara... (klik mikrofon lagi untuk berhenti)');
        
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
            appendMessage('Maaf, terjadi kesalahan pada input suara. Silakan coba lagi atau gunakan keyboard.');
        };
        
        // Handle click to stop
        voiceButton.one('click', function() {
            recognition.stop();
        });
    }
});