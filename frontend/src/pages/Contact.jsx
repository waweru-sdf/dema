import { useState } from 'react'
import { InPersonLink, TeleButton } from '../components/Buttons'
import Hero from '../components/Hero'
import Icon from '../components/Icon'
import Seo from '../components/Seo'
import { useSite } from '../context/SiteContext'
import { api } from '../lib/api'
import { telHref } from '../lib/format'

const ADDRESS = { bole: 'Bole, near Bole Medhanialem', zenebework: 'Zenebework, across from Alert Hospital' }

function ContactForm() {
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '', website: '' })
  const [state, setState] = useState({ busy: false, done: false, message: '', errors: {} })
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const submit = async (e) => {
    e.preventDefault()
    setState({ busy: true, done: false, message: '', errors: {} })
    try {
      await api.contact(form)
      setState({ busy: false, done: true, message: '', errors: {} })
    } catch (err) {
      setState({ busy: false, done: false, message: err.message, errors: err.errors || {} })
    }
  }
  if (state.done) {
    return (
      <div className="card p-8 text-center" role="status">
        <Icon name="circle-check" size={40} className="mx-auto text-leaf" />
        <p className="mt-3 font-display text-2xl font-bold">Message sent</p>
        <p className="mt-2 text-muted">Thank you. We will reply as soon as we can. For anything urgent, please call us.</p>
      </div>
    )
  }
  const field = (k, label, props = {}) => (
    <div className={props.wide ? 'sm:col-span-2' : ''}>
      <label className="mb-1 block text-sm font-semibold" htmlFor={`c-${k}`}>{label}</label>
      {props.area
        ? <textarea id={`c-${k}`} rows={5} className="input" value={form[k]} onChange={set(k)} />
        : <input id={`c-${k}`} type={props.type || 'text'} className="input" value={form[k]} onChange={set(k)} />}
      {state.errors[k] && <p className="mt-1 text-sm text-red-700">{state.errors[k]}</p>}
    </div>
  )
  return (
    <form onSubmit={submit} className="card grid gap-4 p-6 sm:grid-cols-2 sm:p-8" noValidate>
      <h2 className="text-2xl sm:col-span-2">Send us a message</h2>
      {field('name', 'Your name')}{field('email', 'Email', { type: 'email' })}
      {field('subject', 'Subject', { wide: true })}{field('message', 'Message', { wide: true, area: true })}
      <input type="text" name="website" value={form.website} onChange={set('website')} tabIndex={-1} autoComplete="off" className="hidden" aria-hidden="true" />
      {state.message && <p className="text-sm font-semibold text-red-700 sm:col-span-2" role="alert">{state.message}</p>}
      <p className="text-[13px] text-muted sm:col-span-2">Please do not send private medical details by message. Use a telemedicine visit for that.</p>
      <div className="sm:col-span-2"><button className="btn btn-primary" disabled={state.busy}>{state.busy ? 'Sending…' : 'Send message'}</button></div>
    </form>
  )
}

export default function Contact() {
  const { branches, phones, email } = useSite()
  return (
    <>
      <Seo title="Contact and locations" description="Phone numbers, email and addresses of our Bole and Zenebework branches in Addis Ababa." />
      <Hero eyebrow="Contact" title="Contact us" intro="Call, write or visit one of our two branches in Addis Ababa.">
        <div className="mt-7 flex flex-wrap gap-3"><TeleButton className="btn btn-lime" /><InPersonLink className="btn btn-glass">Book in person</InPersonLink></div>
      </Hero>
      <div className="wrap grid gap-6 py-12 lg:grid-cols-[1fr_1.1fr]">
        <div className="space-y-5">
          <img src="/assets/img/hero-poster.jpg" alt="Inside the Dr. Feysel Dermatology Specialized Clinic" className="aspect-video w-full rounded-[28px] object-cover" />
          {branches.map((b) => (
            <div key={b.slug} className="card flex gap-4 p-6">
              <Icon name="map-pin" size={26} className="mt-1 shrink-0 text-leaf" />
              <div><h2 className="text-2xl">{b.name}</h2><p className="mt-1 text-muted">{ADDRESS[b.slug]}</p>
                <a className="mt-2 inline-flex items-center gap-2 font-bold text-royal" href={telHref(b.phone)}><Icon name="phone" size={16} />{b.phone}</a></div>
            </div>
          ))}
          <div className="card p-6">
            <h2 className="text-2xl">More ways to reach us</h2>
            <p className="mt-3 flex items-center gap-2"><Icon name="mail" size={18} className="text-leaf" /><a className="font-semibold text-royal" href={`mailto:${email}`}>{email}</a></p>
            <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2">{phones.map((p) => <li key={p}><a className="font-semibold hover:text-leaf" href={telHref(p)}>{p}</a></li>)}</ul>
          </div>
        </div>
        <ContactForm />
      </div>
    </>
  )
}
