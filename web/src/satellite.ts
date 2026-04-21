const TRAIL_LEN = 22;
const DRIFT_SPEED = 36;
const WASD_FORCE = 58;
const ORBIT_RADIUS = 52;
const ORBIT_FORCE = 68;

interface TrailPt {
  x: number;
  y: number;
}

export interface Keys {
  up: boolean;
  down: boolean;
  left: boolean;
  right: boolean;
}

export class Satellite {
  x: number;
  y: number;
  private driftAngle: number;
  private driftTimer = 0;
  private trail: TrailPt[] = [];
  private logicalW: number;
  private logicalH: number;

  constructor(w: number, h: number) {
    this.logicalW = w;
    this.logicalH = h;
    this.x = w * 0.48;
    this.y = h * 0.52;
    this.driftAngle = Math.random() * Math.PI * 2;
  }

  resize(w: number, h: number): void {
    this.logicalW = w;
    this.logicalH = h;
  }

  update(dt: number, keys: Keys, projectPositions: { x: number; y: number }[]): void {
    const w = this.logicalW;
    const h = this.logicalH;

    this.driftTimer -= dt;
    if (this.driftTimer <= 0) {
      this.driftAngle += (Math.random() - 0.5) * Math.PI * 0.85;
      this.driftTimer = 1.6 + Math.random() * 2.4;
    }

    let vx = Math.cos(this.driftAngle) * DRIFT_SPEED;
    let vy = Math.sin(this.driftAngle) * DRIFT_SPEED;

    if (keys.up) vy -= WASD_FORCE;
    if (keys.down) vy += WASD_FORCE;
    if (keys.left) vx -= WASD_FORCE;
    if (keys.right) vx += WASD_FORCE;

    for (const pp of projectPositions) {
      const dx = this.x - pp.x;
      const dy = this.y - pp.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < ORBIT_RADIUS && dist > 1) {
        const inv = 1 / dist;
        const strength = (1 - dist / ORBIT_RADIUS) * ORBIT_FORCE;
        vx += -dy * inv * strength;
        vy += dx * inv * strength;
      }
    }

    this.trail.push({ x: this.x, y: this.y });
    if (this.trail.length > TRAIL_LEN) this.trail.shift();

    this.x += vx * dt;
    this.y += vy * dt;

    const M = 12;
    let wrapped = false;
    if (this.x < -M) {
      this.x += w + M * 2;
      wrapped = true;
    } else if (this.x > w + M) {
      this.x -= w + M * 2;
      wrapped = true;
    }
    if (this.y < -M) {
      this.y += h + M * 2;
      wrapped = true;
    } else if (this.y > h + M) {
      this.y -= h + M * 2;
      wrapped = true;
    }
    if (wrapped) this.trail = [];
  }

  draw(ctx: CanvasRenderingContext2D): void {
    const x0 = Math.floor(this.x);
    const y0 = Math.floor(this.y);

    for (let i = 0; i < this.trail.length; i++) {
      const frac = (i + 1) / this.trail.length;
      const a = frac * frac * 0.55;
      const size = frac < 0.4 ? 1 : frac < 0.72 ? 2 : 3;
      const tx = Math.floor(this.trail[i].x) - Math.floor(size / 2);
      const ty = Math.floor(this.trail[i].y) - Math.floor(size / 2);
      ctx.fillStyle = `rgba(55,155,255,${a.toFixed(3)})`;
      ctx.fillRect(tx, ty, size, size);
    }

    ctx.fillStyle = "rgba(70,150,255,0.07)";
    ctx.fillRect(x0 - 8, y0 - 7, 17, 15);

    ctx.fillStyle = "rgba(130,205,255,0.88)";
    ctx.fillRect(x0, y0 - 5, 1, 3);

    ctx.fillStyle = "rgba(90,180,255,0.95)";
    ctx.fillRect(x0 - 2, y0 - 2, 5, 5);

    ctx.fillStyle = "rgba(75,160,255,0.80)";
    ctx.fillRect(x0 - 6, y0, 4, 1);
    ctx.fillRect(x0 + 3, y0, 4, 1);

    ctx.fillStyle = "rgba(200,235,255,1.0)";
    ctx.fillRect(x0, y0, 1, 1);
  }

  getPosition(): { x: number; y: number } {
    return { x: this.x, y: this.y };
  }
}
