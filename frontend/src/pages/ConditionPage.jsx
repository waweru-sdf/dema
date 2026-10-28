import { Link, useParams } from 'react-router-dom'
import { ErrorState, Loading } from '../components/States'
import { InPersonLink, TeleButton } from '../components/Buttons'
import DoctorCard from '../components/DoctorCard'
import Hero from '../components/Hero'
import Icon from '../components/Icon'
import ReviewCard from '../components/ReviewCard'
import Seo from '../components/Seo'
import { useFetch } from '../hooks/useFetch'
import { api } from '../lib/api'
import { formatDate } from '../lib/format'
import NotFound from './NotFound'

const FACT_ICONS = ['eye', 'map-pin', 'sun', 'circle-alert']

export default function ConditionPage() {
  const { slug } = useParams()
  const { data, error, loading } = useFetch(() => api.condition(slug), [slug])
  if (error?.status === 404) return <NotFound />
  if (loading) return <><Hero title="" /><Loading /></>
  if (error) return <><Hero title="" /><ErrorState error={error} /></>
  const c = data.condition

  return (
    <>
      <Seo title={`${c.name}: symptoms, causes and treatment`} description={c.summary.slice(0, 158)} />
      <Hero eyebrow="Condition guide" title={c.name} intro={c.summary} tall
        side={c.image && (
          <div className="relative hidden h-80 overflow-hidden rounded-[36px] bg-cover bg-center lg:block" style={{ backgroundImage: `url(${c.image})` }} role="img" aria-label={c.name}>
            {c.reviewed_by && c.reviewed_on && (
              <div className="glass absolute -left-0 bottom-6 left-6 flex items-center gap-3 rounded-2xl bg-ink/70 px-5 py-4 text-white">
                <Icon name="badge-check" size={30} />
                <div><b>Medically reviewed</b><p className="text-[13px] text-[#cfe3f5]">{c.reviewed_by.name} · {formatDate(c.reviewed_on)}</p></div>
              </div>
            )}
          </div>
        )}>
        <p className="mt-5 text-[13.5px] text-[#9db8d6]">
          {c.reviewed_by && c.reviewed_on ? <>Medically reviewed by <Link className="underline" to={`/doctors/${c.reviewed_by.slug}`}>{c.reviewed_by.name}</Link> · </> : null}
          Updated {formatDate(c.updated_at)}
        </p>
      </Hero>

      <div className="wrap space-y-5 py-12">
        {c.facts.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {c.facts.slice(0, 4).map((f, i) => (
              <div key={f.label} className="card p-5">
                <Icon name={FACT_ICONS[i % 4]} size={26} className="text-leaf" />
                <p className="mb-1.5 mt-3 font-display text-lg font-bold">{f.label}</p>
                <p className="text-[14.5px] leading-relaxed text-muted">{f.detail}</p>
              </div>
            ))}
          </div>
        )}

        <div className="grid gap-5 lg:grid-cols-2">
          {c.symptoms.length > 0 && (
            <section className="card p-6 sm:p-9">
              <h2 className="mb-4 text-3xl">Symptoms</h2>
              <ul>{c.symptoms.map((s) => <li key={s} className="flex gap-3 border-b border-line py-3 last:border-0"><Icon name="circle-check" size={20} className="mt-0.5 shrink-0 text-leaf" />{s}</li>)}</ul>
            </section>
          )}
          {c.causes && (
            <section className="card p-6 sm:p-9">
              <h2 className="mb-4 text-3xl">Causes and risk factors</h2>
              <p className="leading-8 text-muted">{c.causes}</p>
              <p className="mt-5 rounded-2xl bg-sky-tint p-4 text-sm text-royal">This page is general information and does not replace a medical consultation.</p>
            </section>
          )}
        </div>

        {c.steps.length > 0 && (
          <section className="card p-6 sm:p-10">
            <h2 className="mb-7 text-3xl">How we approach treatment</h2>
            <ol className="grid gap-7 md:grid-cols-3">
              {c.steps.map((s, i) => (
                <li key={s.label} className="flex gap-4">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-lime font-display text-lg font-bold">{i + 1}</span>
                  <div><h3 className="text-xl">{s.label}</h3><p className="mt-1.5 text-[14.5px] leading-relaxed text-muted">{s.detail}</p></div>
                </li>
              ))}
            </ol>
          </section>
        )}

        <section className="pt-8" aria-labelledby="docs">
          <h2 id="docs" className="mb-5 text-3xl sm:text-4xl">Doctors who treat {c.name.toLowerCase()}</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{c.doctors.map((d) => <DoctorCard key={d.slug} doctor={d} height="h-[360px]" />)}</div>
        </section>

        <section className="relative overflow-hidden rounded-[32px] bg-hero-blue p-7 text-white sm:p-10">
          <div className="relative flex flex-wrap items-center justify-between gap-6">
            <div>
              <h2 className="text-2xl text-white sm:text-3xl">Start with a telemedicine consultation</h2>
              <p className="mt-2 max-w-xl text-[#cfe3f5]">Assessment and follow-ups work well online. Procedures are done in the clinic.</p>
            </div>
            <div className="flex flex-wrap gap-3"><TeleButton className="btn btn-lime" /><InPersonLink className="btn btn-glass">In-person visit</InPersonLink></div>
          </div>
        </section>

        {c.faqs.length > 0 && (
          <section className="pt-8">
            <h2 className="mb-5 text-3xl sm:text-4xl">Frequently asked questions</h2>
            <div className="grid gap-4 md:grid-cols-2">
              {c.faqs.map((f) => <details key={f.label} className="card group p-6" open>
                <summary className="flex cursor-pointer list-none items-start justify-between gap-3 font-display text-lg font-bold">{f.label}<Icon name="chevron-down" size={20} className="mt-1 shrink-0 transition group-open:rotate-180" /></summary>
                <p className="mt-3 leading-relaxed text-muted">{f.detail}</p></details>)}
            </div>
          </section>
        )}

        {data.reviews.length > 0 && (
          <section className="pt-8">
            <h2 className="mb-5 text-3xl sm:text-4xl">What patients say about {c.name.toLowerCase()}</h2>
            <div className="columns-1 gap-5 md:columns-2 lg:columns-3">{data.reviews.map((r) => <ReviewCard key={r.id} review={r} />)}</div>
            <Link to={`/reviews?condition=${c.slug}`} className="btn btn-outline">More reviews</Link>
          </section>
        )}
      </div>
    </>
  )
}
