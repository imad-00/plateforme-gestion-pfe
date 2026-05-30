'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import './landing.css'

/* ════════════════════════════════════════════════════════════════════════════
   GradeX landing page
   École Supérieure en Informatique de Sidi Bel Abbès (ESI-SBA · esi-sba.dz)
   Editorial / academic aesthetic — Fraunces + Hanken Grotesk + JetBrains Mono.
   See landing.css for full design tokens.
   ════════════════════════════════════════════════════════════════════════════ */

interface LandingViewProps {
  /**
   * When set, the viewer is signed in and CTAs route to their dashboard
   * (`/admin` | `/student` | `/teacher`) instead of `/login`. When null, the
   * viewer is a guest and sees Sign-in / Get-started buttons.
   */
  authedDashboardHref?: string | null
  /**
   * False during the initial auth-context restore. We render the "Sign in"
   * CTAs while this is false so SSR / cold loads don't flash a stale button —
   * once the context resolves we swap to "Open your dashboard" if applicable.
   */
  authChecked?: boolean
}

export function LandingView({
  authedDashboardHref = null,
  authChecked = true,
}: LandingViewProps = {}) {
  const [navScrolled, setNavScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  // Swap CTAs only once the auth context has resolved, so a signed-in user
  // never sees a one-frame flash of the guest "Sign in" button.
  const isAuthed = authChecked && !!authedDashboardHref
  const primaryHref = isAuthed ? authedDashboardHref! : '/login'
  const primaryLabel = isAuthed ? 'Open your dashboard' : 'Get started'
  const secondaryHref = isAuthed ? authedDashboardHref! : '/login'
  const secondaryLabel = isAuthed ? 'Back to app' : 'Sign in'

  // Nav shadow on scroll
  useEffect(() => {
    const onScroll = () => setNavScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // Reveal-on-scroll for `.reveal` elements
  useEffect(() => {
    const els = document.querySelectorAll('.landing-root .reveal')
    if (!('IntersectionObserver' in window)) {
      els.forEach(el => el.classList.add('in'))
      return
    }
    const io = new IntersectionObserver(
      entries => {
        entries.forEach(e => {
          if (e.isIntersecting) {
            e.target.classList.add('in')
            io.unobserve(e.target)
          }
        })
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' },
    )
    els.forEach(el => io.observe(el))
    return () => io.disconnect()
  }, [])

  return (
    <div className="landing-root">
      {/* ═════ NAV ═════ */}
      <header className={`nav${navScrolled ? ' scrolled' : ''}`}>
        <div className="container nav-inner">
          <Link href="#top" className="brand" aria-label="GradeX home">
            <span className="mark">G</span> GradeX
          </Link>

          <nav className="nav-links" aria-label="Primary">
            <a href="#about">About ESI-SBA</a>
            <a href="#features">Features</a>
            <a href="#how-it-works">How it works</a>
            <a href="#stats">Impact</a>
            <a href="#testimonials">Voices</a>
          </nav>

          <div className="nav-cta">
            <Link href={secondaryHref} className="btn btn-quiet">{secondaryLabel}</Link>
            <Link href={primaryHref} className="btn btn-primary">
              {primaryLabel}
              <ArrowRight />
            </Link>
          </div>

          <button
            className="nav-toggle"
            aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen(v => !v)}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M4 7h16M4 12h16M4 17h16" />
            </svg>
          </button>
        </div>

        <div className={`mobile-menu${mobileOpen ? ' open' : ''}`}>
          <div className="container">
            <a href="#about" onClick={() => setMobileOpen(false)}>About ESI-SBA</a>
            <a href="#features" onClick={() => setMobileOpen(false)}>Features</a>
            <a href="#how-it-works" onClick={() => setMobileOpen(false)}>How it works</a>
            <a href="#stats" onClick={() => setMobileOpen(false)}>Impact</a>
            <a href="#testimonials" onClick={() => setMobileOpen(false)}>Voices</a>
            <div className="mm-cta">
              <Link href={secondaryHref} className="btn btn-ghost">{secondaryLabel}</Link>
              <Link href={primaryHref} className="btn btn-primary">{primaryLabel}</Link>
            </div>
          </div>
        </div>
      </header>

      <main id="top">
        {/* ═════ HERO ═════ */}
        <section className="hero section" id="hero">
          <div className="container">
            <div className="hero-grid">
              <div className="hero-copy">
                <span className="hero-eyebrow reveal">
                  <span className="dot" /> École Supérieure en Informatique · Sidi Bel Abbès
                </span>
                <h1 className="reveal" data-delay="1">
                  From first proposal to <em>final defense</em>, one academic workflow.
                </h1>
                <p className="hero-sub reveal" data-delay="2">
                  GradeX is the single platform where ESI-SBA students, professors, and juries run
                  final-year projects (PFE) — subjects, teams, deliverables, and defense scheduling,
                  all in one transparent space, one academic year at a time.
                </p>

                <div className="hero-actions reveal" data-delay="2">
                  <Link href={primaryHref} className="btn btn-primary btn-lg">
                    {primaryLabel}
                    <ArrowRight />
                  </Link>
                  <a href="#how-it-works" className="btn btn-ghost btn-lg">See how it works</a>
                </div>

                <div className="hero-trust reveal" data-delay="3">
                  <div className="avatars">
                    <span>SB</span><span>KB</span><span>YA</span><span>NM</span>
                  </div>
                  Trusted across departments at ESI-SBA — students, supervisors &amp; juries.
                </div>
              </div>

              <div className="hero-visual reveal" data-delay="1">
                <div className="browser">
                  <div className="browser-bar">
                    <span className="dots"><i /><i /><i /></span>
                    <span className="url">app.gradex.esi-sba.dz/dashboard</span>
                  </div>
                  <DashboardMockSVG />
                </div>

                <div className="hero-badge">
                  <span className="pill">Scheduled</span>
                  <div className="meta">
                    <b>Defense · Room B-204</b>
                    <small>Jury of 3 · Thu 14:30</small>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ═════ CONTEXT STRIP ═════ */}
        <div className="context">
          <div className="container context-inner reveal">
            <span>SUBJECT SUBMISSION</span><span className="sep" />
            <span>TEAM FORMATION</span><span className="sep" />
            <span>WISHLIST &amp; ASSIGNMENT</span><span className="sep" />
            <span>DELIVERABLES</span><span className="sep" />
            <span>DEFENSE WINDOW</span>
          </div>
        </div>

        {/* ═════ ABOUT THE UNIVERSITY ═════ */}
        <section className="section band" id="about">
          <div className="container">
            <div className="univ-card reveal">
              <div>
                <span className="eyebrow">About the institution</span>
                <h2>École Supérieure en Informatique de Sidi Bel Abbès</h2>
                <p className="lede">
                  ESI-SBA is a public higher school of computer science engineering in Sidi Bel Abbès,
                  Algeria — operating under the Ministry of Higher Education and Scientific Research.
                  It trains state engineers and master&apos;s graduates in Information Systems &amp; Software
                  Engineering, Networks &amp; Distributed Systems, and Artificial Intelligence &amp; Data Science,
                  alongside an active research lab (LabRI-SBA) and an entrepreneurship incubator.
                </p>
                <dl className="facts">
                  <div>
                    <dt>Founded</dt>
                    <dd>2014 · Sidi Bel Abbès, Algeria</dd>
                  </div>
                  <div>
                    <dt>Mission</dt>
                    <dd>Train state-engineer (Ingénieur d&apos;État) computer scientists</dd>
                  </div>
                  <div>
                    <dt>Cycles</dt>
                    <dd>2-year preparatory · 3-year engineering · Master &amp; PhD</dd>
                  </div>
                  <div>
                    <dt>More info</dt>
                    <dd>
                      <a
                        href="https://www.esi-sba.dz"
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: 'var(--accent)', fontWeight: 600 }}
                      >
                        esi-sba.dz →
                      </a>
                    </dd>
                  </div>
                </dl>
              </div>
              <div className="crest">
                <EsiCrestSVG />
              </div>
            </div>
          </div>
        </section>

        {/* ═════ FEATURES ═════ */}
        <section className="section" id="features">
          <div className="container">
            <div className="section-head reveal">
              <span className="eyebrow">Built for every role</span>
              <h2>One platform, three points of view.</h2>
              <p>
                GradeX adapts to who you are. Students, professors, and jury members each get
                exactly the tools their part of the PFE process needs — nothing more, nothing in the way.
              </p>
            </div>

            <div className="grid-3">
              <FeatureCard
                tag="For students"
                title="Form a team, claim a subject."
                body="Find teammates, lock in your group, rank the subjects you want, then track every deliverable and deadline as the campaign moves through its phases."
                icon={
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 10 12 5 2 10l10 5 10-5Z" />
                    <path d="M6 12v5c0 1 2.7 2.5 6 2.5s6-1.5 6-2.5v-5" />
                  </svg>
                }
                items={[
                  'Discover teammates & build your group',
                  'Wishlist & rank available subjects',
                  'Upload deliverables & follow review status',
                ]}
              />
              <FeatureCard
                delay={1}
                tag="For professors"
                title="Propose, supervise, review."
                body="Submit subject proposals for approval, supervise assigned teams, and review their deliverables with structured feedback — all from one supervision board."
                icon={
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z" />
                  </svg>
                }
                items={[
                  'Propose subjects & set team capacity',
                  'Supervise teams across the campaign',
                  'Review deliverables & request revisions',
                ]}
              />
              <FeatureCard
                delay={2}
                tag="For juries"
                title="Evaluate with full context."
                body="See every defense you're assigned to, read the project and its deliverables ahead of time, then record evaluations and publish grades in a single pass."
                icon={
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="m14 13-7.5 7.5a2.1 2.1 0 0 1-3-3L11 10" />
                    <path d="m16 16 6-6" />
                    <path d="m8 8 6-6" />
                    <path d="m9 7 8 8" />
                    <path d="m21 11-8-8" />
                  </svg>
                }
                items={[
                  'View assigned defenses & schedules',
                  'Read project files before the session',
                  'Record evaluations & publish grades',
                ]}
              />
            </div>
          </div>
        </section>

        {/* ═════ HOW IT WORKS ═════ */}
        <section className="section band" id="how-it-works">
          <div className="container">
            <div className="section-head reveal">
              <span className="eyebrow">The workflow</span>
              <h2>Three steps, from idea to defense.</h2>
              <p>
                The whole PFE lifecycle is phase-gated — features open and close at the right moment,
                so everyone always knows what to do next.
              </p>
            </div>

            <div className="steps">
              <Step
                number="STEP 01"
                title="Submit"
                body="Professors propose subjects and admins approve them. Students form their team, lock it, and submit a ranked wishlist of the topics they want."
                icon={
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M14 2v6h6" />
                    <path d="M4 13.5V4a2 2 0 0 1 2-2h8l6 6v11a2 2 0 0 1-2 2H6" />
                    <path d="M2 18h7" />
                    <path d="m6 15-3 3 3 3" />
                  </svg>
                }
              />
              <Step
                delay={1}
                number="STEP 02"
                title="Schedule"
                body="The assignment algorithm matches teams to subjects. Admins set defense windows and the jury fixes a date, a room, and the panel for each session."
                icon={
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="4" width="18" height="18" rx="2" />
                    <path d="M16 2v4M8 2v4M3 10h18" />
                    <path d="m9 16 2 2 4-4" />
                  </svg>
                }
              />
              <Step
                delay={2}
                number="STEP 03"
                title="Defend"
                last
                body="Teams present to the jury, who already have the project and its deliverables on hand. Evaluations are recorded and grades published — same day."
                icon={
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3" />
                  </svg>
                }
              />
            </div>

            <div className="flow-table reveal" data-delay="1">
              <table>
                <thead>
                  <tr><th>Stage</th><th>Owner</th><th>Status</th></tr>
                </thead>
                <tbody>
                  <tr>
                    <td><span className="who">Subject proposal</span> — &ldquo;Federated learning for IoT&rdquo;</td>
                    <td>Dr. K. Belhadj</td>
                    <td><span className="status s-ok">Approved</span></td>
                  </tr>
                  <tr>
                    <td><span className="who">Team Aurora</span> — 3 members, locked</td>
                    <td>Y. Benali</td>
                    <td><span className="status s-ok">Validated</span></td>
                  </tr>
                  <tr>
                    <td><span className="who">Deliverable</span> — Mid-term report v2</td>
                    <td>Supervisor review</td>
                    <td><span className="status s-warn">In review</span></td>
                  </tr>
                  <tr>
                    <td><span className="who">Defense</span> — Room B-204, jury of 3</td>
                    <td>Jury panel</td>
                    <td><span className="status s-acc">Scheduled</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* ═════ STATS ═════ */}
        <section className="section" id="stats">
          <div className="container">
            <div
              className="section-head reveal"
              style={{ maxWidth: 'none', display: 'flex', flexWrap: 'wrap', alignItems: 'flex-end', justifyContent: 'space-between', gap: 20 }}
            >
              <div style={{ maxWidth: 560 }}>
                <span className="eyebrow" style={{ display: 'block', marginBottom: 18 }}>By the numbers</span>
                <h2 style={{ fontSize: 'clamp(30px,4.2vw,46px)', marginBottom: 0 }}>
                  A full campaign, kept on track.
                </h2>
              </div>
              <p style={{ color: 'var(--muted)', maxWidth: '42ch' }}>
                Indicative figures from a recent PFE campaign managed end-to-end on GradeX at ESI-SBA.
              </p>
            </div>

            <div className="stats-grid reveal" data-delay="1">
              <Stat target={1400} suffix="+" label="Students onboarded" />
              <Stat target={520} label="PFE projects managed" />
              <Stat target={180} label="Professors & supervisors" />
              <Stat target={96} suffix="%" label="Defenses on schedule" />
            </div>
          </div>
        </section>

        {/* ═════ TESTIMONIALS ═════ */}
        <section className="section band" id="testimonials">
          <div className="container">
            <div className="section-head reveal">
              <span className="eyebrow">Voices from campus</span>
              <h2>What students and supervisors say.</h2>
            </div>

            <div className="quotes">
              <figure className="quote reveal">
                <div className="mark">&ldquo;</div>
                <blockquote>
                  For the first time the whole PFE felt organised. I always knew which phase was
                  open, when my deliverables were due, and exactly where my team stood — no more
                  chasing emails before every deadline.
                </blockquote>
                <figcaption className="who">
                  <span className="av">YB</span>
                  <div>
                    <b>Yasmine Benali</b>
                    <small>5th-year student · ESI-SBA</small>
                  </div>
                </figcaption>
              </figure>

              <figure className="quote reveal" data-delay="1">
                <div className="mark">&ldquo;</div>
                <blockquote>
                  Proposing subjects, supervising teams and reviewing deliverables used to live in
                  three different places. GradeX put them on one board — and scheduling defenses
                  with the jury became a five-minute job instead of a week of back-and-forth.
                </blockquote>
                <figcaption className="who">
                  <span className="av">KB</span>
                  <div>
                    <b>Dr. Karim Belhadj</b>
                    <small>Associate Professor &amp; PFE supervisor · ESI-SBA</small>
                  </div>
                </figcaption>
              </figure>
            </div>
          </div>
        </section>

        {/* ═════ CTA ═════ */}
        <section className="section cta-band" id="get-started">
          <div className="container">
            <div className="cta-card reveal">
              <span className="eyebrow">Ready when your campaign is</span>
              <h2>Run your next PFE campaign on GradeX.</h2>
              <p>
                Bring students, professors, and juries into one transparent workflow — from the
                first subject proposal to the final published grade.
              </p>
              <div className="hero-actions">
                <Link href={primaryHref} className="btn btn-primary btn-lg">
                  {primaryLabel}
                  <ArrowRight />
                </Link>
                <Link href={secondaryHref} className="btn btn-ghost btn-lg">
                  {isAuthed ? 'Back to app' : 'Sign in to your account'}
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* ═════ FOOTER ═════ */}
      <footer className="footer">
        <div className="container">
          <div className="footer-grid">
            <div className="footer-about">
              <a href="#top" className="brand"><span className="mark">G</span> GradeX</a>
              <p className="about">
                The final-year project (PFE) management platform — subjects, teams, deliverables and
                defenses, in one academic workflow.
              </p>
              <p className="inst">
                École Supérieure en Informatique<br />
                Sidi Bel Abbès (ESI-SBA), Algeria<br />
                <a
                  href="https://www.esi-sba.dz"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: 'var(--accent)' }}
                >
                  www.esi-sba.dz
                </a>
              </p>
            </div>

            <div>
              <h4>Platform</h4>
              <ul>
                <li><a href="#features">Features</a></li>
                <li><a href="#how-it-works">How it works</a></li>
                <li><a href="#stats">Impact</a></li>
                <li><Link href={secondaryHref}>{secondaryLabel}</Link></li>
              </ul>
            </div>

            <div>
              <h4>Roles</h4>
              <ul>
                <li><a href="#features">Students</a></li>
                <li><a href="#features">Professors</a></li>
                <li><a href="#features">Supervisors</a></li>
                <li><a href="#features">Jury members</a></li>
              </ul>
            </div>

            <div>
              <h4>Institution</h4>
              <ul>
                <li>
                  <a href="https://www.esi-sba.dz" target="_blank" rel="noopener noreferrer">
                    esi-sba.dz
                  </a>
                </li>
                <li><a href="#about">About ESI-SBA</a></li>
                <li><a href="#get-started">Get started</a></li>
                <li><a href="mailto:contact@esi-sba.dz">Contact</a></li>
              </ul>
            </div>
          </div>

          <div className="footer-bottom">
            <small>
              © {new Date().getFullYear()} GradeX · École Supérieure en Informatique — Sidi Bel Abbès.
            </small>
            <div className="legal">
              <small><a href="#">Privacy</a></small>
              <small><a href="#">Terms</a></small>
              <small><a href="#">Accessibility</a></small>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

