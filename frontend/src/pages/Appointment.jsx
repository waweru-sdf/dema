import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { TeleButton } from '../components/Buttons'
import Hero from '../components/Hero'
import Icon from '../components/Icon'
import Seo from '../components/Seo'
import { useSite } from '../context/SiteContext'
import { api } from '../lib/api'
import { formatDate } from '../lib/format'

const today = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10)

// In-person booking at one of the two branches. Online visits are booked on the telemedicine service instead.
export default function Appointment() {
  const [params] = useSearchParams()
  const { prices } = useSite()
  const [meta, setMeta] = useState(null)
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', phone: '', service: params.get('service') || '', branch: params.get('branch') || '',
    doctor: params.get('doctor') || '', date: '', time: '', notes: '', website: '',
  })
  const [slots, setSlots] = useState({ items: [], message: 'Choose a date to see available times.' })
  const [state, setState] = useState({ busy: false, done: null, message: '', errors: {} })

  useEffect(() => { api.meta().then(setMeta).catch(() => setMeta({ doctors: [], services: [], branches: [] })) }, [])
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value, ...(k === 'date' || k === 'doctor' || k === 'branch' ? { time: '' } : {}) }))

  useEffect(() => {
    if (!form.date) { setSlots({ items: [], message: 'Choose a date to see available times.' }); return undefined }
    let live = true
    setSlots({ items: [], message: 'Checking availability…' })
    api.availability({ date: form.date, doctor: form.doctor, branch: form.branch }).then((r) => {
      if (!live) return
      if (r.closed) setSlots({ items: [], message: r.message || 'The clinic is closed on this day. Please choose another date.' })
      else if (!r.slots.some((s) => s.available)) setSlots({ items: [], message: 'No times left on this day. Please choose another date.' })
      else setSlots({ items: r.slots, message: '' })
    }).catch(() => live && setSlots({ items: [], message: 'We could not load times. Please try again or call us.' }))
    return () => { live = false }
  }, [form.date, form.doctor, form.branch])

  const doctorName = useMemo(() => meta?.doctors.find((d) => d.slug === form.doctor)?.name, [meta, form.doctor])

  const submit = async (e) => {
    e.preventDefault()
    setState({ busy: true, done: null, message: '', errors: {} })
    try {
      const r = await api.book(form)
      setState({ busy: false, done: r, message: '', errors: {} })
      window.scrollTo(0, 0)
    } catch (err) {
      setState({ busy: false, done: null, message: err.message, errors: err.errors || {} })
    }
  }
  const err = (k) => state.errors[k] && <p className="mt-1 text-sm text-red-700">{state.errors[k]}</p>
  const label = (k, text) => <label className="mb-1 block text-sm font-semibold" htmlFor={`a-${k}`}>{text}</label>

  if (state.done) {
    return (
      <>
        <Seo title="Appointment requested" description="Your in-person appointment request." />
        <Hero eyebrow="In-person visit" title="Request received" />
        <div className="wrap max-w-2xl py-12">
          <div className="card p-8 text-center" role="status">
            <Icon name="circle-check" size={44} className="mx-auto text-leaf" />
            <p className="mt-3 font-display text-3xl font-bold">Thank you, {form.first_name}</p>
            <p className="mt-2 text-muted">Your reference is <strong className="text-ink">{state.done.reference}</strong>. We will confirm your visit by email or phone.</p>
            <p className="mt-2 text-muted">{formatDate(form.date)} at {form.time}{doctorName ? ` with ${doctorName}` : ''}.</p>
          </div>
        </div>
      </>
    )
  }

  return (
    <>
      <Seo title="Book an in-person visit" description="Book an in-person appointment at our Bole or Zenebework branch in Addis Ababa." />
      <Hero eyebrow="In-person visit" title="Book an appointment at our clinic" intro="Choose a branch, a doctor and a time that suits you. We confirm every request by email or phone." />
      <div className="wrap grid gap-6 py-12 lg:grid-cols-[1.6fr_1fr]">
        <form onSubmit={submit} noValidate className="card grid gap-4 p-6 sm:grid-cols-2 sm:p-8">
          <div>{label('first_name', 'First name')}<input id="a-first_name" className="input" value={form.first_name} onChange={set('first_name')} autoComplete="given-name" />{err('first_name')}</div>
          <div>{label('last_name', 'Last name')}<input id="a-last_name" className="input" value={form.last_name} onChange={set('last_name')} autoComplete="family-name" />{err('last_name')}</div>
          <div>{label('email', 'Email')}<input id="a-email" type="email" className="input" value={form.email} onChange={set('email')} autoComplete="email" />{err('email')}</div>
          <div>{label('phone', 'Phone')}<input id="a-phone" type="tel" className="input" value={form.phone} onChange={set('phone')} autoComplete="tel" />{err('phone')}</div>
          <div>{label('service', 'Service')}
            <select id="a-service" className="input" value={form.service} onChange={set('service')}>
              <option value="">Choose a service</option>{meta?.services.map((s) => <option key={s.slug} value={s.slug}>{s.name}</option>)}
            </select>{err('service')}</div>
          <div>{label('branch', 'Branch')}
            <select id="a-branch" className="input" value={form.branch} onChange={set('branch')}>
              <option value="">Choose a branch</option>{meta?.branches.map((b) => <option key={b.slug} value={b.slug}>{b.name}</option>)}
            </select>{err('branch')}</div>
          <div>{label('doctor', 'Doctor (optional)')}
            <select id="a-doctor" className="input" value={form.doctor} onChange={set('doctor')}>
              <option value="">Any available doctor</option>{meta?.doctors.map((d) => <option key={d.slug} value={d.slug}>{d.name}</option>)}
            </select>{err('doctor')}</div>
          <div>{label('date', 'Date')}<input id="a-date" type="date" min={today()} className="input" value={form.date} onChange={set('date')} />{err('date')}</div>
          <fieldset className="sm:col-span-2">
            <legend className="mb-1 text-sm font-semibold">Time</legend>
            {slots.message
              ? <p className="rounded-2xl bg-sky-tint p-4 text-sm text-royal">{slots.message}</p>
              : <div className="flex flex-wrap gap-2">{slots.items.map((s) => (
                <label key={s.time} className={`chip cursor-pointer ${form.time === s.time ? 'chip-on' : ''} ${s.available ? '' : 'pointer-events-none line-through opacity-40'}`}>
                  <input type="radio" name="time" value={s.time} className="sr-only" disabled={!s.available} checked={form.time === s.time} onChange={set('time')} />{s.time}
                </label>))}</div>}
            {err('time')}
          </fieldset>
          <div className="sm:col-span-2">{label('notes', 'Notes (optional)')}<textarea id="a-notes" rows={3} className="input" value={form.notes} onChange={set('notes')} placeholder="Anything we should know before your visit" />{err('notes')}</div>
          <input type="text" name="website" value={form.website} onChange={set('website')} tabIndex={-1} autoComplete="off" className="hidden" aria-hidden="true" />
          {state.message && <p className="text-sm font-semibold text-red-700 sm:col-span-2" role="alert">{state.message}</p>}
          <div className="sm:col-span-2"><button className="btn btn-primary" disabled={state.busy}>{state.busy ? 'Sending…' : 'Request appointment'}</button></div>
        </form>
        <aside className="space-y-5">
          <div className="card bg-gradient-to-br from-[#0A2A55] to-royal p-6 text-white">
            <Icon name="video" size={28} className="text-lime-soft" />
            <h2 className="mt-3 text-2xl text-white">Prefer to see a doctor online?</h2>
            <p className="mt-2 text-[#cfe3f5]">Telemedicine visits are booked and paid on Tena Medicine{prices ? `, from ${prices.chat} birr` : ''}.</p>
            <div className="mt-4"><TeleButton className="btn btn-lime" /></div>
          </div>
          <div className="card p-6">
            <h2 className="text-xl">Before you come</h2>
            <ul className="mt-3 space-y-2 text-[14.5px] text-muted">
              <li>Bring any earlier skin test results or medicine names.</li>
              <li>Arrive 10 minutes early so we can register you.</li>
              <li>Call the branch if you need to change your time.</li>
            </ul>
          </div>
        </aside>
      </div>
    </>
  )
}
