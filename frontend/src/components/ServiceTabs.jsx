import { useState } from 'react'
import Icon from './Icon'
import { InPersonLink } from './Buttons'

// Left: service groups. Right: what each group includes, with a photo.
export default function ServiceTabs({ services, initial = 0 }) {
  const [active, setActive] = useState(initial)
  const s = services[active]
  return (
    <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
      <div role="tablist" aria-label="Service groups" className="flex gap-2 overflow-x-auto pb-1 lg:grid lg:overflow-visible">
        {services.map((g, i) => (
          <button key={g.slug} role="tab" id={`tab-${g.slug}`} aria-selected={i === active} aria-controls="service-panel" onClick={() => setActive(i)}
            className={`flex shrink-0 items-center gap-3 rounded-[20px] px-5 py-4 text-left text-base font-bold transition ${i === active ? 'bg-leaf text-white' : 'bg-white hover:bg-leaf-tint'}`}>
            <Icon name={g.icon} size={22} />{g.title}
          </button>
        ))}
      </div>
      <div id="service-panel" role="tabpanel" aria-labelledby={`tab-${s.slug}`} className="grid overflow-hidden rounded-[30px] bg-white md:grid-cols-2">
        <div className="p-7 sm:p-10">
          <span className="pill">In clinic</span>
          <h3 className="mb-5 mt-3 text-3xl">{s.title}</h3>
          <ul className="space-y-2.5">
            {s.items.map((i) => (
              <li key={i} className="flex gap-2.5 text-base"><Icon name="circle-check" size={20} className="mt-0.5 shrink-0 text-leaf" />{i}</li>
            ))}
          </ul>
          <p className="mt-6 text-[13px] text-muted">Online visits cover consultations, follow-ups and prescriptions. Procedures are done in person.</p>
          <InPersonLink className="btn btn-outline btn-sm mt-5">Book an in-person visit</InPersonLink>
        </div>
        <img src={s.image} alt="" loading="lazy" className="h-64 w-full object-cover md:h-full md:min-h-[420px]" />
      </div>
    </div>
  )
}