/* ─── Sub-components ─────────────────────────────────────────────────────── */

function ArrowRight() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  )
}

function Check() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="m5 12 4.5 4.5L19 7" />
    </svg>
  )
}

function FeatureCard({
  tag,
  title,
  body,
  items,
  icon,
  delay,
}: {
  tag: string
  title: string
  body: string
  items: string[]
  icon: React.ReactNode
  delay?: number
}) {
  return (
    <article className="card reveal" data-delay={delay}>
      <div className="icon">{icon}</div>
      <div className="role-tag">{tag}</div>
      <h3>{title}</h3>
      <p>{body}</p>
      <ul className="feature-list">
        {items.map(text => (
          <li key={text}><Check /> {text}</li>
        ))}
      </ul>
    </article>
  )
}

function Step({
  number,
  title,
  body,
  icon,
  delay,
  last,
}: {
  number: string
  title: string
  body: string
  icon: React.ReactNode
  delay?: number
  last?: boolean
}) {
  return (
    <div className="step reveal" data-delay={delay}>
      <div className="step-no">{number}</div>
      <div className="step-ic">{icon}</div>
      <h3>{title}</h3>
      <p>{body}</p>
      {!last && (
        <div className="arrow">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
            <path d="m9 6 6 6-6 6" />
          </svg>
        </div>
      )}
    </div>
  )
}

