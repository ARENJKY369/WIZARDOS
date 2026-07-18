"""Procedural particle simulation for spell visuals."""

from __future__ import annotations
import math
import random
from dataclasses import dataclass
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor


@dataclass
class Particle:
    pos: QPointF
    vel: QPointF
    life: float
    max_life: float
    size: float
    color: QColor
    spin: float = 0.0


class ParticleEngine:
    def __init__(self) -> None:
        self.particles: list[Particle] = []
        self.ambient = True

    def burst(self, x: float, y: float, color: QColor, effect: str = "sparks", amount: int = 90) -> None:
        if effect in {"explosion", "bombarda"}:
            amount = 180
        elif effect in {"shield", "magic_circle", "patronus"}:
            amount = 140
        for i in range(amount):
            angle = random.random() * math.tau
            if effect in {"shield", "magic_circle"}:
                speed = random.uniform(60, 190)
                pos = QPointF(x + math.cos(angle) * 80, y + math.sin(angle) * 80)
            else:
                speed = random.uniform(40, 420)
                pos = QPointF(x, y)
            vel = QPointF(math.cos(angle) * speed, math.sin(angle) * speed)
            c = QColor(color)
            c.setAlpha(random.randint(120, 255))
            self.particles.append(Particle(pos, vel, random.uniform(0.55, 1.8), random.uniform(0.8, 1.8), random.uniform(2, 9), c, random.uniform(-6, 6)))

    def add_trail_particles(self, x: float, y: float, color: QColor, amount: int = 3) -> None:
        for _ in range(amount):
            angle = random.random() * math.tau
            speed = random.uniform(15, 80)
            vel = QPointF(math.cos(angle) * speed, -random.uniform(5, 45))
            c = QColor(color)
            c.setAlpha(random.randint(150, 255))
            self.particles.append(
                Particle(
                    QPointF(x, y),
                    vel,
                    random.uniform(0.25, 0.75),
                    random.uniform(0.25, 0.75),
                    random.uniform(1.5, 4.5),
                    c,
                )
            )

    def update(self, dt: float, width: int, height: int) -> None:
        if self.ambient and len(self.particles) < 260:
            for _ in range(2):
                c = QColor(100, 210, 255, random.randint(35, 95))
                self.particles.append(
                    Particle(
                        QPointF(random.randrange(max(width, 1)), height + 8),
                        QPointF(random.uniform(-8, 8), random.uniform(-34, -12)),
                        random.uniform(3, 8),
                        8,
                        random.uniform(1, 3),
                        c,
                    )
                )
        alive: list[Particle] = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.vel.setY(p.vel.y() + 16 * dt)
            p.pos.setX(p.pos.x() + p.vel.x() * dt)
            p.pos.setY(p.pos.y() + p.vel.y() * dt)
            alive.append(p)
        self.particles = alive[-1400:]
