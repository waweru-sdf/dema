import { useState } from 'react'
import { api } from '../lib/api'
import Icon from './Icon'

// Patients write their own review. It stays hidden until staff approve it in /admin.
export default function ReviewForm({ options }) {
  const [form, setForm] = useState({ rating: 5, body: '', condition: '', symptom: '', treatment: '', doctor: '', age_group: '', gender: '', consent: false, website: '' })
  const [state, setState] = useState({ busy: false, done: false, message: '', errors: {} })
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setState({ busy: true, done: false, message: '', errors: {} })
    try {
      const res = await api.submitReview({ ...form, rating: Number(form.rating) })
      setState({ busy: false, done: true, message: res.message, errors: {} })
    } catch (err) {
      setState({ busy: false, done: false, message: err.message, errors: err.errors || {} })
    }
  }

  if (state.done) {
    return (
      <div className="card p-8 text-center" role="status">
        <Icon name="circle-check" size={40} className="mx-auto text-leaf" />
        <p className="mt-3 font-display text-2xl font-bold">Thank you</p>
        <p className="mt-2 text-muted">{state.message}</p>
      </div>
    )
  }
  const err = (k) => state.errors[k] && <p className="mt-1 text-sm text-red-700">{state.errors[k]}</p>
  return (
    <form onSubmit={submit} className="card grid gap-4 p-6 sm:grid-cols-2 sm:p-8" noValidate>
      <div className="sm:col-span-2">
        <h3 className="text-2xl">Share your experience</h3>
        <p className="mt-1 text-sm text-muted">Please do not include your name, phone number or other private details. Reviews are published only after our team has checked them.</p>
      </div>
      <fieldset className="sm:col-span-2">
        <legend className="mb-1 text-sm font-semibold">Your rating</legend>
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map((n) => (
            <button type="button" key={n} onClick={() => setForm({ ...form, rating: n })} aria-label={`${n} star${n > 1 ? 's' : ''}`} aria-pressed={form.rating === n}>
              <Icon name="star" size={30} className={n <= form.rating ? 'fill-lime text-lime' : 'text-line'} />
            </button>
          ))}
        </div>
        {err('rating')}
      </fieldset>
      <div className="sm:col-span-2">
        <label className="mb-1 block text-sm font-semibold" htmlFor="rv-body">Your review</label>
        <textarea id="rv-body" rows={5} className="input" value={form.body} onChange={set('body')} maxLength={1200} />
        {err('body')}
      </div>
      <div>
        <label className="mb-1 block text-sm font-semibold" htmlFor="rv-cond">Condition</label>
        <select id="rv-cond" className="input" value={form.condition} onChange={set('condition')}>
          <option value="">Not sure / other</option>
          {options.form_conditions.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
        </select>
      </div>
      <div>
        <label className="mb-1 block text-sm font-semibold" htmlFor="rv-doc">Doctor</label>
        <select id="rv-doc" className="input" value={form.doctor} onChange={set('doctor')}>
          <option value="">Not sure</option>
          {options.form_doctors.map((d) => <option key={d.slug} value={d.slug}>{d.name}</option>)}
        </select>
      </div>
      <div>
        <label className="mb-1 block text-sm font-semibold" htmlFor="rv-sym">Main symptom (optional)</label>
        <input id="rv-sym" className="input" value={form.symptom} onChange={set('symptom')} maxLength={80} placeholder="For example itching" />
      </div>
      <div>
        <label className="mb-1 block text-sm font-semibold" htmlFor="rv-tr">Treatment (optional)</label>
        <input id="rv-tr" className="input" value={form.treatment} onChange={set('treatment')} maxLength={80} placeholder="For example light therapy" />
      </div>
      <div>
        <label className="mb-1 block text-sm font-semibold" htmlFor="rv-age">Age group</label>
        <select id="rv-age" className="input" value={form.age_group} onChange={set('age_group')}>
          <option value="">Choose</option>
          {options.age_groups.map((a) => <option key={a}>{a}</option>)}
        </select>
        {err('age_group')}
      </div>
      <div>
        <label className="mb-1 block text-sm font-semibold" htmlFor="rv-gen">Shown as</label>
        <select id="rv-gen" className="input" value={form.gender} onChange={set('gender')}>
          <option value="">Choose</option>
          {options.genders.map((g) => <option key={g}>{g}</option>)}
        </select>
        {err('gender')}
      </div>
      <input type="text" name="website" value={form.website} onChange={set('website')} tabIndex={-1} autoComplete="off" className="hidden" aria-hidden="true" />
      <div className="sm:col-span-2">
        <label className="flex items-start gap-3 text-sm">
          <input type="checkbox" className="mt-1 h-4 w-4" checked={form.consent} onChange={set('consent')} />
          <span>I agree that the clinic may publish this review on its website, shown only with my age group and no name.</span>
        </label>
        {err('consent')}
      </div>
      {state.message && !state.done && <p className="text-sm font-semibold text-red-700 sm:col-span-2" role="alert">{state.message}</p>}
      <div className="sm:col-span-2">
        <button className="btn btn-primary" disabled={state.busy}>{state.busy ? 'Sending…' : 'Submit review'}</button>
      </div>
    </form>
  )
}