function Stat({
  target,
  suffix = '',
  label,
}: {
  target: number
  suffix?: string
  label: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const [value, setValue] = useState(0)
  const fired = useRef(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (!('IntersectionObserver' in window)) {
      setValue(target)
      return
    }
    const io = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting && !fired.current) {
            fired.current = true
            io.unobserve(entry.target)
            const start = performance.now()
            const duration = 1400
            const ease = (t: number) => 1 - Math.pow(1 - t, 3)
            const tick = (now: number) => {
              const p = Math.min((now - start) / duration, 1)
              setValue(Math.round(ease(p) * target))
              if (p < 1) requestAnimationFrame(tick)
            }
            requestAnimationFrame(tick)
          }
        })
      },
      { threshold: 0.6 },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [target])

  return (
    <div className="stat">
      <div className="num" ref={ref}>
        {value.toLocaleString('en-US')}
        {suffix && <span className="suffix">{suffix}</span>}
      </div>
      <div className="label">{label}</div>
    </div>
  )
}

/* ─── Inline SVG: dashboard mockup (replaces the hero placeholder) ───────── */

function DashboardMockSVG() {
  return (
    <svg
      className="browser-mock"
      viewBox="0 0 800 550"
      role="img"
      aria-label="GradeX student dashboard preview"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect width="800" height="550" fill="#ffffff" />

      {/* Left sidebar */}
      <rect x="0" y="0" width="180" height="550" fill="#fafaf8" />
      <line x1="180" y1="0" x2="180" y2="550" stroke="rgba(22,24,29,0.10)" />

      {/* Brand block */}
      <rect x="18" y="22" width="22" height="22" rx="6" fill="#16181d" />
      <rect x="48" y="28" width="60" height="9" rx="2" fill="#16181d" opacity="0.85" />

      {/* Nav items */}
      <g fontFamily="system-ui" fontSize="11" fill="#6b7077">
        <rect x="12" y="78" width="156" height="30" rx="6" fill="#eef3f8" />
        <rect x="24" y="89" width="14" height="10" rx="2" fill="#1d5c8c" />
        <text x="48" y="98" fill="#15486e" fontWeight="600">Dashboard</text>

        <rect x="24" y="123" width="14" height="10" rx="2" fill="#9aa0a7" />
        <text x="48" y="132">My team</text>

        <rect x="24" y="153" width="14" height="10" rx="2" fill="#9aa0a7" />
        <text x="48" y="162">Subjects</text>

        <rect x="24" y="183" width="14" height="10" rx="2" fill="#9aa0a7" />
        <text x="48" y="192">Wishlist</text>

        <rect x="24" y="213" width="14" height="10" rx="2" fill="#9aa0a7" />
        <text x="48" y="222">Deliverables</text>

        <rect x="24" y="243" width="14" height="10" rx="2" fill="#9aa0a7" />
        <text x="48" y="252">Defense</text>
      </g>

      {/* Topbar */}
      <rect x="180" y="0" width="620" height="50" fill="#ffffff" />
      <line x1="180" y1="50" x2="800" y2="50" stroke="rgba(22,24,29,0.10)" />
      <circle cx="754" cy="25" r="13" fill="#eef3f8" />
      <text x="754" y="29" textAnchor="middle" fontFamily="system-ui" fontSize="11" fontWeight="600" fill="#15486e">YB</text>
      <rect x="700" y="20" width="14" height="10" rx="2" fill="#9aa0a7" />

      {/* Title */}
      <text x="208" y="92" fontFamily="Georgia, serif" fontSize="22" fontWeight="600" fill="#16181d">Dashboard</text>
      <text x="208" y="113" fontFamily="system-ui" fontSize="12" fill="#6b7077">Academic year 2025–2026 · Team Aurora</text>

      {/* Stat cards */}
      {[
        { x: 208, label: 'Subjects', value: '420', delta: 'in catalogue' },
        { x: 350, label: 'My wishlist', value: '8', delta: 'ranked' },
        { x: 492, label: 'Deliverables', value: '3', delta: 'pending' },
        { x: 634, label: 'Defense', value: 'Thu', delta: '14:30 · B-204' },
      ].map(c => (
        <g key={c.label}>
          <rect x={c.x} y="140" width="128" height="86" rx="10" fill="#ffffff" stroke="rgba(22,24,29,0.10)" />
          <text x={c.x + 14} y="164" fontFamily="system-ui" fontSize="10" letterSpacing="1.2" fill="#9aa0a7">{c.label.toUpperCase()}</text>
          <text x={c.x + 14} y="196" fontFamily="Georgia, serif" fontSize="26" fontWeight="600" fill="#16181d">{c.value}</text>
          <text x={c.x + 14} y="214" fontFamily="system-ui" fontSize="11" fill="#6b7077">{c.delta}</text>
        </g>
      ))}

      {/* Schedule table */}
      <rect x="208" y="250" width="554" height="248" rx="10" fill="#ffffff" stroke="rgba(22,24,29,0.10)" />
      <text x="226" y="278" fontFamily="Georgia, serif" fontSize="14" fontWeight="600" fill="#16181d">Defense schedule</text>
      <text x="226" y="296" fontFamily="system-ui" fontSize="11" fill="#9aa0a7">DEFENSE WINDOW · 12 — 26 JUN</text>

      {/* Table head */}
      <rect x="208" y="316" width="554" height="32" fill="#fafaf8" />
      <line x1="208" y1="348" x2="762" y2="348" stroke="rgba(22,24,29,0.10)" />
      <g fontFamily="system-ui" fontSize="10" letterSpacing="1.0" fill="#9aa0a7">
        <text x="226" y="336">TEAM</text>
        <text x="402" y="336">JURY</text>
        <text x="566" y="336">DATE</text>
        <text x="680" y="336">STATUS</text>
      </g>

      {/* Rows */}
      {[
        { y: 372, team: 'Aurora', jury: 'KB · NM · SB', date: 'Thu 14:30', status: 'Scheduled', tone: 'acc' },
        { y: 408, team: 'Nimbus', jury: 'YA · KB · RM', date: 'Thu 16:00', status: 'Scheduled', tone: 'acc' },
        { y: 444, team: 'Orbit',  jury: 'NM · SB · YA', date: 'Fri 09:00', status: 'Ready',     tone: 'ok' },
        { y: 480, team: 'Helios', jury: '— pending',    date: '—',         status: 'Pending',  tone: 'warn' },
      ].map(r => (
        <g key={r.team}>
          <text x="226" y={r.y} fontFamily="system-ui" fontSize="12" fontWeight="600" fill="#16181d">{r.team}</text>
          <text x="402" y={r.y} fontFamily="ui-monospace,monospace" fontSize="11" fill="#6b7077">{r.jury}</text>
          <text x="566" y={r.y} fontFamily="ui-monospace,monospace" fontSize="11" fill="#6b7077">{r.date}</text>
          <StatusPill x={680} y={r.y - 12} tone={r.tone as 'acc' | 'ok' | 'warn'} label={r.status} />
        </g>
      ))}
    </svg>
  )
}

