import { Link } from 'react-router-dom'
import { useSite } from '../context/SiteContext'
import { telHref } from '../lib/format'
import Icon from './Icon'

const BRANCH_ADDRESS = {
  bole: 'Bole, near Bole Medhanialem',
  zenebework: 'Zenebework, across from Alert Hospital',
}

export default function Footer() {
  const { phones, email, branches } = useSite()
  return (
    <footer className="mx-3 mb-4 mt-20 rounded-[32px] bg-ink-deep px-6 pb-6 pt-10 text-[#cfe3f5] sm:mx-8 sm:px-10 lg:mx-12 lg:rounded-[40px] lg:px-14 lg:pt-12">
      <div className="mx-auto grid max-w-[1320px] gap-10 md:grid-cols-2 lg:grid-cols-[1.6fr_1fr_1.3fr_1.3fr]">
        <div className="flex gap-4">
          <img src="/assets/img/logo.png" alt="" className="h-20 w-20 shrink-0 rounded-full bg-white object-contain p-1.5" />
          <div>
            <p className="font-display text-2xl font-bold text-white">Dr. Feysel</p>
            <p className="mt-1 text-[10px] font-bold uppercase tracking-[0.18em] text-lime-soft">Dermatology Specialized Clinic</p>
            <p className="mt-2 font-script text-xl text-lime-soft">Look good, feel good.</p>
          </div>
        </div>
        <div>
          <h3 className="mb-3 font-sans text-xs font-bold uppercase tracking-[0.2em] text-lime-soft">Explore</h3>
          <ul className="space-y-2 text-[14.5px]">
            {[['/about', 'About us'], ['/doctors', 'Doctors'], ['/conditions', 'Conditions'], ['/services', 'Services'], ['/telemedicine', 'Telemedicine'], ['/reviews', 'Reviews'], ['/blog', 'Blog']].map(([to, l]) => (
              <li key={to}><Link className="hover:text-white" to={to}>{l}</Link></li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-3 font-sans text-xs font-bold uppercase tracking-[0.2em] text-lime-soft">Visit us</h3>
          <ul className="space-y-3 text-[14.5px]">
            {branches.map((b) => (
              <li key={b.slug} className="flex gap-2.5"><Icon name="map-pin" size={16} className="mt-1 shrink-0 text-lime-soft" />
                <span><strong className="text-white">{b.name}</strong><br />{BRANCH_ADDRESS[b.slug]}</span></li>
            ))}
            <li className="flex gap-2.5"><Icon name="mail" size={16} className="mt-1 shrink-0 text-lime-soft" />
              <a href={`mailto:${email}`} className="break-all hover:text-white">{email}</a></li>
          </ul>
        </div>
        <div>
          <h3 className="mb-3 font-sans text-xs font-bold uppercase tracking-[0.2em] text-lime-soft">Call</h3>
          <ul className="space-y-2 text-[14.5px]">
            {phones.map((p) => (
              <li key={p} className="flex gap-2.5"><Icon name="phone" size={16} className="mt-1 shrink-0 text-lime-soft" />
                <a href={telHref(p)} className="hover:text-white">{p}</a></li>
            ))}
          </ul>
        </div>
      </div>
      <div className="mx-auto mt-10 flex max-w-[1320px] flex-col gap-2 border-t border-white/15 pt-5 text-[12.5px] text-[#9db8d6] md:flex-row md:justify-between">
        <p>© {new Date().getFullYear()} Dr. Feysel Dermatology Specialized Clinic · Telemedicine provided with Tena Medicine</p>
        <p>Telemedicine does not replace emergency care.</p>
      </div>
    </footer>
  )
}
