document.addEventListener('DOMContentLoaded', () => {
    // Theme Toggle Logic
    const themeSwitch = document.getElementById('theme-switch');
    const htmlElement = document.documentElement;
    const themeLabel = document.getElementById('theme-label');
    
    // Check local storage or system preference
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersLight = window.matchMedia('(prefers-color-scheme: light)').matches;
    
    const initialTheme = savedTheme || (systemPrefersLight ? 'light' : 'dark');
    setTheme(initialTheme);
    
    if (initialTheme === 'light') {
        themeSwitch.checked = true;
    }
    
    themeSwitch.addEventListener('change', (e) => {
        if (e.target.checked) {
            setTheme('light');
        } else {
            setTheme('dark');
        }
    });
    
    function setTheme(theme) {
        htmlElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        
        if (theme === 'light') {
            themeLabel.textContent = 'Light Mode';
        } else {
            themeLabel.textContent = 'Dark Mode';
        }
    }

    // Connect Wallet Button interaction
    const connectWalletBtn = document.getElementById('connect-wallet');
    if (connectWalletBtn) {
        connectWalletBtn.addEventListener('click', () => {
            connectWalletBtn.textContent = 'Connecting...';
            connectWalletBtn.style.opacity = '0.7';
            setTimeout(() => {
                connectWalletBtn.textContent = '0xAb5...8f2C';
                connectWalletBtn.style.opacity = '1';
                connectWalletBtn.classList.remove('btn-primary');
                connectWalletBtn.classList.add('btn-secondary');
            }, 1500);
        });
    }

    // Navigation logic for roles (REMOVED)    // 3D Interactive Canvas Mesh (Blockchain Network Simulation)
    initCanvasMesh();
});

function initCanvasMesh() {
    const canvas = document.getElementById('mesh-canvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    let width, height;
    let particles = [];
    
    const particleCount = 80;
    const connectionDistance = 150;
    const speed = 0.5;

    function resizeCanvas() {
        width = window.innerWidth;
        height = window.innerHeight;
        canvas.width = width;
        canvas.height = height;
    }

    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    class Particle {
        constructor() {
            this.x = Math.random() * width;
            this.y = Math.random() * height;
            this.z = Math.random() * 2 + 0.1; // Pseudo 3D depth
            
            const angle = Math.random() * Math.PI * 2;
            this.vx = Math.cos(angle) * speed;
            this.vy = Math.sin(angle) * speed;
            
            this.radius = this.z * 1.5;
        }

        update() {
            this.x += this.vx / this.z;
            this.y += this.vy / this.z;

            // Bounce off edges
            if (this.x < 0 || this.x > width) this.vx *= -1;
            if (this.y < 0 || this.y > height) this.vy *= -1;
        }

        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(0, 255, 204, 0.4)'; // neon mint
            ctx.fill();
        }
    }

    function createParticles() {
        particles = [];
        for (let i = 0; i < particleCount; i++) {
            particles.push(new Particle());
        }
    }

    function animate() {
        ctx.clearRect(0, 0, width, height);

        // Update and draw particles
        for (let i = 0; i < particles.length; i++) {
            particles[i].update();
            particles[i].draw();
            
            // Draw connections
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < connectionDistance) {
                    ctx.beginPath();
                    // Thicker lines for closer pseudo-3D
                    ctx.lineWidth = Math.max(0.2, 1 - (dist / connectionDistance)) * ((particles[i].z + particles[j].z) / 2);
                    
                    // The line color fades based on distance distance
                    const opacity = 1 - (dist / connectionDistance);
                    ctx.strokeStyle = `rgba(0, 102, 255, ${opacity * 0.5})`; // electric blue connection
                    
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.stroke();
                }
            }
        }

        requestAnimationFrame(animate);
    }

    createParticles();
    animate();
}