function StatusPill({
  x, y, tone, label,
}: {
  x: number
  y: number
  tone: 'acc' | 'ok' | 'warn'
  label: string
}) {
  const palette = {
    acc:  { fill: '#eef3f8', stroke: 'rgba(29,92,140,0.22)',  text: '#1d5c8c' },
    ok:   { fill: '#ecf6f0', stroke: 'rgba(47,125,84,0.22)',  text: '#2f7d54' },
    warn: { fill: '#f9f2e3', stroke: 'rgba(154,107,24,0.22)', text: '#9a6b18' },
  }[tone]
  return (
    <g>
      <rect x={x} y={y} width="70" height="20" rx="10" fill={palette.fill} stroke={palette.stroke} />
      <circle cx={x + 11} cy={y + 10} r="3" fill={palette.text} />
      <text x={x + 22} y={y + 14} fontFamily="ui-monospace,monospace" fontSize="10" fontWeight="600" fill={palette.text}>{label}</text>
    </g>
  )
}

/* ─── Inline SVG: institutional crest ────────────────────────────────────── */

function EsiCrestSVG() {
  return (
    <svg
      viewBox="0 0 280 320"
      role="img"
      aria-label="ESI-SBA institutional emblem"
      xmlns="http://www.w3.org/2000/svg"
      style={{ width: '100%', maxWidth: 280, height: 'auto' }}
    >
      {/* Outer shield */}
      <defs>
        <linearGradient id="shieldFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fafaf8" />
          <stop offset="1" stopColor="#f5f5f1" />
        </linearGradient>
      </defs>
      <path
        d="M140 14 L246 50 V160 C246 220 200 270 140 304 C80 270 34 220 34 160 V50 Z"
        fill="url(#shieldFill)"
        stroke="#16181d"
        strokeWidth="2"
      />
      {/* Inner shield outline */}
      <path
        d="M140 30 L232 60 V160 C232 212 192 256 140 286 C88 256 48 212 48 160 V60 Z"
        fill="none"
        stroke="rgba(22,24,29,0.18)"
        strokeWidth="1"
      />
      {/* Top ribbon */}
      <rect x="60" y="62" width="160" height="28" fill="#1d5c8c" />
      <text
        x="140" y="81" textAnchor="middle"
        fontFamily="Georgia, serif" fontWeight="600"
        fontSize="14" letterSpacing="2" fill="#ffffff"
      >ESI · SBA</text>
      {/* Open book */}
      <g transform="translate(140 170)">
        <path d="M-46 0 L0 -8 L46 0 L46 36 L0 28 L-46 36 Z" fill="#ffffff" stroke="#16181d" strokeWidth="1.6" />
        <line x1="0" y1="-8" x2="0" y2="28" stroke="#16181d" strokeWidth="1.4" />
        <line x1="-34" y1="6"  x2="-6" y2="0"  stroke="rgba(22,24,29,0.4)" strokeWidth="1" />
        <line x1="-34" y1="14" x2="-6" y2="8"  stroke="rgba(22,24,29,0.4)" strokeWidth="1" />
        <line x1="-34" y1="22" x2="-6" y2="16" stroke="rgba(22,24,29,0.4)" strokeWidth="1" />
        <line x1="6"  y1="0"  x2="34" y2="6"  stroke="rgba(22,24,29,0.4)" strokeWidth="1" />
        <line x1="6"  y1="8"  x2="34" y2="14" stroke="rgba(22,24,29,0.4)" strokeWidth="1" />
        <line x1="6"  y1="16" x2="34" y2="22" stroke="rgba(22,24,29,0.4)" strokeWidth="1" />
      </g>
      {/* Stylised microchip below book */}
      <g transform="translate(140 226)" stroke="#1d5c8c" strokeWidth="1.6" fill="none">
        <rect x="-22" y="-12" width="44" height="24" rx="3" fill="#eef3f8" />
        <line x1="-22" y1="-4"  x2="-30" y2="-4" />
        <line x1="-22" y1="4"   x2="-30" y2="4" />
        <line x1="22"  y1="-4"  x2="30"  y2="-4" />
        <line x1="22"  y1="4"   x2="30"  y2="4" />
        <line x1="-8"  y1="-12" x2="-8"  y2="-18" />
        <line x1="8"   y1="-12" x2="8"   y2="-18" />
        <line x1="-8"  y1="12"  x2="-8"  y2="18" />
        <line x1="8"   y1="12"  x2="8"   y2="18" />
        <circle cx="0" cy="0" r="3" fill="#1d5c8c" stroke="none" />
      </g>
      {/* Banner */}
      <path
        d="M50 248 L230 248 L222 274 L58 274 Z"
        fill="#16181d"
      />
      <text
        x="140" y="266" textAnchor="middle"
        fontFamily="Georgia, serif" fontSize="11" letterSpacing="3" fill="#ffffff"
      >SCIENTIA · INGENIUM</text>
      {/* Founded marker */}
      <text
        x="140" y="296" textAnchor="middle"
        fontFamily="ui-monospace, monospace" fontSize="9" letterSpacing="2" fill="rgba(22,24,29,0.5)"
      >FOUNDED 2014 · SIDI BEL ABBÈS</text>
    </svg>
  )
}
