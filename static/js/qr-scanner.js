// QR Scanner Module

class QRScanner {
    constructor(options = {}) {
        this.video = document.getElementById(options.videoId || 'qr-video');
        this.canvas = document.getElementById(options.canvasId || 'qr-canvas');
        this.output = document.getElementById(options.outputId || 'qr-output');
        this.scanRegion = document.getElementById(options.scanRegionId || 'scan-region');
        
        this.stream = null;
        this.scanning = false;
        this.onScan = options.onScan || this.defaultOnScan;
        this.onError = options.onError || this.defaultOnError;
        
        this.init();
    }
    
    init() {
        if (!this.video || !this.canvas) {
            console.error('Required elements not found');
            return;
        }
        
        this.context = this.canvas.getContext('2d');
        this.canvas.width = 300;
        this.canvas.height = 300;
    }
    
    async start() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment' }
            });
            
            this.video.srcObject = this.stream;
            this.video.play();
            
            this.scanning = true;
            this.scan();
            
            if (this.scanRegion) {
                this.scanRegion.classList.add('active');
            }
            
        } catch (error) {
            this.onError(error);
        }
    }
    
    stop() {
        this.scanning = false;
        
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.video.srcObject = null;
        }
        
        if (this.scanRegion) {
            this.scanRegion.classList.remove('active');
        }
    }
    
    scan() {
        if (!this.scanning) return;
        
        if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
            this.context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
            const imageData = this.context.getImageData(0, 0, this.canvas.width, this.canvas.height);
            
            // Simulate QR detection (in real app, use a QR library)
            this.detectQR(imageData);
        }
        
        requestAnimationFrame(() => this.scan());
    }
    
    detectQR(imageData) {
        // This is a simulation - in production, use a proper QR library like jsQR
        // For demo purposes, we'll randomly "detect" QR codes
        if (Math.random() > 0.99) {
            const mockQRData = `PASS:${Math.floor(Math.random() * 10000)}:USER:${Math.floor(Math.random() * 1000)}:VALID:2024-12-31`;
            this.onScan(mockQRData);
        }
    }
    
    defaultOnScan(data) {
        console.log('QR Code detected:', data);
        if (this.output) {
            this.output.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>
                    QR Code detected: ${data}
                </div>
            `;
        }
    }
    
    defaultOnError(error) {
        console.error('Scanner error:', error);
        if (this.output) {
            this.output.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    Error accessing camera: ${error.message}
                </div>
            `;
        }
    }
    
    captureImage() {
        this.context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        return this.canvas.toDataURL('image/png');
    }
    
    toggleTorch() {
        if (!this.stream) return;
        
        const track = this.stream.getVideoTracks()[0];
        const capabilities = track.getCapabilities();
        
        if (capabilities.torch) {
            track.applyConstraints({
                advanced: [{ torch: !track.getSettings().torch }]
            }).catch(error => {
                console.error('Torch error:', error);
            });
        }
    }
}

// Initialize scanner when page loads
document.addEventListener('DOMContentLoaded', function() {
    const startBtn = document.getElementById('startScanner');
    const stopBtn = document.getElementById('stopScanner');
    
    if (startBtn) {
        const scanner = new QRScanner({
            onScan: (data) => {
                console.log('Scanned:', data);
                verifyQRCode(data);
            }
        });
        
        startBtn.addEventListener('click', () => scanner.start());
        stopBtn.addEventListener('click', () => scanner.stop());
    }
});

// Verify QR code with server
async function verifyQRCode(qrData) {
    try {
        const response = await fetch('/verify-qr', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ qr_data: qrData })
        });
        
        const result = await response.json();
        
        if (result.valid) {
            showToast(`Valid pass for ${result.user}`, 'success');
        } else {
            showToast(result.message, 'danger');
        }
        
    } catch (error) {
        console.error('Verification error:', error);
        showToast('Error verifying QR code', 'danger');
    }
}

function showToast(message, type) {
    // Use the toast function from main.js
    if (window.showToast) {
        window.showToast(message, type);
    } else {
        alert(message);
    }
}