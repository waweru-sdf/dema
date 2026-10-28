import { ErrorState, Loading } from '../components/States'
import { InPersonLink, TeleButton } from '../components/Buttons'
import Avatar from '../components/Avatar'
import Hero from '../components/Hero'
import Icon from '../components/Icon'
import Seo from '../components/Seo'
import TelemedicineBand from '../components/TelemedicineBand'
import { useSite } from '../context/SiteContext'
import { useFetch } from '../hooks/useFetch'
import { api } from '../lib/api'

const STEPS = [
  ['search', 'Choose a doctor', 'Start from any doctor profile or condition page. The doctor is already selected when you arrive.'],
  ['message-circle', 'Pick a plan', 'Chat with a doctor, or a video consultation plus chat. One price for every doctor.'],
  ['credit-card', 'Pay securely', 'Pay with Telebirr, a bank or a card. You are not charged until you confirm payment.'],
  ['video', 'Talk and follow up', 'Send photos and messages, and join your video visit from your phone or computer.'],
]

export default function Telemedicine() {
  const { chat_days } = useSite()
  const { data, error, loading } = useFetch(() => api.doctors(), [])
  const AFTER = [
    ['credit-card', 'Payment is confirmed', 'You see a confirmation on screen as soon as payment succeeds.'],
    ['mail', 'SMS and email', 'We send a confirmation with your booking details.'],
    ['message-circle', 'Chat opens straight away', `You can message your doctor and send photos for ${chat_days} days.`],
    ['video', 'Video room opens before your visit', 'For a video plan, a private room opens shortly before your appointment. Join with the same account.'],
  ]
  return (
    <>
      <Seo title="Book a telemedicine consultation" description="See a dermatologist online. Choose chat or video consultation, pay securely and get confirmation by SMS and email." />
      <Hero eyebrow="Telemedicine" title="See a dermatologist from home"
        intro="Online visits are booked and paid on Tena Medicine, our telemedicine service. In-person visits are booked separately.">
        <div className="mt-7 flex flex-wrap gap-3"><TeleButton className="btn btn-lime" /><InPersonLink className="btn btn-glass">Book in person instead</InPersonLink></div>
      </Hero>
      <div className="space-y-16 py-14">
        <section className="wrap" aria-labelledby="how">
          <h2 id="how" className="mb-6 text-3xl sm:text-4xl">How it works</h2>
          <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map(([icon, t, d], i) => (
              <li key={t} className="card p-6">
                <span className="grid h-10 w-10 place-items-center rounded-full bg-lime font-display text-lg font-bold">{i + 1}</span>
                <Icon name={icon} size={26} className="mt-4 text-leaf" />
                <h3 className="mt-2 text-xl">{t}</h3><p className="mt-1.5 text-[14.5px] leading-relaxed text-muted">{d}</p>
              </li>
            ))}
          </ol>
        </section>

        <TelemedicineBand />

        <section className="wrap grid gap-5 lg:grid-cols-[1.4fr_1fr]" aria-labelledby="after">
          <div className="card p-6 sm:p-9">
            <h2 id="after" className="mb-5 text-3xl">After you pay</h2>
            <ul className="grid gap-5 sm:grid-cols-2">
              {AFTER.map(([icon, t, d]) => (
                <li key={t} className="flex gap-3"><Icon name={icon} size={24} className="mt-0.5 shrink-0 text-leaf" /><p><b>{t}</b><span className="block text-[14.5px] leading-relaxed text-muted">{d}</span></p></li>
              ))}
            </ul>
          </div>
          <div className="rounded-3xl border border-amber-200 bg-amber-50 p-6 sm:p-8">
            <h2 className="text-2xl text-amber-900">Not for emergencies</h2>
            <p className="mt-3 leading-relaxed text-amber-900/90">For a rapidly spreading rash with fever, swelling of the face or lips, or trouble breathing, go to the nearest emergency department or call 907.</p>
          </div>
        </section>

        <section className="wrap" aria-labelledby="who">
          <h2 id="who" className="mb-6 text-3xl sm:text-4xl">Doctors available online</h2>
          {loading && <Loading />}
          {error && <ErrorState error={error} />}
          {data && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.doctors.filter((d) => d.accepts_telemedicine).map((d) => (
                <div key={d.slug} className="card flex items-center gap-4 p-5">
                  <Avatar doctor={d} size={64} />
                  <div className="min-w-0 flex-1"><p className="font-display text-lg font-bold">{d.name}</p><p className="truncate text-sm text-muted">{d.title}</p></div>
                  <TeleButton doctor={d.slug} className="btn btn-primary btn-sm" size={15}>Book</TeleButton>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </>
  )
}
