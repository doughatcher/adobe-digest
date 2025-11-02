/**
 * Starfield Animation - Late TNG/LCARS Edition
 * Creates an animated starfield background with nebula effects
 */

(function() {
  'use strict';

  // Configuration - LCARS inspired
  const config = {
    starCount: 300,
    starLayers: 3, // Multiple depth layers
    starSpeed: {
      slow: 0.2,
      medium: 0.5,
      fast: 1.2
    },
    starSize: {
      min: 0.5,
      max: 2.5
    },
    colors: {
      stars: [
        'rgba(255, 153, 102, 0.9)', // LCARS Peach
        'rgba(153, 153, 255, 0.8)', // Federation Blue
        'rgba(204, 153, 204, 0.8)', // Soft Purple
        'rgba(255, 204, 153, 0.9)', // Warm Coral
        'rgba(255, 255, 255, 0.7)'  // White
      ],
      starsLight: [
        'rgba(25, 70, 180, 0.9)',   // Deep cobalt
        'rgba(51, 102, 204, 0.85)', // Cobalt blue
        'rgba(70, 120, 220, 0.8)',  // Medium blue
        'rgba(40, 80, 160, 0.85)',  // Navy blue
        'rgba(60, 100, 200, 0.8)'   // Royal blue
      ],
      nebula: [
        'rgba(102, 51, 153, 0.15)', // Deep Purple
        'rgba(51, 102, 204, 0.12)', // Deep Blue
        'rgba(153, 51, 102, 0.10)'  // Deep Magenta
      ],
      nebulaLight: [
        'rgba(51, 102, 204, 0.25)',  // Cobalt blue nebula
        'rgba(70, 120, 220, 0.22)',  // Medium blue nebula
        'rgba(40, 80, 180, 0.20)'    // Deep blue nebula
      ]
    },
    streakCount: 2, // Fast-moving warp streaks (reduced)
    nebulaCount: 5
  };

  class Star {
    constructor(canvas, layer = 1) {
      this.canvas = canvas;
      this.layer = layer;
      this.speeds = [config.starSpeed.slow, config.starSpeed.medium, config.starSpeed.fast];
      this.speed = this.speeds[layer - 1];
      this.reset();
    }

    reset() {
      this.x = Math.random() * this.canvas.width;
      this.y = Math.random() * this.canvas.height;
      this.z = Math.random() * this.canvas.width;
      this.size = Math.random() * (config.starSize.max - config.starSize.min) + config.starSize.min;
      
      // Choose color based on light/dark mode
      const isLight = document.documentElement.classList.contains('light');
      const colorArray = isLight ? config.colors.starsLight : config.colors.stars;
      this.color = colorArray[Math.floor(Math.random() * colorArray.length)];
      
      this.brightness = Math.random() * 0.5 + 0.5;
      this.pulseSpeed = 0.02 + Math.random() * 0.03;
      this.pulseOffset = Math.random() * Math.PI * 2;
    }

    update() {
      this.z -= this.speed;
      
      if (this.z <= 0) {
        this.reset();
        this.z = this.canvas.width;
      }
      
      // Pulse effect
      this.pulseOffset += this.pulseSpeed;
    }

    draw(ctx) {
      const x = (this.x - this.canvas.width / 2) * (this.canvas.width / this.z);
      const y = (this.y - this.canvas.height / 2) * (this.canvas.width / this.z);
      const size = this.size * (this.canvas.width / this.z);
      
      const screenX = x + this.canvas.width / 2;
      const screenY = y + this.canvas.height / 2;

      if (screenX < 0 || screenX > this.canvas.width || 
          screenY < 0 || screenY > this.canvas.height) {
        return;
      }

      const depth = 1 - this.z / this.canvas.width;
      const pulse = 0.7 + Math.sin(this.pulseOffset) * 0.3;
      
      ctx.beginPath();
      ctx.fillStyle = this.color;
      ctx.globalAlpha = this.brightness * depth * pulse;
      ctx.arc(screenX, screenY, size, 0, Math.PI * 2);
      ctx.fill();
      
      // Add glow for brighter stars
      if (this.brightness > 0.7 && depth > 0.5) {
        ctx.globalAlpha = this.brightness * depth * pulse * 0.3;
        ctx.arc(screenX, screenY, size * 2, 0, Math.PI * 2);
        ctx.fill();
      }
      
      ctx.globalAlpha = 1;
    }
  }

  class WarpStreak {
    constructor(canvas) {
      this.canvas = canvas;
      this.reset();
    }

    reset() {
      // Start from edges at various positions
      const side = Math.random() > 0.5 ? 'left' : 'right';
      if (side === 'left') {
        this.x = -50;
        this.y = Math.random() * this.canvas.height;
      } else {
        this.x = this.canvas.width + 50;
        this.y = Math.random() * this.canvas.height;
        this.direction = -1;
      }
      
      this.z = Math.random() * this.canvas.width * 0.8 + this.canvas.width * 0.2; // Start further back
      this.speed = 3 + Math.random() * 2;
      this.baseLength = 60 + Math.random() * 100;
      this.opacity = 0.2 + Math.random() * 0.3; // More subtle
      this.color = config.colors.stars[Math.floor(Math.random() * config.colors.stars.length)];
      this.active = Math.random() > 0.99; // Much rarer
      this.curve = (Math.random() - 0.5) * 0.3; // Curve factor for trajectory
    }

    update() {
      if (this.active) {
        this.z -= this.speed;
        
        if (this.z <= 0) {
          this.reset();
        }
      } else if (Math.random() > 0.998) { // Even rarer activation
        this.active = true;
      }
    }

    draw(ctx) {
      if (!this.active) return;
      
      // Calculate 3D perspective position
      const centerX = this.canvas.width / 2;
      const centerY = this.canvas.height / 2;
      
      const scale = this.canvas.width / this.z;
      const perspectiveX = (this.x - centerX) * scale + centerX;
      const perspectiveY = (this.y - centerY) * scale + centerY;
      
      // Calculate trail with perspective
      const trailLength = this.baseLength * scale;
      const depth = 1 - this.z / this.canvas.width;
      
      // Apply curve to the streak based on position
      const curveOffset = this.curve * trailLength;
      
      // Start point (head of the streak)
      const headX = perspectiveX;
      const headY = perspectiveY;
      
      // End point (tail) - moves towards center with curve
      const tailZ = this.z + this.baseLength;
      const tailScale = this.canvas.width / tailZ;
      const tailX = (this.x - centerX) * tailScale + centerX;
      const tailY = (this.y - centerY + curveOffset) * tailScale + centerY;
      
      // Only draw if visible
      if (headX < -50 || headX > this.canvas.width + 50 ||
          headY < -50 || headY > this.canvas.height + 50) {
        return;
      }
      
      // Create gradient along the streak path
      const gradient = ctx.createLinearGradient(tailX, tailY, headX, headY);
      gradient.addColorStop(0, this.color.replace(/[\d.]+\)$/, '0)'));
      gradient.addColorStop(0.3, this.color.replace(/[\d.]+\)$/, (this.opacity * 0.3) + ')'));
      gradient.addColorStop(1, this.color.replace(/[\d.]+\)$/, (this.opacity * depth) + ')'));
      
      // Draw curved streak
      ctx.strokeStyle = gradient;
      ctx.lineWidth = 1.5 + depth * 2;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(tailX, tailY);
      
      // Add a gentle curve using quadratic curve
      const midX = (tailX + headX) / 2;
      const midY = (tailY + headY) / 2 + curveOffset * 0.5;
      ctx.quadraticCurveTo(midX, midY, headX, headY);
      
      ctx.stroke();
      
      // Add glow effect for closer streaks
      if (depth > 0.6) {
        ctx.strokeStyle = this.color.replace(/[\d.]+\)$/, (this.opacity * depth * 0.2) + ')');
        ctx.lineWidth = 4 + depth * 3;
        ctx.stroke();
      }
    }
  }

  class Nebula {
    constructor(canvas) {
      this.canvas = canvas;
      this.reset();
    }

    reset() {
      this.x = Math.random() * this.canvas.width;
      this.y = Math.random() * this.canvas.height;
      this.radius = 150 + Math.random() * 200;
      
      // Choose color based on light/dark mode
      const isLight = document.documentElement.classList.contains('light');
      const colorArray = isLight ? config.colors.nebulaLight : config.colors.nebula;
      this.color = colorArray[Math.floor(Math.random() * colorArray.length)];
      
      this.drift = (Math.random() - 0.5) * 0.1;
      this.driftY = (Math.random() - 0.5) * 0.05;
    }

    update() {
      this.x += this.drift;
      this.y += this.driftY;
      
      // Wrap around
      if (this.x < -this.radius) this.x = this.canvas.width + this.radius;
      if (this.x > this.canvas.width + this.radius) this.x = -this.radius;
      if (this.y < -this.radius) this.y = this.canvas.height + this.radius;
      if (this.y > this.canvas.height + this.radius) this.y = -this.radius;
    }

    draw(ctx) {
      const gradient = ctx.createRadialGradient(this.x, this.y, 0, this.x, this.y, this.radius);
      gradient.addColorStop(0, this.color);
      gradient.addColorStop(0.5, this.color.replace(/[\d.]+\)$/, '0.05)'));
      gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
      
      ctx.fillStyle = gradient;
      ctx.fillRect(this.x - this.radius, this.y - this.radius, this.radius * 2, this.radius * 2);
    }
  }

  class Starfield {
    constructor() {
      this.canvas = null;
      this.ctx = null;
      this.stars = [];
      this.streaks = [];
      this.nebulae = [];
      this.animationId = null;
      this.init();
    }

    init() {
      // Create canvas
      this.canvas = document.createElement('canvas');
      this.canvas.id = 'starfield-canvas';
      this.ctx = this.canvas.getContext('2d');
      
      // Insert as first child of body
      document.body.insertBefore(this.canvas, document.body.firstChild);
      
      // Set initial size
      this.resize();
      
      // Create nebulae (background layer)
      for (let i = 0; i < config.nebulaCount; i++) {
        this.nebulae.push(new Nebula(this.canvas));
      }
      
      // Create stars in multiple layers
      const starsPerLayer = Math.floor(config.starCount / config.starLayers);
      for (let layer = 1; layer <= config.starLayers; layer++) {
        for (let i = 0; i < starsPerLayer; i++) {
          this.stars.push(new Star(this.canvas, layer));
        }
      }
      
      // Create warp streaks
      for (let i = 0; i < config.streakCount; i++) {
        this.streaks.push(new WarpStreak(this.canvas));
      }
      
      // Handle window resize
      window.addEventListener('resize', () => this.resize());
      
      // Start animation
      this.animate();
    }

    resize() {
      this.canvas.width = window.innerWidth;
      this.canvas.height = window.innerHeight;
    }

    animate() {
      // Clear with slight trail effect - adjust for light/dark mode
      const isLight = document.documentElement.classList.contains('light');
      this.ctx.fillStyle = isLight ? 'rgba(212, 228, 247, 0.08)' : 'rgba(0, 0, 0, 0.15)';
      this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
      
      // Draw nebulae (slowest, background)
      this.nebulae.forEach(nebula => {
        nebula.update();
        nebula.draw(this.ctx);
      });
      
      // Draw stars (multiple layers)
      this.stars.forEach(star => {
        star.update();
        star.draw(this.ctx);
      });
      
      // Draw warp streaks (fastest, foreground)
      this.streaks.forEach(streak => {
        streak.update();
        streak.draw(this.ctx);
      });
      
      this.animationId = requestAnimationFrame(() => this.animate());
    }

    destroy() {
      if (this.animationId) {
        cancelAnimationFrame(this.animationId);
      }
      if (this.canvas && this.canvas.parentNode) {
        this.canvas.parentNode.removeChild(this.canvas);
      }
    }
  }

  // Initialize starfield when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      window.starfield = new Starfield();
    });
  } else {
    window.starfield = new Starfield();
  }

  // Clean up on theme change
  window.addEventListener('themechange', () => {
    if (window.starfield) {
      window.starfield.destroy();
      window.starfield = null;
    }
  });
})();
