import { createContext, useContext } from 'react'
import { useFetch } from '../hooks/useFetch'
import { api } from '../lib/api'

// Settings the clinic edits in /admin (telemedicine address, prices, phones). Safe defaults keep the site usable if the API is slow.
const DEFAULTS = {
  telemedicine_url: 'https://tena.marhiwotmch.com',
  in_person_url: '/appointment',
  prices: { chat: '800', video_chat: '1500' },
  chat_days: '30',
  email: 'Feyselclinic@gmail.com',
  phones: ['0955 904 040', '0920 201 929', '0955 803 030', '0919 237 070', '0118 322 653'],
  branches: [
    { slug: 'bole', name: 'Bole branch', phone: '0920201929' },
    { slug: 'zenebework', name: 'Zenebework branch', phone: '0919237070' },
  ],
}

const SiteContext = createContext(DEFAULTS)

export function SiteProvider({ children }) {
  const { data } = useFetch(() => api.settings(), [])
  return <SiteContext.Provider value={{ ...DEFAULTS, ...(data || {}) }}>{children}</SiteContext.Provider>
}

export const useSite = () => useContext(SiteContext)
