import { useEffect, useState } from 'react'
import Particles, { initParticlesEngine } from '@tsparticles/react'
import { loadSlim } from '@tsparticles/slim'

export default function ParticlesBackground() {
  const [ready, setReady] = useState(false)
  useEffect(() => { initParticlesEngine(async (e) => { await loadSlim(e) }).then(() => setReady(true)) }, [])
  if (!ready) return null
  return (
    <Particles
      id="tsparticles"
      className="fixed inset-0 pointer-events-none"
      options={{
        background: { color: { value: 'transparent' } },
        fpsLimit: 60,
        interactivity: {
          events: { onHover: { enable: true, mode: 'grab' }, onClick: { enable: true, mode: 'push' } },
          modes: { grab: { distance: 200, links: { opacity: 0.5 } }, push: { quantity: 4 } }
        },
        particles: {
          color: { value: ['#3498db', '#9b59b6', '#2ecc71'] },
          links: { color: '#3498db', distance: 130, enable: true, opacity: 0.25, width: 1 },
          move: { enable: true, speed: 1.2 },
          number: { value: 80 },
          opacity: { value: 0.5 },
          shape: { type: 'circle' },
          size: { value: { min: 1, max: 3 } }
        }
      }}
    />
  )
}
