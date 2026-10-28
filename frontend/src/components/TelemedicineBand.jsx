import { useSite } from '../context/SiteContext'
import { money } from '../lib/format'
import { InPersonLink, TeleButton } from './Buttons'
import Icon from './Icon'
import Avatar from './Avatar'

// Dark band explaining online visits. Booking itself happens on the telemedicine service.
export default function TelemedicineBand({ doctor }) {
  const { prices, chat_days } = useSite()
  const plans = [
    { icon: 'message-circle', name: 'Chat with a doctor', text: `Messages and photos for ${chat_days} days`, price: prices.chat },
    { icon: 'video', name: 'Video consultation + chat', text: `A video visit, then ${chat_days} days of chat`, price: prices.video_chat },
  ]
  return (
    <section className="wrap">
      <div className="relative overflow-hidden rounded-[32px] bg-hero-blue p-6 text-white sm:p-10 lg:rounded-[40px] lg:p-14">
        <div className="pointer-events-none absolute -right-24 -top-40 h-[520px] w-[520px] rounded-full bg-[radial-gradient(circle,rgba(124,194,66,.3),transparent_65%)]" />
        <div className="relative grid items-center gap-10 lg:grid-cols-[1.2fr_1fr]">
          <div>
            <span className="pill pill-dark">Telemedicine, with Tena Medicine</span>
            <h2 className="mt-4 text-3xl leading-tight text-white sm:text-5xl">Your dermatologist, on your phone.</h2>
            <p className="mt-4 max-w-xl text-[17px] leading-relaxed text-[#cfe3f5]">
              Online visits are booked and paid on Tena Medicine, our telemedicine service. You arrive with your chosen doctor already selected.
            </p>
            <div className="mt-7 grid gap-4 sm:grid-cols-2">
              {plans.map((p) => (
                <div key={p.name} className="glass rounded-3xl p-5">
                  <Icon name={p.icon} size={26} />
                  <p className="mt-3 font-bold">{p.name}</p>
                  <p className="mt-1 text-[13.5px] text-[#cfe3f5]">{p.text}</p>
                  <p className="mt-3 font-display text-3xl font-bold text-lime">{money(p.price)}</p>
                </div>
              ))}
            </div>
            <div className="mt-7 flex flex-wrap gap-3">
              <TeleButton className="btn btn-lime" />
              <InPersonLink className="btn btn-glass">Prefer in person? Book on our site</InPersonLink>
            </div>
          </div>
          <div className="hidden justify-center gap-5 lg:flex" aria-hidden="true">
            <div className="mt-6 h-[420px] w-[210px] rounded-[34px] border-8 border-[#1b4a80] bg-ink p-3.5">
              <div className="h-full rounded-[22px] bg-white p-4 text-xs text-ink">
                <b className="font-display text-sm">Chat</b>
                <div className="my-3 rounded-xl bg-leaf-tint p-2.5">Hello, how can I help with your skin today?</div>
                <div className="ml-6 rounded-xl bg-sky-tint p-2.5">Patches on my hands, photo attached</div>
                <div className="ml-6 mt-3 h-24 rounded-xl bg-cover bg-center" style={{ backgroundImage: 'url(/assets/img/services/pigment.jpg)' }} />
              </div>
            </div>
            <div className="-mt-4 h-[420px] w-[210px] rounded-[34px] border-8 border-[#1b4a80] bg-ink p-3.5">
              <div className="grid h-full place-items-center rounded-[22px] bg-ink-deep p-4 text-center">
                <div>
                  {doctor ? <Avatar doctor={doctor} size={84} className="mx-auto" /> : <span className="mx-auto grid h-[84px] w-[84px] place-items-center rounded-full bg-white/10"><Icon name="stethoscope" size={36} /></span>}
                  <p className="mt-3 font-display text-base font-bold text-white">{doctor?.name || 'Your doctor'}</p>
                  <p className="mt-1 text-xs text-lime-soft">Video visit</p>
                  <span className="mx-auto mt-12 grid h-12 w-12 place-items-center rounded-full bg-leaf"><Icon name="video" size={22} /></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
