import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { TeleButton } from './Buttons'
import Icon from './Icon'
import { InPersonLink } from './Buttons'

const LINKS = [
  ['/', 'Home'], ['/about', 'About'], ['/doctors', 'Doctors'], ['/conditions', 'Conditions'], ['/services', 'Services'],
  ['/reviews', 'Reviews'], ['/blog', 'Blog'], ['/contact', 'Contact'],
]

// Floating white pill that sits on top of each page's dark hero (see Hero.jsx).
export default function Nav() {
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()
  useEffect(() => setOpen(false), [pathname])

  return (
    <header className="sticky top-3 z-50 -mb-[84px] px-3 pt-3 sm:px-8 lg:px-12">
      <div className="mx-auto max-w-[1320px] rounded-[28px] bg-white/95 px-4 py-2.5 shadow-pill backdrop-blur lg:rounded-full lg:pl-6 lg:pr-3">
        <div className="flex items-center gap-4 lg:gap-8">
          <Link to="/" className="flex items-center gap-2.5" aria-label="Dr. Feysel Dermatology Specialized Clinic, home">
            <img src="/assets/img/logo.png" alt="" className="h-11 w-11 object-contain" />
            <span>
              <span className="block font-display text-xl font-bold leading-none">Dr. Feysel</span>
              <span className="mt-1 hidden text-[8.5px] font-bold uppercase tracking-[0.16em] text-leaf sm:block">Dermatology Specialized Clinic</span>
            </span>
          </Link>
          <nav aria-label="Main" className="hidden flex-1 items-center gap-6 text-[14.5px] font-semibold lg:flex">
            {LINKS.map(([to, label]) => (
              <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `transition hover:text-leaf ${isActive ? 'text-leaf' : ''}`}>
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 lg:ml-0">
            <InPersonLink className="hidden whitespace-nowrap text-[13.5px] font-bold hover:text-leaf xl:inline-flex xl:items-center xl:gap-1">In-person visit</InPersonLink>
            <TeleButton className="btn btn-primary btn-sm hidden sm:inline-flex" size={16} />
            <button className="grid h-10 w-10 place-items-center rounded-full bg-canvas lg:hidden" aria-label={open ? 'Close menu' : 'Open menu'}
              aria-expanded={open} onClick={() => setOpen(!open)}>
              <Icon name={open ? 'x' : 'menu'} size={20} />
            </button>
          </div>
        </div>
        {open && (
          <div className="mt-3 border-t border-line pb-2 pt-3 lg:hidden">
            <nav aria-label="Mobile" className="grid gap-1">
              {LINKS.map(([to, label]) => (
                <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => `rounded-xl px-3 py-2.5 font-semibold ${isActive ? 'bg-leaf-tint text-leaf-dark' : ''}`}>
                  {label}
                </NavLink>
              ))}
            </nav>
            <div className="mt-3 grid gap-2">
              <TeleButton className="btn btn-primary" />
              <InPersonLink className="btn btn-outline" />
            </div>
          </div>
        )}
      </div>
    </header>
  )
}
