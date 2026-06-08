/**
 * Floating Lines - Animated Canvas Background
 * A Vanilla JS implementation of the React "Floating Lines" component.
 */

class FloatingLines {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        
        // Configuration options
        this.options = {
            waveCount: 3,         // Top, Middle, Bottom layer logic
            lineSpacing: 15,      // Space between parallel lines
            baseSpeed: 0.001,     // Animation speed for sine waves
            waveAmplitude: 60,    // Height of the sine waves
            waveFrequency: 0.005, // Frequency of the sine waves
            interactive: true,
            bendRadius: 200,      // Mouse interaction radius
            bendStrength: 60,     // Max displacement amount
            colors: ['#3b82f6', '#8b5cf6', '#10b981'], // Colors for layers
            blendMode: 'screen',
            globalAlpha: 0.6
        };

        this.mouse = { x: -1000, y: -1000 };
        this.time = 0;
        this.layers = [];
        
        this.init();
        this.bindEvents();
        this.animate();
    }

    init() {
        this.resize();
        
        // Define layers (top, middle, bottom relative to center)
        this.layers = [
            { yOffset: -this.canvas.height * 0.15, color: this.options.colors[0], speed: 1.2, phase: 0 },
            { yOffset: 0, color: this.options.colors[1], speed: 0.8, phase: 2 },
            { yOffset: this.canvas.height * 0.15, color: this.options.colors[2], speed: 1.5, phase: 4 }
        ];
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    bindEvents() {
        window.addEventListener('resize', () => this.resize());
        
        if (this.options.interactive) {
            window.addEventListener('mousemove', (e) => {
                this.mouse.x = e.clientX;
                this.mouse.y = e.clientY;
            });
            window.addEventListener('mouseout', () => {
                this.mouse.x = -1000;
                this.mouse.y = -1000;
            });
        }
    }

    drawLayer(layer) {
        const { width, height } = this.canvas;
        const centerY = height / 2 + layer.yOffset;
        
        this.ctx.strokeStyle = layer.color;
        this.ctx.lineWidth = 1.5;
        this.ctx.globalAlpha = this.options.globalAlpha;
        this.ctx.globalCompositeOperation = this.options.blendMode;

        // Draw multiple parallel lines per layer
        for (let i = -3; i <= 3; i++) {
            this.ctx.beginPath();
            let isFirstPoint = true;
            
            for (let x = 0; x <= width; x += 10) {
                // Base sine wave calculation
                const wave1 = Math.sin(x * this.options.waveFrequency + this.time * layer.speed + layer.phase);
                const wave2 = Math.cos(x * this.options.waveFrequency * 0.5 - this.time * layer.speed * 0.8);
                let y = centerY + (wave1 + wave2) * this.options.waveAmplitude + (i * this.options.lineSpacing);

                // Mouse interaction (displacement)
                if (this.options.interactive) {
                    const dx = x - this.mouse.x;
                    const dy = y - this.mouse.y;
                    const distance = Math.sqrt(dx * dx + dy * dy);
                    
                    if (distance < this.options.bendRadius) {
                        // Calculate push effect (closer = stronger push)
                        const pushFactor = (this.options.bendRadius - distance) / this.options.bendRadius;
                        const pushY = (dy / distance) * pushFactor * this.options.bendStrength;
                        
                        // Apply displacement
                        y += pushY;
                    }
                }

                if (isFirstPoint) {
                    this.ctx.moveTo(x, y);
                    isFirstPoint = false;
                } else {
                    this.ctx.lineTo(x, y);
                }
            }
            this.ctx.stroke();
        }
    }

    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        this.time += this.options.baseSpeed;
        
        this.layers.forEach(layer => this.drawLayer(layer));
        
        requestAnimationFrame(() => this.animate());
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new FloatingLines('floating-lines-canvas');
});
