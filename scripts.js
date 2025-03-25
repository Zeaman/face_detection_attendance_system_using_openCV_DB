document.addEventListener('DOMContentLoaded', function() {
    const webcamImg = document.getElementById('webcamFeed');
    const canvas = document.getElementById('detectionCanvas');
    const ctx = canvas.getContext('2d');
    const statusElement = document.getElementById('attendanceStatus');
    const faceCountElement = document.getElementById('faceCount');
    const lastDetectionElement = document.getElementById('lastDetection');
    const attendanceTable = document.querySelector('#attendanceTable tbody');
    
    // Set canvas size to match video feed
    function resizeCanvas() {
        canvas.width = webcamImg.clientWidth;
        canvas.height = webcamImg.clientHeight;
    }
    
    // Initialize
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    updateStatus();
    refreshAttendance();
    
    // Update status every second
    setInterval(updateStatus, 1000);
    
    function updateStatus() {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                // Update status display
                statusElement.innerHTML = data.status;
                
                // Update detection info
                faceCountElement.textContent = data.count;
                lastDetectionElement.textContent = new Date().toLocaleTimeString();
                
                // Draw bounding boxes
                drawDetections(data.faces);
                
                // Update status class
                if (data.status.includes("Approved")) {
                    statusElement.className = "attendance-status status-approved";
                } else if (data.status.includes("Low Confidence")) {
                    statusElement.className = "attendance-status status-rejected";
                } else {
                    statusElement.className = "attendance-status";
                }
            })
            .catch(error => {
                console.error('Status update error:', error);
            });
    }
    
    function drawDetections(faces) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        faces.forEach(face => {
            const [x, y, w, h] = face.bbox;
            ctx.strokeStyle = face.confidence >= 0.7 ? '#27ae60' : '#e74c3c';
            ctx.lineWidth = 2;
            ctx.strokeRect(x, y, w, h);
            
            ctx.fillStyle = face.confidence >= 0.7 ? '#27ae60' : '#e74c3c';
            ctx.font = '14px Arial';
            ctx.fillText(
                `${Math.round(face.confidence * 100)}%`, 
                x + 5, 
                y - 5
            );
        });
    }
    
    function refreshAttendance() {
        fetch('/api/attendance')
            .then(response => response.json())
            .then(data => {
                attendanceTable.innerHTML = '';
                
                data.attendance.forEach(record => {
                    const row = document.createElement('tr');
                    
                    const statusClass = record.status === 'Approved' ? 
                        'status-approved' : 
                        (record.status === 'Pending' ? 'status-pending' : 'status-rejected');
                    
                    row.innerHTML = `
                        <td>${record.user_id.substring(0, 8)}</td>
                        <td>${Math.round(record.confidence * 100)}%</td>
                        <td class="${statusClass}">${record.status}</td>
                        <td>${new Date(record.timestamp).toLocaleTimeString()}</td>
                    `;
                    attendanceTable.appendChild(row);
                });
            })
            .catch(error => {
                console.error('Attendance update error:', error);
            });
        
        // Refresh every 5 seconds
        setTimeout(refreshAttendance, 5000);
    }
});