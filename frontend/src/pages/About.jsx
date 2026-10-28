import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { InPersonLink, TeleButton } from '../components/Buttons'
import DoctorCard from '../components/DoctorCard'
import Hero from '../components/Hero'
import Icon from '../components/Icon'
import Seo from '../components/Seo'
import { ErrorState, Loading } from '../components/States'
import { useFetch } from '../hooks/useFetch'
import { api } from '../lib/api'

function Gallery({ items }) {
  const [open, setOpen] = useState(null)
  useEffect(() => {
    if (open === null) return undefined
    const onKey = (e) => { if (e.key === 'Escape') setOpen(null); if (e.key === 'ArrowRight') setOpen((i) => (i + 1) % items.length); if (e.key === 'ArrowLeft') setOpen((i) => (i + items.length - 1) % items.length) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, items.length])
  return (
    <>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
        {items.map((g, i) => (
          <button key={g.id} type="button" onClick={() => setOpen(i)} aria-label={`Open picture ${i + 1}: ${g.caption}`}
            className="group overflow-hidden rounded-3xl bg-white shadow-sm">
            <img src={g.url} alt={g.caption} loading="lazy" className="aspect-[4/3] w-full object-cover transition duration-500 group-hover:scale-105" />
          </button>
        ))}
      </div>
      {open !== null && (
        <div className="fixed inset-0 z-[70] grid place-items-center bg-ink/90 p-4" role="dialog" aria-modal="true" aria-label="Picture viewer" onClick={() => setOpen(null)}>
          <button className="absolute right-5 top-5 rounded-full bg-white p-2" aria-label="Close" onClick={() => setOpen(null)}><Icon name="x" size={22} /></button>
          <figure className="max-h-full max-w-5xl" onClick={(e) => e.stopPropagation()}>
            <img src={items[open].url} alt={items[open].caption} className="max-h-[80vh] rounded-2xl object-contain" />
            <figcaption className="mt-3 text-center text-white">{items[open].caption}</figcaption>
          </figure>
        </div>
      )}
    </>
  )
}

export default function About() {
  const team = useFetch(() => api.doctors(), [])
  const pics = useFetch(() => api.gallery(), [])
  return (
    <>
      <Seo title="About us" description="Patient-centred dermatology in Addis Ababa: our mission, vision, values, doctors and clinic." />
      <Hero eyebrow="About us" title="Patient-centred dermatology in Addis Ababa"
        intro="Medical, surgical and cosmetic dermatology under one roof, at our Bole and Zenebework branches." />
      <section className="wrap grid items-center gap-10 py-14 lg:grid-cols-2">
        <div>
          <p className="text-xs font-bold uppercase tracking-[.14em] text-leaf">Who we are</p>
          <h2 className="mt-1 text-3xl sm:text-4xl">Healthy skin is about overall health</h2>
          <p className="mt-4 leading-8 text-muted">At Dr. Feysel Specialty Dermatology Clinic, we understand that healthy skin is not just about appearance. It is about overall health. Our team of experienced dermatologists is committed to providing top-notch, patient-centred care.</p>
          <p className="mt-3 leading-8 text-muted">We diagnose and treat a wide range of dermatological conditions, so you receive personal attention and effective solutions. Whether you need treatment for a specific skin condition or are considering a cosmetic procedure, we have the expertise to address your needs.</p>
          <ul className="mt-5 space-y-2.5">
            {['Highly trained, board-certified dermatologists', 'Medical, surgical and cosmetic dermatology under one roof', 'Two branches: Bole and Zenebework'].map((t) => (
              <li key={t} className="flex items-start gap-2.5 font-semibold"><Icon name="circle-check" size={20} className="mt-0.5 shrink-0 text-leaf" />{t}</li>
            ))}
          </ul>
          <div className="mt-7 flex flex-wrap gap-3"><TeleButton /><InPersonLink>Book in person</InPersonLink></div>
        </div>
        <div className="relative aspect-video overflow-hidden rounded-[28px] bg-ink shadow-lift">
          <iframe className="absolute inset-0 h-full w-full border-0" src="https://www.youtube-nocookie.com/embed/QIvs_u-eXjE" title="Dr. Feysel Dermatology clinic video" loading="lazy"
            allow="accelerometer; encrypted-media; gyroscope; picture-in-picture" allowFullScreen />
        </div>
      </section>

      <section className="bg-[#E8F1F9] py-14">
        <div className="wrap">
          <p className="text-center text-xs font-bold uppercase tracking-[.14em] text-leaf">What drives us</p>
          <h2 className="mb-8 mt-1 text-center text-3xl sm:text-4xl">Mission, vision and values</h2>
          <div className="grid gap-5 md:grid-cols-3">
            <div className="card p-7"><Icon name="target" size={30} className="text-leaf" /><h3 className="mt-3 text-2xl">Mission</h3>
              <p className="mt-2 leading-7 text-muted">To provide our patients with up-to-date, affordable and state-of-the-art health care, delivered in a personable and compassionate manner.</p></div>
            <div className="card p-7"><Icon name="eye" size={30} className="text-royal" /><h3 className="mt-3 text-2xl">Vision</h3>
              <p className="mt-2 leading-7 text-muted">To become a leader in innovative, high-quality dermatologic services in East Africa.</p></div>
            <div className="card p-7"><Icon name="gem" size={30} className="text-leaf" /><h3 className="mt-3 text-2xl">Core values</h3>
              <div className="mt-3 flex flex-wrap gap-2">{['Integrity', 'Professionalism', 'Quality', 'Respect', 'Transparency'].map((v) => <span key={v} className="pill pill-blue">{v}</span>)}</div></div>
          </div>
        </div>
      </section>

      <section className="wrap py-14">
        <div className="mb-7 flex flex-wrap items-end justify-between gap-3">
          <div><p className="text-xs font-bold uppercase tracking-[.14em] text-leaf">Our team</p><h2 className="mt-1 text-3xl sm:text-4xl">Meet our doctors</h2></div>
          <Link to="/doctors" className="btn btn-outline">All doctors and profiles</Link>
        </div>
        {team.loading && <Loading />}
        {team.error && <ErrorState error={team.error} />}
        {team.data && <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">{team.data.doctors.map((d) => <DoctorCard key={d.slug} doctor={d} />)}</div>}
      </section>

      {pics.data?.gallery.length > 0 && (
        <section className="wrap pb-14">
          <p className="text-xs font-bold uppercase tracking-[.14em] text-leaf">Inside the clinic</p>
          <h2 className="mb-7 mt-1 text-3xl sm:text-4xl">Gallery</h2>
          <Gallery items={pics.data.gallery} />
        </section>
      )}
    </>
  )
}
