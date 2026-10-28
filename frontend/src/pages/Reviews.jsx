import { useSearchParams } from 'react-router-dom'
import { ErrorState, Loading } from '../components/States'
import Hero from '../components/Hero'
import Icon from '../components/Icon'
import ReviewCard from '../components/ReviewCard'
import ReviewForm from '../components/ReviewForm'
import Seo from '../components/Seo'
import Stars from '../components/Stars'
import { useFetch } from '../hooks/useFetch'
import { api } from '../lib/api'

const GROUPS = [
  ['condition', 'Condition', 'conditions', (f) => f.slug, (f) => f.name],
  ['symptom', 'Symptom', 'symptoms', (f) => f.name, (f) => f.name],
  ['treatment', 'Treatment', 'treatments', (f) => f.name, (f) => f.name],
  ['doctor', 'Doctor', 'doctors', (f) => f.slug, (f) => f.name],
]

export default function Reviews() {
  const [params, setParams] = useSearchParams()
  const filters = Object.fromEntries(['condition', 'symptom', 'treatment', 'doctor', 'page'].map((k) => [k, params.get(k) || '']))
  const { data, error, loading } = useFetch(() => api.reviews(filters), [params.toString()])

  const choose = (key, value) => {
    const next = new URLSearchParams(params)
    next.delete('page')
    if (!value || params.get(key) === value) next.delete(key)
    else next.set(key, value)
    setParams(next, { replace: true })
  }
  const goto = (page) => { const next = new URLSearchParams(params); next.set('page', page); setParams(next); window.scrollTo({ top: 0, behavior: 'smooth' }) }
  const pages = data ? Math.ceil(data.total / data.per_page) : 1
  const active = GROUPS.some(([k]) => filters[k])

  return (
    <>
      <Seo title="Patient reviews" description="Patient reviews you can browse by condition, symptom and treatment. Published with consent, without full names." />
      <Hero eyebrow="Patient reviews" title="Patient reviews" intro="Real experiences, filterable by condition, symptom or treatment. Published with consent and never with full names."
        side={data?.summary.average && (
          <div className="glass mx-auto w-full max-w-xs rounded-[28px] p-7 text-center lg:ml-auto">
            <p className="font-display text-6xl font-bold leading-none text-white">{data.summary.average}</p>
            <Stars value={Math.round(data.summary.average)} size={22} className="mt-3 justify-center" />
            <p className="mt-2 text-sm text-[#cfe3f5]">{data.summary.count} approved reviews</p>
          </div>
        )} />
      <div className="wrap py-10">
        {data && (
          <div className="card relative z-10 mb-6 space-y-3 p-5 shadow-lift sm:p-6 lg:-mt-14">
            {GROUPS.map(([key, label, facet, val, text]) => data.facets[facet].length > 0 && (
              <div key={key} className="flex flex-wrap items-center gap-2">
                <b className="w-24 text-xs font-bold uppercase tracking-[0.18em] text-leaf-dark">{label}</b>
                <button className={`chip ${!filters[key] ? 'chip-on' : ''}`} onClick={() => choose(key, '')}>All</button>
                {data.facets[facet].map((f) => (
                  <button key={val(f)} className={`chip ${filters[key] === val(f) ? 'chip-on' : ''}`} aria-pressed={filters[key] === val(f)} onClick={() => choose(key, val(f))}>
                    {text(f)} <span className="ml-1.5 text-xs opacity-60">{f.count}</span>
                  </button>
                ))}
              </div>
            ))}
            {active && <button className="text-sm font-semibold text-royal underline" onClick={() => setParams({}, { replace: true })}>Clear all filters</button>}
          </div>
        )}

        {loading && <Loading />}
        {error && <ErrorState error={error} />}
        {data && (data.reviews.length ? (
          <>
            <p className="mb-5 text-sm text-muted" aria-live="polite">Showing {data.reviews.length} of {data.total} reviews</p>
            <div className="columns-1 gap-5 md:columns-2 lg:columns-3">{data.reviews.map((r, i) => <ReviewCard key={r.id} review={r} large={i % 2 === 0} />)}</div>
            {pages > 1 && (
              <div className="mt-6 flex flex-wrap justify-center gap-2" role="navigation" aria-label="Pages">
                {Array.from({ length: pages }, (_, i) => i + 1).map((n) => (
                  <button key={n} className={`chip ${n === data.page ? 'chip-on' : ''}`} aria-current={n === data.page ? 'page' : undefined} onClick={() => goto(n)}>{n}</button>
                ))}
              </div>
            )}
          </>
        ) : <p className="card p-8 text-muted">No reviews match these filters yet.</p>)}

        <div className="mt-12 grid gap-6 lg:grid-cols-[1fr_1.4fr]">
          <div className="space-y-5">
            <div className="card bg-sky-tint p-7">
              <h2 className="flex items-center gap-2 text-2xl"><Icon name="shield-check" size={24} className="text-royal" /> Privacy first</h2>
              <p className="mt-3 leading-relaxed text-muted">Reviews are published only with the patient's consent and only after our team has checked them. We show an age group and condition, never full names, phone numbers or private medical details.</p>
            </div>
            <div className="card p-7">
              <h2 className="text-2xl">Been treated at our clinic?</h2>
              <p className="mt-3 leading-relaxed text-muted">Your experience helps other patients choose. Use the form to send your review. It appears after approval.</p>
            </div>
          </div>
          {data && <ReviewForm options={data} />}
        </div>
      </div>
    </>
  )
}
