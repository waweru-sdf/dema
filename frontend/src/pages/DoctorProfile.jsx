import { Link, useParams } from 'react-router-dom'
import { ErrorState, Loading } from '../components/States'
import { InPersonLink, TeleButton } from '../components/Buttons'
import Hero from '../components/Hero'
import Icon from '../components/Icon'
import ReviewCard from '../components/ReviewCard'
import Avatar from '../components/Avatar'
import Seo from '../components/Seo'
import { useSite } from '../context/SiteContext'
import { useFetch } from '../hooks/useFetch'
import { api } from '../lib/api'
import { money } from '../lib/format'
import NotFound from './NotFound'

function Fact({ label, value }) {
  return (
    <div className="card p-5">
      <p className="eyebrow text-[11px]">{label}</p>
      <p className="mt-2 font-display text-xl font-bold leading-snug">{value}</p>
    </div>
  )
}

function Card({ title, children }) {
  return <section className="card p-6 sm:p-8"><h2 className="mb-4 text-2xl sm:text-3xl">{title}</h2>{children}</section>
}

export default function DoctorProfile() {
  const { slug } = useParams()
  const { prices } = useSite()
  const { data, error, loading } = useFetch(() => api.doctor(slug), [slug])
  if (error?.status === 404) return <NotFound />
  if (loading) return <><Hero title="" /><Loading /></>
  if (error) return <><Hero title="" /><ErrorState error={error} /></>
  const d = data.doctor
  const facts = [
    d.years_experience != null && ['Experience', `${d.years_experience} years`],
    d.branch_name && ['Branch', d.branch_name],
    d.languages.length > 0 && ['Languages', d.languages.join(', ')],
    d.registration_no && ['Registration', d.registration_no],
  ].filter(Boolean)

  return (
    <>
      <Seo title={`${d.name}, ${d.title}`} description={d.bio ? d.bio.slice(0, 155) : `${d.name}, ${d.title} at Dr. Feysel Dermatology Specialized Clinic.`} />
      <Hero eyebrow={d.title} title={d.name} intro={d.subspecialties.join(' · ') || undefined} className="pb-4 lg:pb-32">
        <nav aria-label="Breadcrumb" className="mt-6 text-sm text-[#cfe3f5]"><Link to="/" className="hover:text-white">Home</Link> / <Link to="/doctors" className="hover:text-white">Doctors</Link> / {d.name}</nav>
      </Hero>
      <div className="wrap relative z-10 grid gap-6 pt-8 lg:-mt-24 lg:grid-cols-[300px_1fr_330px] lg:pt-0">
        <div>
          {d.photo
            ? <img src={d.photo} alt={`Portrait of ${d.name}`} className="aspect-[4/5] w-full max-w-sm rounded-[34px] border-8 border-canvas object-cover object-top shadow-lift lg:max-w-none" />
            : <div className="grid aspect-[4/5] w-full max-w-sm place-items-center rounded-[34px] border-8 border-canvas bg-gradient-to-br from-sky-tint to-leaf-tint shadow-lift lg:max-w-none"><Avatar doctor={d} size={140} /></div>}
        </div>
        <div className="space-y-5 lg:pt-36">
          {facts.length > 0 && <div className="grid gap-4 sm:grid-cols-2">{facts.map(([l, v]) => <Fact key={l} label={l} value={v} />)}</div>}
          <Card title="About">
            {d.bio ? <p className="leading-8 text-muted">{d.bio}</p>
              : <p className="leading-8 text-muted">{d.name} is part of the dermatology team at Dr. Feysel Dermatology Specialized Clinic. A full biography is being added.</p>}
          </Card>
          <Card title="Qualifications and certifications">
            {d.qualifications.length > 0 ? (
              <ul className="divide-y divide-line">
                {d.qualifications.map((q) => (
                  <li key={q.label + q.detail} className="flex gap-3 py-3">
                    <Icon name="graduation-cap" size={22} className="mt-0.5 shrink-0 text-leaf" />
                    <p><b>{q.label}</b>{q.detail && <span className="block text-[15px] text-muted">{q.detail}</span>}</p>
                  </li>
                ))}
              </ul>
            ) : <p className="text-muted">Degrees, board certification and registration details are being confirmed with the clinic and will appear here.</p>}
          </Card>
          <Card title="Conditions treated">
            {d.conditions.length > 0
              ? <div className="flex flex-wrap gap-2">{d.conditions.map((c) => <Link key={c.slug} to={`/conditions/${c.slug}`} className="chip hover:bg-leaf-tint">{c.name}</Link>)}</div>
              : <p className="text-muted">See <Link className="font-semibold text-royal" to="/conditions">all conditions we treat</Link>.</p>}
          </Card>
          <Card title="Subspecialties">
            {d.subspecialties.length > 0
              ? <div className="flex flex-wrap gap-2">{d.subspecialties.map((s) => <span key={s} className="pill pill-blue">{s}</span>)}</div>
              : <p className="text-muted">General, surgical and cosmetic dermatology.</p>}
          </Card>
          {d.procedures.length > 0 && (
            <Card title="Procedures"><div className="flex flex-wrap gap-2">{d.procedures.map((s) => <span key={s} className="chip">{s}</span>)}</div></Card>
          )}
          {data.reviews.length > 0 && (
            <section><h2 className="mb-4 text-2xl sm:text-3xl">Patient reviews</h2>{data.reviews.slice(0, 3).map((r) => <ReviewCard key={r.id} review={r} />)}</section>
          )}
        </div>
        <aside className="lg:sticky lg:top-28 lg:self-start lg:pt-36">
          <div className="card p-6 shadow-lift">
            <h2 className="text-2xl">See {d.name} online</h2>
            <p className="mb-5 mt-2 text-[14.5px] leading-relaxed text-muted">Chat from {money(prices.chat)} or video + chat for {money(prices.video_chat)}. Booked and paid on Tena Medicine.</p>
            {d.accepts_telemedicine
              ? <TeleButton doctor={d.slug} className="btn btn-primary w-full" />
              : <p className="rounded-2xl bg-sky-tint p-3 text-sm text-royal">Telemedicine is not available with this doctor. Please book an in-person visit.</p>}
            <InPersonLink className="btn btn-outline mt-3 w-full" />
          </div>
        </aside>
      </div>
    </>
  )
}
